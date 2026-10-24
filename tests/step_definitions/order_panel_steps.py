"""Steps for the order panel: market and pending orders, the One-Click tab, validation, Trade Details."""
import re
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from playwright.sync_api import Request, expect
from pytest_bdd import parsers, then, when

from src.models.Order import Order
from src.pages.components.order_panel import OrderPanel
from src.pages.trade_page import TradePage
from tests.step_definitions.live_prices import (BUY, PRICE_LAG_POINTS, SELL, STOP_LOSS, TAKE_PROFIT,
                                                entry_price, goes_above, live_check, number, point,
                                                price_from_points)
from tests.step_definitions.orders import is_new_order, record_placed_order, server_today

PRICE, STOP_LIMIT_PRICE, VOLUME = "Price", "Stop Limit Price", "Volume"
SPECIFIED_DATE, SPECIFIED_DATE_AND_TIME, GOOD_TILL_DAY = "Specified Date", "Specified Date and Time", "Good Till Day"
# After a click that should send nothing, how long to watch for an order request.
NO_REQUEST_WAIT_MS = 1500

# Units in one lot, from the symbol's Specification tab ("Contract Size").
CONTRACT_SIZE = {"UKOIL": Decimal(1000)}
# The demo account's leverage (1:100, shown on the Assets page).
LEVERAGE = Decimal(100)
# Money in the Trade Details is shown to 2 decimals.
CENT = Decimal("0.01")
# After Place is clicked, the Order Confirmation normally opens well within this.
CONFIRMATION_WAIT_MS = 1500
# The order panel's open tab has the class "selected".
SELECTED_TAB = re.compile(r"\bselected\b")


@when(parsers.parse('I fill in a "{side}" market order for "{volume}" lots with "{fill_policy}"'),
      target_fixture="order")
def fill_in_market_order(trade_page: TradePage, side: str, volume: str, fill_policy: str) -> Order:
    panel = trade_page.order_panel.choose_order_type("Market")
    _choose_side(panel, side)
    panel.set_volume(volume).choose_fill_policy(fill_policy)
    return Order(symbol=trade_page.open_symbol.inner_text().strip(), side=side, volume=volume,
                 fill_policy=fill_policy)


@when(parsers.parse('I enter a volume of "{volume}"'))
def enter_volume(trade_page: TradePage, volume: str):
    trade_page.order_panel.set_volume(volume)


@when(parsers.parse('I set the Stop Loss price "{distance}" from the market'))
def stop_loss_price_from_market(trade_page: TradePage, order: Order, distance: str):
    order.stop_loss = _set_price_away(trade_page.order_panel, order.side, STOP_LOSS, _fraction(distance))


@when(parsers.parse('I set the Take Profit price "{distance}" from the market'))
def take_profit_price_from_market(trade_page: TradePage, order: Order, distance: str):
    order.take_profit = _set_price_away(trade_page.order_panel, order.side, TAKE_PROFIT, _fraction(distance))


@when(parsers.parse('I set the "{field}" price "{distance}" on the wrong side of the market'))
def price_on_wrong_side(trade_page: TradePage, order: Order, field: str, distance: str):
    _set_price_away(trade_page.order_panel, order.side, field, _fraction(distance), wrong_side=True)


@when(parsers.parse('I set the "{field}" price to "{price}"'))
def set_price(trade_page: TradePage, field: str, price: str):
    _set_price(trade_page.order_panel, field, price)


@when(parsers.parse('I set the Stop Loss "{distance}" from the market in points'))
def stop_loss_in_points(trade_page: TradePage, order: Order, distance: str):
    order.stop_loss_points = _set_points_away(trade_page.order_panel, order.side, STOP_LOSS, _fraction(distance))


@when(parsers.parse('I set the Take Profit "{distance}" from the market in points'))
def take_profit_in_points(trade_page: TradePage, order: Order, distance: str):
    order.take_profit_points = _set_points_away(trade_page.order_panel, order.side, TAKE_PROFIT,
                                                _fraction(distance))


