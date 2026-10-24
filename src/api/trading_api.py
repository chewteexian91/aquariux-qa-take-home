"""The site's internal trading API, used for test setup and cleanup (see docs/api-notes.md).

Scenarios check behaviour through the UI. Opening and closing orders here instead is about ten
times faster than through the UI, and the API returns the new Order No. directly.
"""
import time

from playwright.sync_api import APIRequestContext, APIResponse, Playwright

from src.models.Order import Order

LOGIN = "/api/auth/v2/metatrader5/demo/login"
MARKET_ORDER = "/api/trade/trade/v1/market"  # POST place, PATCH modify a position's SL/TP
PENDING_ORDER = "/api/trade/trade/v1/limit"  # POST place, PATCH modify a pending order
CLOSE_OR_DELETE = "/api/trade/trade/v1"  # PUT close a position, DELETE a pending order
BULK_CLOSE = "/api/trade/trade/v1/bulk"
BULK_DELETE = "/api/trade/trade/v1/limit/bulk"
OPEN_POSITIONS = "/api/trade/order/v1"
PENDING_ORDERS = "/api/trade/order/v1/pending"
POSITIONS_HISTORY = "/api/order/v3/histories"
ORDERS_AND_DEALS = "/api/trade/order/v1/deal/histories"
NOTIFICATIONS = "/api/notification/v2"
PREFERENCE = "/api/user/setting/v1/preference"
SYMBOL_DETAIL = "/api/market/v1/symbol/detail"

# A symbol's "status" in SYMBOL_DETAIL while its market is open, and outside its trading hours.
MARKET_OPEN = "TRADING"
MARKET_CLOSED = "CLOSED"

