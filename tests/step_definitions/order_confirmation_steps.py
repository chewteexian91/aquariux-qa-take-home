"""Steps for the Order Confirmation dialog: checking it, confirming, and confirming into a failure."""
from urllib.parse import urlparse

from playwright.sync_api import Request, Response, Route, expect
from pytest_bdd import parsers, then, when

from src.api.trading_api import MARKET_ORDER, placed_order_no
from src.models.Order import Order
from src.pages.trade_page import TradePage
from tests.step_definitions.live_prices import (PRICE_LAG_POINTS, STOP_LOSS, TAKE_PROFIT, live_check,
                                                number, point, price_from_points)

# Ways to make the order request fail in the browser. None of them reaches the server.
FAILURES = {
    "network error": lambda route: route.abort("failed"),
    "blocked request": lambda route: route.abort("blockedbyclient"),
    "timeout": lambda route: route.abort("timedout"),
    # What a gateway in front of the API sends when the API is down: a page, not the API's JSON.
    "502 gateway page": lambda route: route.fulfill(
        status=502, content_type="text/html", body="<html><body><h1>502 Bad Gateway</h1></body></html>"),
    "503 gateway page": lambda route: route.fulfill(
        status=503, content_type="text/plain", body="Service Unavailable"),
}


@then("the order confirmation should show my order")
def confirmation_shows_order(trade_page: TradePage, order: Order):
    dialog = trade_page.order_confirmation
    expect(dialog.symbol).to_have_text(order.symbol)
    expect(dialog.order_type).to_have_text(order.side.upper())
    expect(dialog.value("Volume")).to_have_text(order.volume)
    expect(dialog.value("Fill Policy")).to_have_text(order.fill_policy)
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
    with trade_page.page.expect_response(_is_market_order) as answer:
        trade_page.order_confirmation.confirm()
    try:
        order.order_id = placed_order_no(answer.value)
    except RuntimeError as rejected:
        # The site turning the order down is a failed check, not a broken test.
        raise AssertionError(f"The order was not placed: {rejected}") from None
    open_orders.append(order)  # closed again in teardown, pass or fail


@when(parsers.parse('I confirm the order and the server answers {status:d} with "{message}"'))
def confirm_into_error_answer(trade_page: TradePage, status: int, message: str):
    _confirm_into(trade_page, lambda route: route.fulfill(
        status=status, json={"code": str(status), "message": message}))


@when(parsers.parse('I confirm the order and the request fails with a "{failure}"'))
def confirm_into_failure(trade_page: TradePage, failure: str):
    if failure not in FAILURES:
        raise ValueError(f"Unknown failure '{failure}'. Use one of: {', '.join(FAILURES)}")
    _confirm_into(trade_page, FAILURES[failure])


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


def _confirm_into(trade_page: TradePage, fail):
    """Confirm, with the order request failed in the browser instead of sent."""
    page = trade_page.page

    def handle(route: Route):
        if route.request.method == "POST":
            fail(route)
        else:
            route.fallback()

    # Left in place until the scenario ends: each scenario gets a new page.
    page.route(f"**{MARKET_ORDER}", handle)
    with page.expect_request(_is_market_order):
        trade_page.order_confirmation.confirm()


def _is_market_order(message: Request | Response) -> bool:
    request = message.request if isinstance(message, Response) else message
    return request.method == "POST" and urlparse(request.url).path == MARKET_ORDER