@then("the Stop Loss and Take Profit prices should be worked out from the points")
def prices_from_points(trade_page: TradePage, order: Order):
    def mismatch(snap: dict) -> str | None:
        for field, price, points in ((STOP_LOSS, snap["stop_loss"], order.stop_loss_points),
                                     (TAKE_PROFIT, snap["take_profit"], order.take_profit_points)):
            expected = price_from_points(snap, order.side, field, points)
            if number(price) is None or abs(number(price) - expected) > PRICE_LAG_POINTS * point(snap):
                return (f"{field} {points} points from the market should be {expected}, the price box shows "
                        f"{price!r} (Buy {snap['buy']}, Sell {snap['sell']})")
        return None

    live_check(trade_page, mismatch)


@when("I place the order")
def place_order(trade_page: TradePage):
    trade_page.order_panel.place_order()


@when("I place the order with one-click trading on")
def place_order_one_click_on(trade_page: TradePage, order: Order, open_orders: list[Order]):
    # With one-click trading on, Place sends the order itself: no confirmation to confirm.
    with trade_page.page.expect_response(is_new_order) as answer:
        trade_page.order_panel.place_order()
    record_placed_order(answer.value, order, open_orders)


# --- Pending orders ---

@when(parsers.parse('I fill in a "{side}" "{order_type}" order for "{volume}" lots priced "{distance}" from the market'),
      target_fixture="order")
def fill_in_pending_order(trade_page: TradePage, side: str, order_type: str, volume: str, distance: str) -> Order:
    panel = trade_page.order_panel
    _choose_side(panel, side)
    panel.choose_order_type(order_type).set_volume(volume)
    price = _price_from_market(panel, side, distance)
    panel.set_price(price)
    return Order(symbol=trade_page.open_symbol.inner_text().strip(), side=side, volume=volume, order_type=order_type,
                 price=price, fill_policy="Return", expiry="Good Till Canceled")


@when("I clear the price")
def clear_price(trade_page: TradePage):
    trade_page.order_panel.set_price("")


@when(parsers.parse('I set the Stop Limit Price "{distance}" from the market'))
def set_stop_limit_price(trade_page: TradePage, order: Order, distance: str):
    order.stop_limit_price = _price_from_market(trade_page.order_panel, order.side, distance)
    trade_page.order_panel.set_stop_limit_price(order.stop_limit_price)


@when(parsers.parse('I choose a "{order_type}" order'))
def choose_order_type(trade_page: TradePage, order_type: str):
    trade_page.order_panel.choose_order_type(order_type)


@when(parsers.parse('I choose the expiry "{expiry}"'))
def choose_expiry(trade_page: TradePage, order: Order, expiry: str):
    panel = trade_page.order_panel
    panel.choose_expiry(expiry)
    order.expiry = expiry
    if expiry == GOOD_TILL_DAY:
        order.expiry_date = server_today(trade_page).isoformat()
    elif expiry in (SPECIFIED_DATE, SPECIFIED_DATE_AND_TIME):
        order.expiry_date = _expiry_shown(panel, expiry)


@when(parsers.parse('I pick an expiry date {days:d} days ahead'))
def pick_expiry_date(trade_page: TradePage, order: Order, days: int):
    panel = trade_page.order_panel
    # The box starts at the server's date.
    today = datetime.strptime(panel.expiry_date_box.inner_text().strip(), "%Y-%m-%d").date()
    day = today + timedelta(days=days)
    panel.pick_expiry_date(day)
    expect(panel.expiry_date_box).to_have_text(day.isoformat())
    order.expiry_date = _expiry_shown(panel, order.expiry)


@when("I set the expiry hour to one that has already passed today")
def set_past_expiry_hour(trade_page: TradePage):
    panel = trade_page.order_panel
    hour = int(panel.expiry_time_box.inner_text().strip().split(":")[0]) - 1
    if hour < 0:
        pytest.skip("It's just after midnight on the server's clock: no hour has passed yet today")
    panel.set_expiry_hour(f"{hour:02d}")
    expect(panel.expiry_time_box).to_have_text(re.compile(rf"^{hour:02d}:"))


@when(parsers.parse('I set the "{field}" price "{distance}" on the wrong side of my order\'s price'))
def price_on_wrong_side_of_order_price(trade_page: TradePage, order: Order, field: str, distance: str):
    price, fraction = Decimal(order.price), _fraction(distance)
    # A Buy's Stop Loss belongs below its price and its Take Profit above; this puts it the other way.
    above = not goes_above(order.side, field)
    wrong = (price * (1 + fraction if above else 1 - fraction)).quantize(price)  # same decimals as the price
    _set_price(trade_page.order_panel, field, str(wrong))


