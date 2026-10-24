"""Helpers for creating and recording orders, shared by several step files.

Not a step file: it holds no steps, so it isn't registered in `pytest_plugins`.
"""
import re
from datetime import date, datetime
from urllib.parse import urlparse

import pytest
from playwright.sync_api import Request, Response, expect

from src.api.trading_api import MARKET_ORDER, PENDING_ORDER, TradingApi, placed_order_no
from src.models.Order import Order
from src.pages.trade_page import TradePage
from tests.step_definitions.trading_data import PENDING_PRICES, price_text


def is_new_order(message: Request | Response) -> bool:
    """A request (or its answer) that places a market or pending order."""
    request = message.request if isinstance(message, Response) else message
    return request.method == "POST" and urlparse(request.url).path in (MARKET_ORDER, PENDING_ORDER)


# A table shows a change about 1.5 s after the site answers. A check that nothing changed waits this
# long first, or it would pass before the change had a chance to show.
TABLE_UPDATE_MS = 2000


def let_tables_update(page):
    page.wait_for_timeout(TABLE_UPDATE_MS)


def send_and_finish(page, is_request, action):
    """Do `action`, which sends a request, and wait until that request has finished: answered, or
    failed (a faked network error). Later checks then see what the site did with the answer."""
    with page.expect_request(is_request) as sent:
        action()
    sent.value.response()  # None when the request failed without an answer


def record_placed_order(response: Response, order: Order, open_orders: list[Order]):
    """Take the Order No. from the site's answer and register the order for cleanup."""
    try:
        order.order_id = placed_order_no(response)
    except RuntimeError as rejected:
        # The site turning the order down is a failed check, not a broken test.
        raise AssertionError(f"The order was not placed: {rejected}") from None
    open_orders.append(order)  # removed again in teardown, pass or fail


def skip_if_market_closed(trading_api: TradingApi, symbol: str):
    """Outside the symbol's trading hours the server turns every new order down, so a scenario
    that needs one can't run."""
    if not trading_api.market_is_open(symbol):
        pytest.skip(f"{symbol} market is closed: no order can be placed")


def open_position(trading_api: TradingApi, open_orders: list[Order], symbol: str, side: str, volume: str,
                  stop_loss: str | None = None, take_profit: str | None = None) -> Order:
    """Open a position through the API and register it for cleanup."""
    skip_if_market_closed(trading_api, symbol)
    order = trading_api.open_market_order(symbol, side, volume, stop_loss, take_profit)
    open_orders.append(order)  # closed again in teardown, pass or fail
    order.entry_price = price_text(symbol, trading_api.position(order.order_id)["openPrice"])
    return order


def place_pending(trading_api: TradingApi, open_orders: list[Order], symbol: str, side: str, order_type: str,
                  volume: str, **expiry) -> Order:
    """Place a pending order through the API, far from the market, and register it for cleanup."""
    skip_if_market_closed(trading_api, symbol)
    price, stop_limit_price = PENDING_PRICES[symbol][(side, order_type)]
    order = trading_api.place_pending_order(symbol, side, order_type, volume, price, stop_limit_price, **expiry)
    open_orders.append(order)  # deleted again in teardown, pass or fail
    return order


def server_today(trade_page: TradePage) -> date:
    """Today on the server's clock (shown top right), which expiry dates follow."""
    expect(trade_page.server_time).to_have_text(re.compile(r"\d{4}-\d{2}-\d{2}"))
    shown = re.search(r"\d{4}-\d{2}-\d{2}", trade_page.server_time.inner_text()).group()
    return datetime.strptime(shown, "%Y-%m-%d").date()
