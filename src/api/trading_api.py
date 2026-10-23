"""The site's internal trading API, used for test setup and cleanup (see docs/api-notes.md).

Scenarios check behaviour through the UI. Opening and closing orders here instead is about ten
times faster than through the UI, and the API returns the new Order No. directly.
"""
from playwright.sync_api import APIRequestContext, APIResponse, Playwright

from src.models.Order import Order

LOGIN = "/api/auth/v2/metatrader5/demo/login"
MARKET_ORDER = "/api/trade/trade/v1/market"
OPEN_POSITIONS = "/api/trade/order/v1"
BULK_CLOSE = "/api/trade/trade/v1/bulk"
PREFERENCE = "/api/user/setting/v1/preference"

ORDER_TYPES = {"buy": 0, "sell": 1}
FILL_OR_KILL = 0
# The site closes at most 30 positions per bulk close.
BULK_CLOSE_LIMIT = 30


class TradingApi:
    def __init__(self, playwright: Playwright, base_url: str, username: str, password: str):
        self._playwright = playwright
        self._base_url = base_url
        self._credentials = {"userId": username, "password": password, "source": "WEB"}
        self.request = self._new_session()

    @classmethod
    def log_in(cls, playwright: Playwright, base_url: str, username: str, password: str) -> "TradingApi":
        return cls(playwright, base_url, username, password)

    def dispose(self):
        self.request.dispose()

    def _new_session(self) -> APIRequestContext:
        anonymous = self._playwright.request.new_context(base_url=self._base_url)
        try:
            token = _result(anonymous.post(LOGIN, data=self._credentials), LOGIN)["token"]
        finally:
            anonymous.dispose()
        headers = {"authorization": f"Bearer {token}"}
        return self._playwright.request.new_context(base_url=self._base_url, extra_http_headers=headers)

    def _send(self, method: str, path: str, **kwargs) -> APIResponse:
        """Send a call, logging in again once if this session has been logged out.

        The site keeps about 10 sessions per account and logs out the oldest when another one
        starts (HTTP 401). Every scenario logs in through the UI, so during a run this API session
        is soon the oldest. A 401 means the call was refused, so sending it again is safe.
        """
        response = self.request.fetch(path, method=method, **kwargs)
        if response.status == 401:
            self.request.dispose()
            self.request = self._new_session()
            response = self.request.fetch(path, method=method, **kwargs)
        return response

    def open_market_order(self, symbol: str, side: str, volume: str) -> Order:
        payload = {
            "orderType": _order_type(side),
            "symbol": symbol,
            "lotSize": float(volume),
            "fillPolicy": FILL_OR_KILL,
            "indicate": "PRICE",
        }
        result = _result(self._send("POST", MARKET_ORDER, data=payload), MARKET_ORDER)
        return Order(order_id=result["clOrdId"], symbol=symbol, side=side, volume=volume)

    def open_positions(self) -> list[dict]:
        """Every open position on the account, as the Open Positions table lists them."""
        return _result(self._send("GET", OPEN_POSITIONS), OPEN_POSITIONS)

    def close_positions(self, positions: list[dict]):
        """Close these positions in full. Takes items from open_positions(), Buy or Sell."""
        for start in range(0, len(positions), BULK_CLOSE_LIMIT):
            batch = positions[start:start + BULK_CLOSE_LIMIT]
            orders = [{"orderId": p["orderId"], "symbol": p["symbol"], "lotSize": p["lotSize"],
                       "fillPolicy": FILL_OR_KILL} for p in batch]
            result = _result(self._send("PUT", BULK_CLOSE, data={"orderList": orders}), BULK_CLOSE)
            closed = {str(order_id) for order_id in result.get("closedOrderIds", [])}
            still_open = [p["orderId"] for p in batch if p["orderId"] not in closed]
            if still_open:
                raise RuntimeError(f"Bulk close left these positions open: {still_open}")

    def set_one_click_trading(self, on: bool):
        """Turn one-click trading on or off for the account (a server setting, shared by every session)."""
        payload = {"type": "OCT_ENABLE", "category": "ONE_CLICK_TRADING", "value": "true" if on else "false"}
        response = self._send("PATCH", PREFERENCE, data=payload)
        # This call answers 200 with an empty body, not the usual {"code": "200", ...} wrapper.
        if not response.ok:
            raise RuntimeError(f"{PREFERENCE} failed: HTTP {response.status} {response.text()[:300]}")


def placed_order_no(response) -> str:
    """The Order No. from the site's answer to a market order (an API or browser response)."""
    return _result(response, MARKET_ORDER)["clOrdId"]


def _order_type(side: str) -> int:
    try:
        return ORDER_TYPES[side.lower()]
    except KeyError:
        raise ValueError(f"Unknown side '{side}'. Use one of: Buy, Sell") from None


def _result(response: APIResponse, path: str):
    """The `result` of a successful call. Every response is wrapped as {"code": "200", "result": ...}."""
    try:
        body = response.json()
    except Exception:
        body = None
    if not response.ok or not isinstance(body, dict) or body.get("code") != "200":
        raise RuntimeError(f"{path} failed: HTTP {response.status} {response.text()[:300]}")
    return body["result"]