@when("I open the order type list")
def open_order_type_list(trade_page: TradePage):
    trade_page.order_panel.open_order_type_list()


@then(parsers.parse('the order types offered should be "{order_types}"'))
def order_types_offered(trade_page: TradePage, order_types: str):
    expect(trade_page.order_panel.order_type_options).to_have_text(order_types.split(", "))


@when("I open the expiry list")
def open_expiry_list(trade_page: TradePage):
    trade_page.order_panel.open_expiry_list()


@then(parsers.parse('the expiry options offered should be "{expiries}"'))
def expiries_offered(trade_page: TradePage, expiries: str):
    expect(trade_page.order_panel.expiry_options).to_have_text(expiries.split(", "))


@when("I open the expiry calendar")
def open_expiry_calendar(trade_page: TradePage):
    trade_page.order_panel.open_expiry_calendar()


@then("only days from tomorrow should be selectable as the expiry date")
def only_from_tomorrow_selectable(trade_page: TradePage):
    panel = trade_page.order_panel
    # The box starts at today's date on the server's clock.
    today = datetime.strptime(panel.expiry_date_box.inner_text().strip(), "%Y-%m-%d").date()
    expect(panel.expiry_calendar_day(today + timedelta(days=1))).to_be_enabled()
    expect(panel.expiry_calendar_day(today)).to_be_disabled()


# --- One-Click tab ---

@when("I open the One-Click tab")
def open_one_click_tab(trade_page: TradePage):
    trade_page.order_panel.open_one_click_tab()
    expect(trade_page.order_panel.one_click_buy_button).to_be_visible()


@when("I open the Trade tab")
def open_trade_tab(trade_page: TradePage):
    trade_page.order_panel.open_trade_tab()
    expect(trade_page.order_panel.place_order_button).to_be_visible()


@when(parsers.parse('I place a "{side}" order for "{volume}" lots with one click'), target_fixture="order")
def one_click_order(trade_page: TradePage, open_orders: list[Order], side: str, volume: str) -> Order:
    panel = trade_page.order_panel
    panel.set_volume(volume)
    button = panel.one_click_buy_button if side == BUY else panel.one_click_sell_button
    with trade_page.page.expect_response(is_new_order) as answer:
        button.click()
    order = Order(symbol=trade_page.open_symbol.inner_text().strip(), side=side, volume=volume)
    record_placed_order(answer.value, order, open_orders)
    return order


# parsers.re (not parse) so an empty volume still matches.
@when(parsers.re(r'I enter "(?P<volume>[^"]*)" lots on the One-Click tab'))
def enter_one_click_volume(trade_page: TradePage, volume: str):
    trade_page.order_panel.set_volume(volume)


@when("I try to buy with one click")
def try_one_click_buy(trade_page: TradePage, order_requests: list[Request]):
    trade_page.order_panel.buy_with_one_click()


@then("no order should have been sent")
def no_order_sent(trade_page: TradePage, order_requests: list[Request]):
    trade_page.page.wait_for_timeout(NO_REQUEST_WAIT_MS)
    assert not order_requests, f"An order was sent: {[r.post_data for r in order_requests]}"


@then("no order confirmation should have opened")
def no_confirmation(trade_page: TradePage):
    expect(trade_page.order_confirmation.confirm_button).to_be_hidden()


@then(parsers.parse('the volume should read "{volume}"'))
def volume_reads(trade_page: TradePage, volume: str):
    expect(trade_page.order_panel.volume_input).to_have_value(volume)


@then(parsers.parse('I should not see a "{field}" error'))
def no_field_error(trade_page: TradePage, field: str):
    expect(_error_of(trade_page.order_panel, field).filter(has_text=re.compile(r"\S"))).to_have_count(0)


@then("I should not be able to place the order")
def cannot_place_order(trade_page: TradePage):
    # Place stays enabled while a field shows an error. Clicking it should open nothing.
    trade_page.order_panel.place_order()
    trade_page.page.wait_for_timeout(CONFIRMATION_WAIT_MS)
    expect(trade_page.order_confirmation.confirm_button).to_be_hidden()


# --- Market closed ---

@then("the order panel should say the market is closed")
def panel_says_market_closed(trade_page: TradePage):
    expect(trade_page.order_panel.market_closed).to_be_visible()


