"""Steps for the Edit Position / Edit Order dialog and confirming a change."""
from decimal import Decimal
from urllib.parse import urlparse

from playwright.sync_api import Request, expect
from pytest_bdd import parsers, then, when

from src.api.trading_api import MARKET_ORDER, PENDING_ORDER
from src.models.Order import Order
from src.pages.components.edit_dialog import EditDialog
from src.pages.components.form_fields import type_into
from src.pages.components.open_positions import NOT_SET
from src.pages.trade_page import TradePage
from tests.step_definitions.live_prices import STOP_LOSS, TAKE_PROFIT, entry_price, goes_above, point, steady_snapshot
from tests.step_definitions.orders import server_today, send_and_finish
from tests.step_definitions.trading_data import EDITED_BUY_LIMIT, NEW_POSITION_SL_TP

# After Update is clicked, the Order Confirmation normally opens well within this.
CONFIRMATION_WAIT_MS = 1500
# How long the Edit Order dialog may take to fill itself in again after a list refresh.
RESET_SETTLE_MS = 1000


# --- Positions ---

@when("I change my position's Stop Loss and Take Profit")
def change_position_sl_tp(trade_page: TradePage, order: Order):
    stop_loss, take_profit = NEW_POSITION_SL_TP[order.symbol][order.side]
    _edit_position(trade_page, order).set_stop_loss(stop_loss).set_take_profit(take_profit).update()
    order.stop_loss, order.take_profit = stop_loss, take_profit


@when("I clear my position's Stop Loss and Take Profit")
def clear_position_sl_tp(trade_page: TradePage, order: Order):
    _edit_position(trade_page, order).set_stop_loss("").set_take_profit("").update()
    order.stop_loss = order.take_profit = None


@when(parsers.parse('I set my position\'s "{field}" price "{distance}" on the wrong side of the market'))
def position_price_on_wrong_side(trade_page: TradePage, order: Order, field: str, distance: str):
    # The market price comes from the order panel, which shows the open symbol. Read it before the
    # dialog opens: while it's open the panel's live prices read empty.
    if trade_page.open_symbol.inner_text().strip() != order.symbol:
        trade_page.symbol_search.search(order.symbol).select(order.symbol)
    snap = steady_snapshot(trade_page)
    market, fraction = entry_price(snap, order.side), Decimal(distance.rstrip("%")) / 100
    above = not goes_above(order.side, field)
    price = str((market * (1 + fraction if above else 1 - fraction)).quantize(point(snap)))
    _set(_edit_position(trade_page, order), field, price)


@when(parsers.parse('I set my position\'s "{field}" price to "{price}"'))
def position_price_to(trade_page: TradePage, order: Order, field: str, price: str):
    _set(_edit_position(trade_page, order), field, price)


# --- Pending orders ---

@when("I change my order's price, Stop Loss, Take Profit and expiry")
def change_pending_order(trade_page: TradePage, order: Order):
    price, stop_loss, take_profit = EDITED_BUY_LIMIT
    dialog = _edit_order(trade_page, order)
    dialog.set_price(price).set_stop_loss(stop_loss).set_take_profit(take_profit).choose_expiry("Good Till Day")
    _retype_if_reset(trade_page, dialog, {dialog.price_input: price, dialog.stop_loss_price_input: stop_loss,
                                          dialog.take_profit_price_input: take_profit})
    dialog.update()
    order.price, order.stop_loss, order.take_profit = price, stop_loss, take_profit
    order.expiry, order.expiry_date = "Good Till Day", server_today(trade_page).isoformat()


@when(parsers.parse('I start changing my order\'s price to "{price}"'))
def start_changing_pending_price(trade_page: TradePage, order: Order, price: str):
    _edit_order(trade_page, order).set_price(price)


@when(parsers.parse('I change my order\'s price to "{price}"'))
def change_pending_price(trade_page: TradePage, order: Order, price: str):
    _edit_order(trade_page, order).set_price(price).update()


