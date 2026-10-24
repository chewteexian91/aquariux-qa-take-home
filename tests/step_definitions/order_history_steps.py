"""Steps for the Positions History and Orders & Deals tabs, and closed positions made through the API."""
import re
import time
from decimal import ROUND_HALF_UP, Decimal

from playwright.sync_api import expect
from pytest_bdd import given, parsers, then, when

from src.api.trading_api import TradingApi
from src.models.Order import Close, Order
from src.pages.trade_page import TradePage
from tests.step_definitions.orders import open_position
from tests.step_definitions.trading_data import POSITION_SL_TP, price_text

CLOSE_TEMPLATE = "NT_ORDER_CLOSE"
# The server's records of a close show up within a second or two.
RECORDS_TIMEOUT_S = 20


# --- Setup through the API (before logging in) ---

@given(parsers.parse('I had a "{side}" position of "{volume}" lots on "{symbol}" that I closed'),
       target_fixture="order")
def had_closed_position(trading_api: TradingApi, open_orders: list[Order], side: str, volume: str, symbol: str) -> Order:
    return _position_closed_in(trading_api, open_orders, symbol, side, volume, [volume])


@given(parsers.parse('I had a "{side}" position of "{volume}" lots on "{symbol}" that I closed in two halves'),
       target_fixture="order")
def had_position_closed_in_halves(trading_api: TradingApi, open_orders: list[Order], side: str, volume: str,
                                  symbol: str) -> Order:
    half = str(Decimal(volume) / 2)
    return _position_closed_in(trading_api, open_orders, symbol, side, volume, [half, half])


@given(parsers.parse('I have a "{side}" position of "{volume}" lots on "{symbol}" that I partly closed by "{part}" lots'),
       target_fixture="order")
def have_partly_closed_position(trading_api: TradingApi, open_orders: list[Order], side: str, volume: str,
                                symbol: str, part: str) -> Order:
    return _position_closed_in(trading_api, open_orders, symbol, side, volume, [part])


def _position_closed_in(trading_api: TradingApi, open_orders: list[Order], symbol: str, side: str, volume: str,
                        parts: list[str]) -> Order:
    """Open a position with SL/TP, close it in these parts, and note each close as the server recorded it."""
    stop_loss, take_profit = POSITION_SL_TP[symbol][side]
    since_ms = int(time.time() * 1000) - 60_000
    order = open_position(trading_api, open_orders, symbol, side, volume, stop_loss, take_profit)
    for part in parts:
        trading_api.close_position(order, part)
    order.closes = _closes(trading_api, order, len(parts), since_ms)
    return order


def _closes(trading_api: TradingApi, order: Order, count: int, since_ms: int) -> list[Close]:
    """The closes of a position, oldest first, as the server recorded them.

    The "Position Closed" notifications say which order closed which part. The price and P/L come
    from that order's deal in Orders & Deals: the fill itself. (A notification's close price can
    differ from the fill, docs/findings.md #20.)
    """
    deadline = time.monotonic() + RECORDS_TIMEOUT_S
    while True:
        notified = [n["metadata"] for n in trading_api.order_notifications()
                    if n["notificationTemplate"] == CLOSE_TEMPLATE and n["metadata"]["orderId"] == order.order_id]
        deals = {d["orderId"]: d["deals"][0] for d in trading_api.orders_and_deals(since_ms) if d["deals"]}
        if (len(notified) >= count and all(str(m["tradeId"]) in deals for m in notified)) or time.monotonic() > deadline:
            break
        time.sleep(1)
    if len(notified) != count:
        raise RuntimeError(f"Expected {count} closes of position {order.order_id}, the server lists {len(notified)}")
    closes = []
    for m in reversed(notified):  # notifications are newest first
        deal = deals[str(m["tradeId"])]
        closes.append(Close(order_id=str(m["tradeId"]), volume=_lots(deal["lotSize"]),
                            price=price_text(order.symbol, deal["price"]), profit=f"{deal['profit']:.2f}"))
    return closes


def _lots(value) -> str:
    return f"{Decimal(str(value)).normalize():f}"


# --- The tabs ---

@when("I open Positions History")
def open_positions_history(trade_page: TradePage):
    _close_notifications(trade_page)
    trade_page.order_history.open_positions_history()


@when("I open Orders & Deals")
def open_orders_and_deals(trade_page: TradePage):
    _close_notifications(trade_page)
    trade_page.order_history.open_orders_and_deals()


def _close_notifications(trade_page: TradePage):
    # The notifications panel covers the tables.
    if trade_page.notifications.panel.is_visible():
        trade_page.notifications.bell.click()
        expect(trade_page.notifications.panel).to_be_hidden()


@when(parsers.parse('I choose the date range "{preset}"'))
def choose_date_range(trade_page: TradePage, preset: str):
    trade_page.order_history.choose_date_range(preset)


