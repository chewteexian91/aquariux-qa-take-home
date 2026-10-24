"""Steps for the Open Positions table, and positions created through the API as a starting point."""
import re

from playwright.sync_api import expect
from pytest_bdd import given, parsers, then

from src.api.trading_api import TradingApi
from src.models.Order import Order
from src.pages.components.open_positions import NOT_SET
from src.pages.trade_page import TradePage
from tests.step_definitions.orders import let_tables_update, open_position
from tests.step_definitions.trading_data import CONTRACT_SIZE, DECIMALS, POSITION_SL_TP

PROFIT_FORMAT = re.compile(r"^[+-]?\d[\d,]*\.\d{2}$")  # "-3.00", "+6.00"
ROI_FORMAT = re.compile(r"^[+-]?\d[\d,]*\.\d{2}%$")  # "-1.34%"


# --- Setup through the API (before logging in, so the page loads with it) ---

@given(parsers.parse('I have a "{side}" position of "{volume}" lots on "{symbol}"'), target_fixture="order")
def have_position(trading_api: TradingApi, open_orders: list[Order], side: str, volume: str, symbol: str) -> Order:
    return open_position(trading_api, open_orders, symbol, side, volume)


@given(parsers.parse('I have a "{side}" position of "{volume}" lots on "{symbol}" with a Stop Loss and Take Profit'),
       target_fixture="order")
def have_position_with_sl_tp(trading_api: TradingApi, open_orders: list[Order], side: str, volume: str,
                             symbol: str) -> Order:
    stop_loss, take_profit = POSITION_SL_TP[symbol][side]
    return open_position(trading_api, open_orders, symbol, side, volume, stop_loss, take_profit)


@given(parsers.parse('I have {count:d} "{side}" positions of "{volume}" lots on "{symbol}"'))
def have_positions(trading_api: TradingApi, open_orders: list[Order], count: int, side: str, volume: str,
                   symbol: str):
    for _ in range(count):
        open_position(trading_api, open_orders, symbol, side, volume)


# --- The table ---

@then("my position should be listed in Open Positions as ordered")
def position_listed_as_ordered(trade_page: TradePage, order: Order):
    positions = trade_page.open_positions
    expect(positions.row(order.order_id)).to_be_visible()
    expect(positions.cell(order.order_id, "symbol")).to_have_text(order.symbol)
    expect(positions.cell(order.order_id, "order-type")).to_have_text(order.side.upper())
    expect(positions.cell(order.order_id, "volume")).to_have_text(order.volume)
    expect(positions.cell(order.order_id, "stop-loss")).to_have_text(order.stop_loss or NOT_SET)
    expect(positions.cell(order.order_id, "take-profit")).to_have_text(order.take_profit or NOT_SET)


@then("my position should be listed with its details")
def position_listed_with_details(trade_page: TradePage, order: Order):
    position_listed_as_ordered(trade_page, order)
    positions, order_id = trade_page.open_positions, order.order_id
    expect(positions.cell(order_id, "units")).to_have_text(_units(order, order.volume))
    expect(positions.cell(order_id, "entry-price")).to_have_text(order.entry_price)
    # Live values: only their format can be checked.
    expect(positions.cell(order_id, "current-price")).to_have_text(re.compile(rf"^\d+\.\d{{{DECIMALS[order.symbol]}}}$"))
    expect(positions.cell(order_id, "profit")).to_have_text(PROFIT_FORMAT)
    expect(positions.cell(order_id, "roi")).to_have_text(ROI_FORMAT)


@then(parsers.parse('my position should still be listed with "{volume}" lots'))
def position_still_listed_with_volume(trade_page: TradePage, order: Order, volume: str):
    let_tables_update(trade_page.page)
    position_listed_with_volume(trade_page, order, volume)


@then(parsers.parse('my position should be listed with "{volume}" lots'))
def position_listed_with_volume(trade_page: TradePage, order: Order, volume: str):
    positions = trade_page.open_positions
    expect(positions.row(order.order_id)).to_be_visible()
    expect(positions.cell(order.order_id, "volume")).to_have_text(volume)
    expect(positions.cell(order.order_id, "units")).to_have_text(_units(order, volume))


@then("my position should no longer be listed")
def position_not_listed(trade_page: TradePage, order: Order):
    # The row was there: the step before used one of its buttons.
    expect(trade_page.open_positions.row(order.order_id)).to_have_count(0)


@then(parsers.parse('my position should show Stop Loss "{stop_loss}" and Take Profit "{take_profit}"'))
def position_shows_sl_tp(trade_page: TradePage, order: Order, stop_loss: str, take_profit: str):
    positions = trade_page.open_positions
    expect(positions.row(order.order_id)).to_be_visible()
    expect(positions.cell(order.order_id, "stop-loss")).to_have_text(stop_loss)
    expect(positions.cell(order.order_id, "take-profit")).to_have_text(take_profit)


@then("my position should still show its first Stop Loss and Take Profit")
def position_shows_first_sl_tp(trade_page: TradePage, order: Order):
    let_tables_update(trade_page.page)
    stop_loss, take_profit = POSITION_SL_TP[order.symbol][order.side]
    position_shows_sl_tp(trade_page, order, stop_loss, take_profit)


@then("my position should show its new Stop Loss and Take Profit")
def position_shows_new_sl_tp(trade_page: TradePage, order: Order):
    position_shows_sl_tp(trade_page, order, order.stop_loss or NOT_SET, order.take_profit or NOT_SET)


def _units(order: Order, volume: str) -> str:
    return f"{round(float(volume) * CONTRACT_SIZE[order.symbol]):,}"