@when(parsers.parse('I set my order\'s "{field}" price "{distance}" on the wrong side of its price'))
def pending_price_on_wrong_side(trade_page: TradePage, order: Order, field: str, distance: str):
    dialog = _edit_order(trade_page, order)
    price, fraction = Decimal(order.price), Decimal(distance.rstrip("%")) / 100
    above = not goes_above(order.side, field)
    _set(dialog, field, str((price * (1 + fraction if above else 1 - fraction)).quantize(price)))


# --- Either ---

@when("I cancel the edit")
def cancel_edit(trade_page: TradePage):
    trade_page.edit_dialog.cancel()
    expect(trade_page.edit_dialog.update_button).to_be_hidden()


@when("I confirm the change")
def confirm_change(trade_page: TradePage):
    send_and_finish(trade_page.page, _is_change, trade_page.order_confirmation.confirm)


@then(parsers.parse('I should see the edit "{field}" error "{error}"'))
def see_edit_error(trade_page: TradePage, field: str, error: str):
    expect(_error_of(trade_page.edit_dialog, field)).to_have_text(error)


@then("I should not be able to update")
def cannot_update(trade_page: TradePage):
    # Update stays enabled while a field shows an error. Clicking it should open nothing.
    trade_page.edit_dialog.update()
    trade_page.page.wait_for_timeout(CONFIRMATION_WAIT_MS)
    expect(trade_page.order_confirmation.confirm_button).to_be_hidden()


@then("the order confirmation should show the new Stop Loss and Take Profit")
def confirmation_shows_new_sl_tp(trade_page: TradePage, order: Order):
    dialog = trade_page.order_confirmation
    expect(dialog.symbol).to_have_text(order.symbol)
    expect(dialog.value("Volume")).to_have_text(order.volume)
    for field, price in ((STOP_LOSS, order.stop_loss), (TAKE_PROFIT, order.take_profit)):
        if price is None:
            expect(dialog.label(field)).to_have_count(0)
        else:
            expect(dialog.value(field)).to_have_text(price)


@then("the order confirmation should show my changed order")
def confirmation_shows_changed_order(trade_page: TradePage, order: Order):
    dialog = trade_page.order_confirmation
    expect(dialog.order_type).to_have_text(order.type_label)
    expect(dialog.value("Price")).to_have_text(order.price)
    expect(dialog.value(STOP_LOSS)).to_have_text(order.stop_loss or NOT_SET)
    expect(dialog.value(TAKE_PROFIT)).to_have_text(order.take_profit or NOT_SET)
    expect(dialog.value("Expiry")).to_have_text(order.expiry)


def _edit_position(trade_page: TradePage, order: Order) -> EditDialog:
    trade_page.open_positions.edit(order.order_id)
    expect(trade_page.edit_dialog.order_id).to_have_text(order.order_id)
    return trade_page.edit_dialog


def _edit_order(trade_page: TradePage, order: Order) -> EditDialog:
    trade_page.pending_orders.edit(order.order_id)
    expect(trade_page.edit_dialog.order_id).to_have_text(order.order_id)
    # The dialog fills in the order's values just after it opens, over anything typed before that.
    expect(trade_page.edit_dialog.price_input).to_have_value(order.price)
    return trade_page.edit_dialog


def _retype_if_reset(trade_page: TradePage, dialog: EditDialog, typed: dict):
    """Type the values again if the dialog put the order's own values back.

    Right after the page loads, the order list refreshes once more, and an open Edit Order dialog
    fills itself in again from it, over what was typed (seen with the price and Stop Loss).
    """
    trade_page.page.wait_for_timeout(RESET_SETTLE_MS)
    for box, value in typed.items():
        if box.input_value() != value:
            type_into(box, value)
    for box, value in typed.items():
        expect(box).to_have_value(value)


def _set(dialog: EditDialog, field: str, price: str):
    setters = {STOP_LOSS: dialog.set_stop_loss, TAKE_PROFIT: dialog.set_take_profit, "Price": dialog.set_price}
    setters[field](price)


def _error_of(dialog: EditDialog, field: str):
    errors = {STOP_LOSS: dialog.stop_loss_price_error, TAKE_PROFIT: dialog.take_profit_price_error,
              "Price": dialog.price_error}
    return errors[field]


def _is_change(request: Request) -> bool:
    return request.method == "PATCH" and urlparse(request.url).path in (MARKET_ORDER, PENDING_ORDER)