@then("Positions History should list my position")
def positions_history_lists_closed(trade_page: TradePage, order: Order):
    history, order_id = trade_page.order_history, order.order_id
    expect(history.row(order_id)).to_be_visible()
    expect(history.cell(order_id, "symbol")).to_have_text(order.symbol)
    expect(history.cell(order_id, "order-type")).to_have_text(order.side.upper())
    expect(history.cell(order_id, "entry-price")).to_have_text(order.entry_price)
    expect(history.cell(order_id, "stop-loss")).to_have_text(order.stop_loss)
    expect(history.cell(order_id, "take-profit")).to_have_text(order.take_profit)
    closed = sum(Decimal(c.volume) for c in order.closes)
    if closed == Decimal(order.volume):
        # One row for the whole position: the volume, the average close price, the total P/L.
        expect(history.cell(order_id, "volume")).to_have_text(order.volume)
        average = sum(Decimal(c.price) * Decimal(c.volume) for c in order.closes) / closed
        expect(history.cell(order_id, "close-price")).to_have_text(
            str(average.quantize(Decimal(order.entry_price), rounding=ROUND_HALF_UP)))
    else:
        # Still open: the row shows what has been closed so far, out of the whole.
        expect(history.cell(order_id, "volume")).to_have_text(f"{_lots(closed)} / {order.volume}")
        expect(history.cell(order_id, "close-price")).to_have_text(order.closes[-1].price)
    _expect_amount(history.cell(order_id, "profit"), sum(Decimal(c.profit) for c in order.closes))


@then("Orders & Deals should list my opening order as filled")
def opening_order_filled(trade_page: TradePage, order: Order):
    history, order_id = trade_page.order_history, order.order_id
    expect(history.row(order_id)).to_be_visible()
    expect(history.cell(order_id, "order-type")).to_have_text(order.side)
    expect(history.cell(order_id, "state")).to_have_text("FILLED", use_inner_text=True)  # upper case by CSS
    expect(history.cell(order_id, "volume")).to_have_text(f"{order.volume} / {order.volume}")  # filled / ordered
    expect(history.cell(order_id, "entry-price")).to_have_text(order.entry_price)


@then("Orders & Deals should list each close of my position as a filled order with its own Order No.")
def closing_orders_filled(trade_page: TradePage, order: Order):
    history = trade_page.order_history
    other_side = "Sell" if order.side == "Buy" else "Buy"
    assert order.closes, "The scenario has no closes to check"
    for close in order.closes:
        assert close.order_id != order.order_id, f"The close of {order.order_id} reused its Order No."
        expect(history.row(close.order_id)).to_be_visible()
        expect(history.cell(close.order_id, "order-type")).to_have_text(other_side)
        expect(history.cell(close.order_id, "state")).to_have_text("FILLED", use_inner_text=True)
        expect(history.cell(close.order_id, "volume")).to_have_text(f"{close.volume} / {close.volume}")
        expect(history.cell(close.order_id, "entry-price")).to_have_text(close.price)


@when("I expand my opening order")
def expand_opening_order(trade_page: TradePage, order: Order):
    trade_page.order_history.expand(order.order_id)


@then(parsers.parse('its deal should be "{direction}" for "{volume}" lots'))
def deal_shows(trade_page: TradePage, order: Order, direction: str, volume: str):
    deal = trade_page.order_history.deal_row(order.order_id)
    # Deal rows have no test ids: check their text.
    expect(deal).to_contain_text(direction)
    expect(deal).to_contain_text(volume)


@then(parsers.parse('Orders & Deals should list my order as "{state}"'))
def order_listed_with_state(trade_page: TradePage, order: Order, state: str):
    history, order_id = trade_page.order_history, order.order_id
    expect(history.row(order_id)).to_be_visible()
    expect(history.cell(order_id, "order-type")).to_have_text(f"{order.side} {order.order_type}")
    expect(history.cell(order_id, "state")).to_have_text(state, use_inner_text=True)  # upper case by CSS
    expect(history.cell(order_id, "volume")).to_have_text(f"{order.volume} / 0")


@then("its remarks should say when it expired")
def expired_remarks(trade_page: TradePage, order: Order):
    # The expiry date as Pending Orders showed it ("2026-10-23 19:17:00"), to the minute.
    expect(trade_page.order_history.cell(order.order_id, "remarks")).to_have_text(f"Expired [{order.expiry_date[:16]}]")


@then("Orders & Deals should not list my opening order")
def opening_order_not_listed(trade_page: TradePage, order: Order):
    expect(trade_page.order_history.row(order.order_id)).to_have_count(0)


@then("Orders & Deals should say there is no history")
def orders_and_deals_empty(trade_page: TradePage):
    expect(trade_page.order_history.orders_and_deals_empty).to_be_visible()


@then("Orders & Deals should not say there is no history")
def orders_and_deals_not_empty(trade_page: TradePage):
    expect(trade_page.order_history.orders_and_deals_empty).to_be_hidden()


@then("Positions History should not say there is no history")
def positions_history_not_empty(trade_page: TradePage):
    expect(trade_page.order_history.positions_history_empty).to_be_hidden()


def _expect_amount(cell, expected: Decimal):
    """Money to 2 decimals; a gain may carry a "+"."""
    expect(cell).to_have_text(re.compile(rf"^\+?{re.escape(f'{expected:.2f}')}$"))