@then("the Place button should be disabled")
def place_button_disabled(trade_page: TradePage):
    expect(trade_page.order_panel.place_order_button).to_be_disabled()


@then("I should not be able to buy or sell with one click")
def no_one_click_buy_or_sell(trade_page: TradePage):
    panel = trade_page.order_panel
    # On the One-Click tab, or BUY / SELL would be missing only because the Trade tab is showing.
    expect(panel.one_click_tab).to_have_class(SELECTED_TAB)
    expect(panel.one_click_buy_button).to_have_count(0)
    expect(panel.one_click_sell_button).to_have_count(0)


@then(parsers.parse('I should see the "{field}" error "{error}"'))
def see_field_error(trade_page: TradePage, field: str, error: str):
    expect(_error_of(trade_page.order_panel, field)).to_have_text(error)


@then(parsers.parse('I should see a "{field}" error'))
def see_any_field_error(trade_page: TradePage, field: str):
    expect(_error_of(trade_page.order_panel, field)).to_have_text(re.compile(r"\S"))


@when("I open the fill policy list")
def open_fill_policy_list(trade_page: TradePage):
    trade_page.order_panel.open_fill_policy_list()


@then(parsers.parse('the fill policies offered should be "{fill_policies}"'))
def fill_policies_offered(trade_page: TradePage, fill_policies: str):
    expect(trade_page.order_panel.fill_policy_options).to_have_text(fill_policies.split(", "))


# --- Trade Details ---

@when("I open the Trade Details")
def open_trade_details(trade_page: TradePage):
    panel = trade_page.order_panel.open_trade_details()
    expect(panel.trade_details_expanded.first).to_be_attached()
    # The details start at 0.00 and are worked out once the order has a volume.
    expect(panel.trade_detail_value("Trade Volume")).not_to_have_text("0.00")


@then("the Trade Volume should be the units times the entry price")
def trade_volume_is_units_times_price(trade_page: TradePage, order: Order):
    _check_detail(trade_page, "Trade Volume", lambda snap: _units(order) * entry_price(snap, order.side),
                  _price_lag(order))


@then("the Est. Margin Required should be the Trade Volume at 1:100 leverage")
def margin_is_trade_volume_over_leverage(trade_page: TradePage):
    _check_detail(trade_page, "Est. Margin Required", lambda snap: _shown(snap, "Trade Volume") / LEVERAGE)


@then("the Amount Per Tick should be the units times one point")
def amount_per_tick_is_units_times_point(trade_page: TradePage, order: Order):
    _check_detail(trade_page, "Amount Per Tick", lambda snap: _units(order) * point(snap))


@then("the Potential Loss should be what the Stop Loss would lose")
def potential_loss_at_stop_loss(trade_page: TradePage, order: Order):
    _check_detail(trade_page, "Potential Loss", lambda snap: _profit_at(order, order.stop_loss, snap),
                  _price_lag(order))


@then("the Potential Gain should be what the Take Profit would gain")
def potential_gain_at_take_profit(trade_page: TradePage, order: Order):
    _check_detail(trade_page, "Potential Gain", lambda snap: _profit_at(order, order.take_profit, snap),
                  _price_lag(order))


@then("the Risk:Reward should be the gain over the loss")
def risk_reward_is_gain_over_loss(trade_page: TradePage):
    def mismatch(snap: dict) -> str | None:
        shown = snap["details"]["Risk:Reward"]
        gain, loss = _shown(snap, "Potential Gain"), _shown(snap, "Potential Loss")
        if gain is None or not loss:
            return f"No gain and loss to work out a ratio from: {snap['details']}"
        expected = gain / abs(loss)
        match = re.fullmatch(r"1 : (\d+(?:\.\d+)?)", shown)
        if match and abs(Decimal(match.group(1)) - expected) <= CENT:
            return None
        return f'Risk:Reward should be "1 : {expected:.2f}", the site shows "{shown}" ({snap["details"]})'

    live_check(trade_page, mismatch)


# parsers.re (not parse) so an empty value still matches, e.g. Risk:Reward with no SL/TP.
@then(parsers.re(r'the Trade Details should show "(?P<label>[^"]+)" "(?P<value>[^"]*)"'))
def trade_detail_shows(trade_page: TradePage, label: str, value: str):
    expect(trade_page.order_panel.trade_detail_value(label)).to_have_text(value)


