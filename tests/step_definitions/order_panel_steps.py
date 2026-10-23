"""Steps for the order panel: filling in an order, its validation, and the Trade Details."""
import re
from decimal import Decimal

from playwright.sync_api import expect
from pytest_bdd import parsers, then, when

from src.models.Order import Order
from src.pages.components.order_panel import OrderPanel
from src.pages.trade_page import TradePage
from tests.step_definitions.live_prices import (BUY, PRICE_LAG_POINTS, SELL, STOP_LOSS, TAKE_PROFIT,
                                                entry_price, goes_above, live_check, number, point,
                                                price_from_points)

# Units in one lot, from the symbol's Specification tab ("Contract Size").
CONTRACT_SIZE = {"UKOIL": Decimal(1000)}
# The demo account's leverage (1:100, shown on the Assets page).
LEVERAGE = Decimal(100)
# Money in the Trade Details is shown to 2 decimals.
CENT = Decimal("0.01")
# After Place is clicked, the Order Confirmation normally opens well within this.
CONFIRMATION_WAIT_MS = 1500


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


@then("I should not be able to place the order")
def cannot_place_order(trade_page: TradePage):
    # Place stays enabled while a field shows an error. Clicking it should open nothing.
    trade_page.order_panel.place_order()
    trade_page.page.wait_for_timeout(CONFIRMATION_WAIT_MS)
    expect(trade_page.order_confirmation.confirm_button).to_be_hidden()


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
    errors = {"Volume": panel.volume_error, STOP_LOSS: panel.stop_loss_price_error,
              TAKE_PROFIT: panel.take_profit_price_error}
    return errors[field]


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
