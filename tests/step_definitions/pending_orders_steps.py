"""Steps for the Pending Orders table, deleting an order, and pending orders created through the API."""
import time
from datetime import datetime
from urllib.parse import urlparse

from playwright.sync_api import Request, expect
from pytest_bdd import given, parsers, then, when

from src.api.trading_api import CLOSE_OR_DELETE, TradingApi
from src.models.Order import Order
from src.pages.components.open_positions import NOT_SET
from src.pages.trade_page import TradePage
from tests.step_definitions.orders import let_tables_update, place_pending, send_and_finish

PENDING_TYPES = (("Buy", "Limit"), ("Sell", "Limit"), ("Buy", "Stop"), ("Sell", "Stop"),
                 ("Buy", "Stop Limit"), ("Sell", "Stop Limit"))
# An order made to expire "within two minutes" expires at the start of the minute after next:
# the server keeps expiry times to the minute.
EXPIRY_GRACE_S = 15  # how long after its expiry minute the order may take to leave the table


# --- Setup through the API (before logging in, so the page loads with it) ---

@given(parsers.parse('I have a "{side}" "{order_type}" order of "{volume}" lots on "{symbol}"'),
       target_fixture="order")
def have_pending_order(trading_api: TradingApi, open_orders: list[Order], side: str, order_type: str,
                       volume: str, symbol: str) -> Order:
    return place_pending(trading_api, open_orders, symbol, side, order_type, volume)


@given(parsers.parse('I have one pending order of each type on "{symbol}"'))
def have_one_of_each(trading_api: TradingApi, open_orders: list[Order], symbol: str):
    volume = "0.1" if symbol == "UKOIL" else "0.01"
    for side, order_type in PENDING_TYPES:
        place_pending(trading_api, open_orders, symbol, side, order_type, volume)


@given(parsers.parse('I have {count:d} "{side}" "{order_type}" orders of "{volume}" lots on "{symbol}"'))
def have_pending_orders(trading_api: TradingApi, open_orders: list[Order], count: int, side: str,
                        order_type: str, volume: str, symbol: str):
    for _ in range(count):
        place_pending(trading_api, open_orders, symbol, side, order_type, volume)


@given(parsers.parse('I have a "{side}" "{order_type}" order of "{volume}" lots on "{symbol}" that expires within two minutes'),
       target_fixture="order")
def have_expiring_order(trading_api: TradingApi, open_orders: list[Order], side: str, order_type: str,
                        volume: str, symbol: str) -> Order:
    expires_at_s = (int(time.time()) // 60 + 2) * 60
    return place_pending(trading_api, open_orders, symbol, side, order_type, volume,
                         expiry="Specified Date and Time", expiration_ms=expires_at_s * 1000)


@given(parsers.parse('I had a "{side}" "{order_type}" order of "{volume}" lots on "{symbol}" that I deleted'),
       target_fixture="order")
def had_deleted_order(trading_api: TradingApi, open_orders: list[Order], side: str, order_type: str,
                      volume: str, symbol: str) -> Order:
    order = place_pending(trading_api, open_orders, symbol, side, order_type, volume)
    trading_api.delete_pending_order(order)
    return order


# --- The table ---

@when("I open Pending Orders")
def open_pending_orders(trade_page: TradePage):
    trade_page.pending_orders.open()


@then("my order should be listed in Pending Orders as ordered")
def pending_listed_as_ordered(trade_page: TradePage, order: Order):
    table, order_id = trade_page.pending_orders, order.order_id
    trade_page.pending_orders.open()
    expect(table.row(order_id)).to_be_visible()
    expect(table.cell(order_id, "symbol")).to_have_text(order.symbol)
    expect(table.cell(order_id, "order-type")).to_have_text(order.type_label)
    expect(table.cell(order_id, "volume")).to_have_text(f"{order.volume} / 0")  # ordered / filled
    expect(table.cell(order_id, "entry-price")).to_have_text(order.price)
    expect(table.cell(order_id, "fill-policy")).to_have_text("Return")
    expect(table.cell(order_id, "expiry")).to_have_text(order.expiry)
    expect(table.cell(order_id, "expiry-date")).to_have_text(order.expiry_date or NOT_SET)
    expect(table.cell(order_id, "stop-loss")).to_have_text(order.stop_loss or NOT_SET)
    expect(table.cell(order_id, "take-profit")).to_have_text(order.take_profit or NOT_SET)


@then(parsers.parse('my order should still show price "{price}"'))
def pending_shows_price(trade_page: TradePage, order: Order, price: str):
    let_tables_update(trade_page.page)
    expect(trade_page.pending_orders.row(order.order_id)).to_be_visible()
    expect(trade_page.pending_orders.cell(order.order_id, "entry-price")).to_have_text(price)


@then("no pending order should have been created")
def none_created(trading_api: TradingApi, order: Order):
    created = [o["orderId"] for o in trading_api.pending_orders()
               if o["symbol"] == order.symbol and abs(o["price"] - float(order.price)) < 1e-9]
    assert not created, f"A pending order was created at {order.price}: {created}"


@then("my order should still be pending")
def still_pending(trade_page: TradePage, order: Order):
    let_tables_update(trade_page.page)
    expect(trade_page.pending_orders.row(order.order_id)).to_be_visible()


@then("my order should no longer be pending")
def no_longer_pending(trade_page: TradePage, order: Order):
    # The row was there: the step before used one of its buttons, or checked it.
    expect(trade_page.pending_orders.row(order.order_id)).to_have_count(0)


# --- Deleting ---

@when("I start deleting my order")
def start_deleting(trade_page: TradePage, order: Order):
    trade_page.pending_orders.open()
    trade_page.pending_orders.delete(order.order_id)
    expect(trade_page.delete_order_dialog.root).to_contain_text(order.order_id)


@when("I delete my order")
def delete_order(trade_page: TradePage, order: Order):
    start_deleting(trade_page, order)
    confirm_deletion(trade_page)


@when("I confirm the deletion")
def confirm_deletion(trade_page: TradePage):
    send_and_finish(trade_page.page, _is_delete, trade_page.delete_order_dialog.confirm)


@when("I cancel the deletion")
def cancel_deletion(trade_page: TradePage):
    trade_page.delete_order_dialog.cancel()
    expect(trade_page.delete_order_dialog.root).to_be_hidden()


# --- Expiry ---

@when("I wait for my order to expire")
def wait_for_expiry(trade_page: TradePage, order: Order):
    table = trade_page.pending_orders.open()
    expect(table.row(order.order_id)).to_be_visible()
    # Both on the server's clock: "2026-10-23 19:17:00" and "Server Time : 2026-10-23 19:15:40".
    order.expiry_date = table.cell(order.order_id, "expiry-date").inner_text().strip()
    expires = datetime.strptime(order.expiry_date, "%Y-%m-%d %H:%M:%S")
    now = datetime.strptime(trade_page.server_time.inner_text().split(":", 1)[1].strip(), "%Y-%m-%d %H:%M:%S")
    trade_page.page.wait_for_timeout(max(0.0, (expires - now).total_seconds()) * 1000)
    expect(table.row(order.order_id)).to_have_count(0, timeout=EXPIRY_GRACE_S * 1000)


def _is_delete(request: Request) -> bool:
    return request.method == "DELETE" and urlparse(request.url).path == CLOSE_OR_DELETE
