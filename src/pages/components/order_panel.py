import re

from playwright.sync_api import Locator, Page

# Title of the collapsible Trade Details section (no test id).
TRADE_DETAILS_TITLE = "Trade Details"

# Test ids of the Trade Details rows, by the label the site shows. Each row holds a label and a value.
TRADE_DETAILS_ROWS = {
    "Trade Volume": "trade-details-trade-size",
    "Est. Margin Required": "trade-details-margin-required",
    "Amount Per Tick": "trade-details-amount-per-tick",
    "Potential Loss": "trade-details-potential-loss",
    "Potential Gain": "trade-details-potential-gain",
    "Risk:Reward": "trade-details-risk-reward",
}

# Reads the prices, inputs and Trade Details in one go, so they all come from the same moment.
# Live prices tick several times a second, and the details are worked out from them.
_SNAPSHOT_JS = """(rows) => {
  const el = id => document.querySelector(`[data-testid="${id}"]`);
  const text = id => (el(id)?.innerText ?? '').trim();
  const value = id => el(id)?.value ?? '';
  const details = {};
  for (const [label, id] of Object.entries(rows)) details[label] = (el(id)?.lastElementChild?.innerText ?? '').trim();
  return {
    buy: text('trade-live-buy-price'), sell: text('trade-live-sell-price'),
    point: text('trade-one-point-equal-label'),
    stop_loss: value('trade-input-stoploss-price'), stop_loss_points: value('trade-input-stoploss-points'),
    take_profit: value('trade-input-takeprofit-price'), take_profit_points: value('trade-input-takeprofit-points'),
    details,
  };
}"""


class OrderPanel:
    """Order panel on the right of the trade page, for the symbol that is open."""

    def __init__(self, page: Page):
        self.page = page

        # Tabs
        self.trade_tab = page.get_by_test_id("tab-trade")
        self.specification_tab = page.get_by_test_id("tab-specification")

        # Side and live prices
        self.buy_button = page.get_by_test_id("trade-button-order-buy")
        self.sell_button = page.get_by_test_id("trade-button-order-sell")
        self.buy_price = page.get_by_test_id("trade-live-buy-price")
        self.sell_price = page.get_by_test_id("trade-live-sell-price")

        # Order settings
        self.order_type_dropdown = page.get_by_test_id("trade-dropdown-order-type")
        self.fill_policy_dropdown = page.get_by_test_id("trade-dropdown-fill-policy")
        # The open list sits in the dropdown's second child; its options have no test ids.
        self.fill_policy_options = self.fill_policy_dropdown.locator("xpath=./div[2]//div[@tabindex='0']")
        self.volume_input = page.get_by_test_id("trade-input-volume")
        self.swap_to_units_button = page.get_by_test_id("trade-swap-to-units")
        self.volume_info_label = page.get_by_test_id("trade-volume-info-label")
        self.volume_info_min_value = page.get_by_test_id("trade-volume-info-min-value")
        self.one_point_equals_label = page.get_by_test_id("trade-one-point-equal-label")

        # Stop loss / take profit
        self.stop_loss_price_input = page.get_by_test_id("trade-input-stoploss-price")
        self.stop_loss_points_input = page.get_by_test_id("trade-input-stoploss-points")
        self.take_profit_price_input = page.get_by_test_id("trade-input-takeprofit-price")
        self.take_profit_points_input = page.get_by_test_id("trade-input-takeprofit-points")

        # Validation messages under a field (e.g. "Minimum volume is 0.1."). No test ids: each is
        # the element right after the input's wrapper. Empty or missing when there is no error.
        self.volume_error = _error_under(self.volume_input)
        self.stop_loss_price_error = _error_under(self.stop_loss_price_input)
        self.take_profit_price_error = _error_under(self.take_profit_price_input)

        # Trade details (collapsed by default). Each row holds its label and value.
        self.trade_details = page.get_by_test_id("trade-details")
        self.trade_details_title = self.trade_details.get_by_text(TRADE_DETAILS_TITLE)
        # The header and its arrow get the class "expanded" while the section is open.
        self.trade_details_expanded = self.trade_details.locator(".expanded")
        self.trade_details_pin = page.get_by_test_id("trade-details-pin-icon")
        self.trade_volume = page.get_by_test_id("trade-details-trade-size")
        self.margin_required = page.get_by_test_id("trade-details-margin-required")
        self.amount_per_tick = page.get_by_test_id("trade-details-amount-per-tick")
        self.potential_loss = page.get_by_test_id("trade-details-potential-loss")
        self.potential_gain = page.get_by_test_id("trade-details-potential-gain")
        self.risk_reward = page.get_by_test_id("trade-details-risk-reward")

        # Submit ("Place Buy Order" / "Place Sell Order"). It stays enabled while a field shows an
        # error; clicking it then just doesn't open the Order Confirmation.
        self.place_order_button = page.get_by_test_id("trade-button-order")

    def trade_detail_value(self, label: str) -> Locator:
        """The value of a Trade Details row, by its label (e.g. "Potential Loss")."""
        return self.page.get_by_test_id(TRADE_DETAILS_ROWS[label]).locator("xpath=./div[2]")

    def choose_buy(self):
        self.buy_button.click()
        return self

    def choose_sell(self):
        self.sell_button.click()
        return self

    def choose_order_type(self, order_type: str):
        _choose(self.order_type_dropdown, order_type)
        return self

    def choose_fill_policy(self, fill_policy: str):
        _choose(self.fill_policy_dropdown, fill_policy)
        return self

    def open_fill_policy_list(self):
        _selected(self.fill_policy_dropdown).click()
        return self

    def set_volume(self, volume: str):
        _type(self.volume_input, volume)
        return self

    # A price is typed key by key and the field is then left without moving into its Points box.
    # While the Points box has focus, or after a price is pasted in one go, the site moves the
    # price with the market, so the order goes out with a different price (docs/site-notes.md).
    def set_stop_loss(self, price: str | None = None, points: str | None = None):
        if price is not None:
            _type(self.stop_loss_price_input, price)
        if points is not None:
            _type(self.stop_loss_points_input, points)
        return self

    def set_take_profit(self, price: str | None = None, points: str | None = None):
        if price is not None:
            _type(self.take_profit_price_input, price)
        if points is not None:
            _type(self.take_profit_points_input, points)
        return self

    def open_trade_details(self):
        if self.trade_details_expanded.count() == 0:
            self.trade_details_title.click()
        return self

    def place_order(self):
        self.place_order_button.click()
        return self

    def snapshot(self) -> dict:
        """Live prices, SL/TP inputs and Trade Details values (as shown), all read at the same moment."""
        return self.page.evaluate(_SNAPSHOT_JS, TRADE_DETAILS_ROWS)


def _type(box: Locator, value: str):
    box.clear()
    box.press_sequentially(value)
    # Leaving the field makes the site format and check the value. Blur rather than Tab: Tab from
    # a price moves into its Points box, and the price then follows the market.
    box.blur()


def _error_under(box: Locator) -> Locator:
    return box.locator("xpath=../following-sibling::div[1]")


def _selected(dropdown: Locator) -> Locator:
    # The first focusable element is the box showing the selected value. The options come after it.
    return dropdown.locator("[tabindex='0']").first


def _choose(dropdown: Locator, option: str):
    # The open list also contains the selected value, so leave it alone if it's already chosen.
    if _selected(dropdown).inner_text().strip() == option:
        return
    _selected(dropdown).click()
    dropdown.locator("xpath=./div[2]//div[@tabindex='0']").filter(
        has_text=re.compile(rf"^{re.escape(option)}$")).click()
