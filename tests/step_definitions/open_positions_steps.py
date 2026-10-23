"""Steps for the Open Positions table."""
from playwright.sync_api import expect
from pytest_bdd import then

from src.models.Order import Order
from src.pages.components.open_positions import NOT_SET
from src.pages.trade_page import TradePage


@then("my position should be listed in Open Positions as ordered")
def position_listed_as_ordered(trade_page: TradePage, order: Order):
    positions = trade_page.open_positions
    expect(positions.row(order.order_id)).to_be_visible()
    expect(positions.cell(order.order_id, "symbol")).to_have_text(order.symbol)
    expect(positions.cell(order.order_id, "order-type")).to_have_text(order.side.upper())
    expect(positions.cell(order.order_id, "volume")).to_have_text(order.volume)
    expect(positions.cell(order.order_id, "stop-loss")).to_have_text(order.stop_loss or NOT_SET)
    expect(positions.cell(order.order_id, "take-profit")).to_have_text(order.take_profit or NOT_SET)