ORDER_TYPES = {"buy": 0, "sell": 1}
PENDING_ORDER_TYPES = {
    ("buy", "limit"): 2, ("sell", "limit"): 3,
    ("buy", "stop"): 4, ("sell", "stop"): 5,
    ("buy", "stop limit"): 8, ("sell", "stop limit"): 9,
}
# Expiry as the UI names it -> the API's tradeExpiry.
EXPIRY = {
    "Good Till Canceled": "GTC",
    "Good Till Day": "GTD",
    "Specified Date": "SPECIFIED_DAY",
    "Specified Date and Time": "SPECIFIED_TIMESTAMP",
}
FILL_OR_KILL = 0
RETURN = 2  # the only fill policy for pending orders
# The site closes or deletes at most 30 orders per bulk call.
BULK_LIMIT = 30


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
        starts (HTTP 401). A 401 means the call was refused, so sending it again is safe.
        """
        response = self.request.fetch(path, method=method, **kwargs)
        if response.status == 401:
            self.request.dispose()
            self.request = self._new_session()
            response = self.request.fetch(path, method=method, **kwargs)
        return response

    # --- Market ---

    def market_is_open(self, symbol: str) -> bool:
        """Whether the symbol can be traded right now. The server's own answer, so it covers
        weekends, daily breaks and holidays without a timetable (docs/api-notes.md)."""
        path = f"{SYMBOL_DETAIL}?symbol={symbol}"
        return _result(self._send("GET", path), SYMBOL_DETAIL)["status"] == MARKET_OPEN

    # --- Positions ---

    def open_market_order(self, symbol: str, side: str, volume: str,
                          stop_loss: str | None = None, take_profit: str | None = None) -> Order:
        payload = {
            "orderType": _order_type(side),
            "symbol": symbol,
            "lotSize": float(volume),
            "fillPolicy": FILL_OR_KILL,
            "indicate": "PRICE",
        }
        if stop_loss is not None:
            payload["stopLoss"] = float(stop_loss)
        if take_profit is not None:
            payload["takeProfit"] = float(take_profit)
        result = _result(self._send("POST", MARKET_ORDER, data=payload), MARKET_ORDER)
        return Order(order_id=result["clOrdId"], symbol=symbol, side=side, volume=volume,
                     fill_policy="Fill or Kill", stop_loss=stop_loss, take_profit=take_profit)

    def open_positions(self) -> list[dict]:
        """Every open position on the account, as the Open Positions table lists them."""
        return _result(self._send("GET", OPEN_POSITIONS), OPEN_POSITIONS)

    def position(self, order_id: str) -> dict:
        matches = [p for p in self.open_positions() if p["orderId"] == order_id]
        if not matches:
            raise RuntimeError(f"Position {order_id} is not open")
        return matches[0]

    def close_position(self, order: Order, volume: str):
        """Close `volume` lots of a position (all of it or part)."""
        # The close call answers 500 "Internal error" unless this session has listed the
        # positions since the position opened (docs/api-notes.md), so list them first.
        self.position(order.order_id)
        payload = {"orderId": order.order_id, "symbol": order.symbol, "lotSize": float(volume),
                   "orderType": _order_type(order.side), "fillPolicy": FILL_OR_KILL}
        _result(self._send("PUT", CLOSE_OR_DELETE, data=payload), CLOSE_OR_DELETE)

    def close_positions(self, positions: list[dict]):
        """Close these positions in full. Takes items from open_positions(), Buy or Sell."""
        for batch in _batches(positions):
            orders = [{"orderId": p["orderId"], "symbol": p["symbol"], "lotSize": p["lotSize"],
                       "fillPolicy": FILL_OR_KILL} for p in batch]
            result = _result(self._send("PUT", BULK_CLOSE, data={"orderList": orders}), BULK_CLOSE)
            _check_all_done(batch, result.get("closedOrderIds"), "Bulk close left these positions open")

    # --- Pending orders ---

    def place_pending_order(self, symbol: str, side: str, order_type: str, volume: str, price: str,
                            stop_limit_price: str | None = None, expiry: str = "Good Till Canceled",
                            expiration_ms: int | None = None, stop_loss: str | None = None,
                            take_profit: str | None = None) -> Order:
        """Place a Limit, Stop or Stop Limit order. `expiry` is the UI's name for it."""
        payload = {
            "orderType": _pending_order_type(side, order_type),
            "symbol": symbol,
            "lotSize": float(volume),
            "price": float(price),
            "priceTrigger": float(stop_limit_price) if stop_limit_price is not None else None,
            "fillPolicy": RETURN,
            "indicate": "PRICE",
            "tradeExpiry": EXPIRY[expiry],
        }
        if expiration_ms is not None:
            payload["expiration"] = expiration_ms
        if stop_loss is not None:
            payload["stopLoss"] = float(stop_loss)
        if take_profit is not None:
            payload["takeProfit"] = float(take_profit)
        result = _result(self._send("POST", PENDING_ORDER, data=payload), PENDING_ORDER)
        return Order(order_id=result["clOrdId"], symbol=symbol, side=side, volume=volume, order_type=order_type,
                     price=price, stop_limit_price=stop_limit_price, expiry=expiry, fill_policy="Return",
                     stop_loss=stop_loss, take_profit=take_profit)

    def pending_orders(self) -> list[dict]:
        """Every pending order on the account, as the Pending Orders table lists them."""
        return _result(self._send("GET", PENDING_ORDERS), PENDING_ORDERS)

    def delete_pending_order(self, order: Order):
        path = f"{CLOSE_OR_DELETE}?symbol={order.symbol}&orderId={order.order_id}"
        _result(self._send("DELETE", path), CLOSE_OR_DELETE)

    def delete_pending_orders(self, orders: list[dict]):
        """Delete these pending orders. Takes items from pending_orders()."""
        for batch in _batches(orders):
            body = [{"orderId": o["orderId"], "symbol": o["symbol"]} for o in batch]
            result = _result(self._send("PUT", BULK_DELETE, data=body), BULK_DELETE)
            _check_all_done(batch, result.get("deletedOrderIds"), "Bulk delete left these orders pending")

    # --- Records ---

    def order_notifications(self) -> list[dict]:
        """The Positions tab of the notifications panel, newest first."""
        return _result(self._send("GET", f"{NOTIFICATIONS}?notificationType=ORDER"), NOTIFICATIONS)

    def orders_and_deals(self, since_ms: int) -> list[dict]:
        """Orders & Deals from `since_ms` (epoch ms) until now."""
        to_ms = int(time.time() * 1000) + 60_000
        path = f"{ORDERS_AND_DEALS}?from={since_ms}&to={to_ms}"
        return _result(self._send("GET", path), ORDERS_AND_DEALS)

    # --- Account settings (shared by every session on the account) ---

    def set_one_click_trading(self, on: bool):
        """Turn one-click trading on or off for the account."""
        self._set_preference({"type": "OCT_ENABLE", "category": "ONE_CLICK_TRADING", "value": _flag(on)})

    def set_hide_other_symbols(self, on: bool):
        """Show only the open symbol's orders in the tables (and in bulk actions), or all of them."""
        self._set_preference({"type": "HIDE_OTHER_SYMBOLS", "category": "MARKET", "value": _flag(on)})

    def _set_preference(self, payload: dict):
        response = self._send("PATCH", PREFERENCE, data=payload)
        # This call answers 200 with an empty body, not the usual {"code": "200", ...} wrapper.
        if not response.ok:
            raise RuntimeError(f"{PREFERENCE} failed: HTTP {response.status} {response.text()[:300]}")


def placed_order_no(response) -> str:
    """The Order No. from the site's answer to a new market or pending order."""
    return _result(response, "order")["clOrdId"]


def _order_type(side: str) -> int:
    try:
        return ORDER_TYPES[side.lower()]
    except KeyError:
        raise ValueError(f"Unknown side '{side}'. Use one of: Buy, Sell") from None


def _pending_order_type(side: str, order_type: str) -> int:
    try:
        return PENDING_ORDER_TYPES[(side.lower(), order_type.lower())]
    except KeyError:
        raise ValueError(f"Unknown pending order '{side} {order_type}'. "
                         f"Use Buy or Sell with Limit, Stop or Stop Limit") from None


def _flag(on: bool) -> str:
    return "true" if on else "false"


def _batches(items: list) -> list[list]:
    return [items[start:start + BULK_LIMIT] for start in range(0, len(items), BULK_LIMIT)]


def _check_all_done(batch: list[dict], done_ids, message: str):
    done = {str(order_id) for order_id in done_ids or []}
    left = [o["orderId"] for o in batch if o["orderId"] not in done]
    if left:
        raise RuntimeError(f"{message}: {left}")


def _result(response: APIResponse, path: str):
    """The `result` of a successful call. Every response is wrapped as {"code": "200", "result": ...}."""
    try:
        body = response.json()
    except Exception:
        body = None
    if not response.ok or not isinstance(body, dict) or body.get("code") != "200":
        raise RuntimeError(f"{path} failed: HTTP {response.status} {response.text()[:300]}")
    return body["result"]