# --- Helpers ---

def _choose_side(panel: OrderPanel, side: str):
    if side == BUY:
        panel.choose_buy()
    elif side == SELL:
        panel.choose_sell()
    else:
        raise ValueError(f"Unknown side '{side}'. Use {BUY} or {SELL}.")


def _set_price(panel: OrderPanel, field: str, price: str):
    if field == STOP_LOSS:
        panel.set_stop_loss(price=price)
    elif field == TAKE_PROFIT:
        panel.set_take_profit(price=price)
    else:
        raise ValueError(f"Unknown field '{field}'. Use {STOP_LOSS} or {TAKE_PROFIT}.")


def _set_price_away(panel: OrderPanel, side: str, field: str, fraction: Decimal, wrong_side: bool = False) -> str:
    """Type a price `fraction` away from the market, on the field's correct side (or the wrong one)."""
    snap = panel.snapshot()
    market, one_point = entry_price(snap, side), point(snap)
    above = goes_above(side, field) != wrong_side
    price = str((market * (1 + fraction if above else 1 - fraction)).quantize(one_point))
    _set_price(panel, field, price)
    return price


def _set_points_away(panel: OrderPanel, side: str, field: str, fraction: Decimal) -> str:
    """Type a distance in points, `fraction` of the price. Returns the points typed."""
    snap = panel.snapshot()
    points = str((entry_price(snap, side) * fraction / point(snap)).to_integral_value())
    if field == STOP_LOSS:
        panel.set_stop_loss(points=points)
        expect(panel.stop_loss_price_input).not_to_have_value("")
    else:
        panel.set_take_profit(points=points)
        expect(panel.take_profit_price_input).not_to_have_value("")
    return points


def _error_of(panel: OrderPanel, field: str):
    errors = {VOLUME: panel.volume_error, STOP_LOSS: panel.stop_loss_price_error,
              TAKE_PROFIT: panel.take_profit_price_error, PRICE: panel.price_error,
              STOP_LIMIT_PRICE: panel.stop_limit_price_error}
    return errors[field]


def _price_from_market(panel: OrderPanel, side: str, distance: str) -> str:
    """A price `distance` ("-20%", "+19%") away from the side's market price, to the symbol's point."""
    snap = panel.snapshot()
    fraction = Decimal(distance.rstrip("%")) / 100
    return str((entry_price(snap, side) * (1 + fraction)).quantize(point(snap)))


def _expiry_shown(panel: OrderPanel, expiry: str) -> str:
    """The expiry date as the Pending Orders table will show it: "2026-10-26" or "2026-10-27 18:43:00"."""
    day = panel.expiry_date_box.inner_text().strip()
    if expiry == SPECIFIED_DATE_AND_TIME:
        return f"{day} {panel.expiry_time_box.inner_text().strip()}:00"
    return day


def _fraction(distance: str) -> Decimal:
    """ "30%" -> 0.30 """
    return Decimal(distance.rstrip("%")) / 100


def _units(order: Order) -> Decimal:
    return Decimal(order.volume) * CONTRACT_SIZE[order.symbol]


def _shown(snap: dict, label: str) -> Decimal | None:
    return number(snap["details"][label])


def _profit_at(order: Order, close_at: str, snap: dict) -> Decimal:
    """Profit (negative for a loss) if the position opened now and closed at `close_at`."""
    direction = 1 if order.side == BUY else -1
    return (Decimal(close_at) - entry_price(snap, order.side)) * _units(order) * direction


def _price_lag(order: Order):
    """How far a Trade Details value worked out from the live price may be off."""
    return lambda snap: CENT + PRICE_LAG_POINTS * point(snap) * _units(order)


def _check_detail(trade_page: TradePage, label: str, expected_of, tolerance_of=lambda snap: CENT):
    def mismatch(snap: dict) -> str | None:
        expected, shown, tolerance = expected_of(snap), snap["details"][label], tolerance_of(snap)
        if number(shown) is not None and abs(number(shown) - expected) <= tolerance:
            return None
        return (f'{label} should be {expected:.2f} (± {tolerance:.2f}), the site shows "{shown}" '
                f'(Buy {snap["buy"]}, Sell {snap["sell"]}, details {snap["details"]})')

    live_check(trade_page, mismatch)
