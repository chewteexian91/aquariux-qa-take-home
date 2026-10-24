"""Steps for the Order Confirmation dialog: checking it, confirming, and confirming into a failure."""
from playwright.sync_api import expect
from pytest_bdd import parsers, then, when

from src.models.Order import Order
from src.pages.trade_page import TradePage
from tests.step_definitions.live_prices import (PRICE_LAG_POINTS, STOP_LOSS, TAKE_PROFIT, live_check,
                                                number, point, price_from_points)
from tests.step_definitions.orders import is_new_order, record_placed_order, send_and_finish
from tests.step_definitions.request_failures import answer_with, fail_requests, failure

# How the confirmation names a pending order's expiry date row.
EXPIRY_DATE_LABELS = {"Specified Date": "Expiry Date", "Specified Date and Time": "Expiry Date & Time"}


@then("the order confirmation should show my order")
def confirmation_shows_order(trade_page: TradePage, order: Order):
    dialog = trade_page.order_confirmation
    expect(dialog.symbol).to_have_text(order.symbol)
    expect(dialog.order_type).to_have_text(order.type_label)
    expect(dialog.value("Volume")).to_have_text(order.volume)
    expect(dialog.value("Fill Policy")).to_have_text(order.fill_policy)
    if order.order_type != "Market":
        _check_pending_rows(trade_page, order)
    for field in (STOP_LOSS, TAKE_PROFIT):
        price, points = (order.stop_loss, order.stop_loss_points) if field == STOP_LOSS else \
            (order.take_profit, order.take_profit_points)
        if points is not None:
            shown = _price_from_points_shown(trade_page, order, field, points)
            # From here the price is fixed: it's what the order is sent with.
            if field == STOP_LOSS:
                order.stop_loss = shown
            else:
                order.take_profit = shown
        elif price is None:
            # Checked after the rows above, so the dialog has finished drawing.
            expect(dialog.label(field)).to_have_count(0)
        else:
            expect(dialog.value(field)).to_have_text(price)


@when("I confirm the order")
def confirm_order(trade_page: TradePage, order: Order, open_orders: list[Order]):
    with trade_page.page.expect_response(is_new_order) as answer:
        trade_page.order_confirmation.confirm()
    record_placed_order(answer.value, order, open_orders)


@when("I try to confirm the order")
def try_to_confirm(trade_page: TradePage, order: Order, open_orders: list[Order]):
    """Confirm an order the site should turn down."""
    answer = send_and_finish(trade_page.page, is_new_order, trade_page.order_confirmation.confirm)
    if answer is not None and answer.ok:
        # Placed after all: the scenario fails, and teardown closes or deletes the order.
        record_placed_order(answer, order, open_orders)


@when(parsers.parse('I confirm the order, with its request mocked to answer {status:d} with "{message}"'))
def confirm_into_mocked_answer(trade_page: TradePage, status: int, message: str):
    _confirm_into(trade_page, answer_with(status, message))


@when(parsers.parse('I confirm the order, with its request mocked to fail with a "{kind}"'))
def confirm_into_mocked_failure(trade_page: TradePage, kind: str):
    _confirm_into(trade_page, failure(kind))


def _check_pending_rows(trade_page: TradePage, order: Order):
    dialog = trade_page.order_confirmation
    expect(dialog.value("Price")).to_have_text(order.price)
    if order.stop_limit_price is not None:
        expect(dialog.value("Stop Limit Price")).to_have_text(order.stop_limit_price)
    expect(dialog.value("Expiry")).to_have_text(order.expiry)
    if order.expiry in EXPIRY_DATE_LABELS:
        # The confirmation shows the time without seconds; the table adds ":00".
        expect(dialog.value(EXPIRY_DATE_LABELS[order.expiry])).to_have_text(order.expiry_date.removesuffix(":00"))


def _price_from_points_shown(trade_page: TradePage, order: Order, field: str, points: str) -> str:
    """Check a price entered as points is that far from the close price, and return it as shown."""
    value = trade_page.order_confirmation.value(field)
    expect(value).not_to_be_empty()

    def mismatch(snap: dict) -> str | None:
        expected, shown = price_from_points(snap, order.side, field, points), value.inner_text()
        if number(shown) is not None and abs(number(shown) - expected) <= PRICE_LAG_POINTS * point(snap):
            return None
        return (f"{field} in the confirmation should be {points} points from the market, about {expected}; "
                f"it shows {shown!r} (Buy {snap['buy']}, Sell {snap['sell']})")

    live_check(trade_page, mismatch)
    return value.inner_text()


def _confirm_into(trade_page: TradePage, handle):
    """Confirm, with the order request failed in the browser instead of sent."""
    page = trade_page.page
    fail_requests(page, "place market order", handle)
    with page.expect_request(is_new_order):
        trade_page.order_confirmation.confirm()
