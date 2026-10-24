"""Steps for the "Confirm To Close Position" dialog."""
from urllib.parse import urlparse

from playwright.sync_api import Request, expect
from pytest_bdd import parsers, then, when

from src.api.trading_api import CLOSE_OR_DELETE
from src.models.Order import Order
from src.pages.trade_page import TradePage
from tests.step_definitions.orders import send_and_finish


@when("I open the close dialog for my position")
def open_close_dialog(trade_page: TradePage, order: Order):
    trade_page.open_positions.close(order.order_id)
    expect(trade_page.close_position_dialog.volume_input).to_be_visible()


@when(parsers.parse('I close "{volume}" lots of my position'))
def close_part(trade_page: TradePage, order: Order, volume: str):
    open_close_dialog(trade_page, order)
    trade_page.close_position_dialog.set_volume(volume)
    confirm_close(trade_page)


@when("I close my whole position using Max")
def close_all_with_max(trade_page: TradePage, order: Order):
    open_close_dialog(trade_page, order)
    trade_page.close_position_dialog.use_max()
    expect(trade_page.close_position_dialog.volume_input).to_have_value(order.volume)
    confirm_close(trade_page)


# parsers.re (not parse) so an empty volume still matches.
@when(parsers.re(r'I enter a close volume of "(?P<volume>[^"]*)"'))
def enter_close_volume(trade_page: TradePage, volume: str):
    trade_page.close_position_dialog.set_volume(volume)


@when("I clear the close volume")
def clear_close_volume(trade_page: TradePage):
    trade_page.close_position_dialog.set_volume("")


@when(parsers.parse('I press "{which}" in the close dialog'))
def press_min_or_max(trade_page: TradePage, which: str):
    dialog = trade_page.close_position_dialog
    {"Min": dialog.use_min, "Max": dialog.use_max}[which]()


@when("I confirm the close")
def confirm_close(trade_page: TradePage):
    send_and_finish(trade_page.page, _is_close, trade_page.close_position_dialog.confirm)


@when("I cancel the close")
def cancel_close(trade_page: TradePage):
    trade_page.close_position_dialog.cancel()
    expect(trade_page.close_position_dialog.volume_input).to_be_hidden()


@then(parsers.parse('the close volume should read "{volume}"'))
def close_volume_reads(trade_page: TradePage, volume: str):
    expect(trade_page.close_position_dialog.volume_input).to_have_value(volume)


@then(parsers.parse('I should see the close volume error "{error}"'))
def close_volume_error(trade_page: TradePage, error: str):
    expect(trade_page.close_position_dialog.volume_error).to_have_text(error)


@then("I should not be able to confirm the close")
def cannot_confirm_close(trade_page: TradePage):
    expect(trade_page.close_position_dialog.confirm_button).to_be_disabled()


@then("I should be able to confirm the close")
def can_confirm_close(trade_page: TradePage):
    expect(trade_page.close_position_dialog.confirm_button).to_be_enabled()


def _is_close(request: Request) -> bool:
    return request.method == "PUT" and urlparse(request.url).path == CLOSE_OR_DELETE
