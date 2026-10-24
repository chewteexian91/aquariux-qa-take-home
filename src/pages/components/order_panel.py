from datetime import date

from playwright.sync_api import Locator, Page

from src.pages.components.form_fields import choose, error_under, exact, options, selected, type_into

# Title of the collapsible Trade Details section (no test id).
TRADE_DETAILS_TITLE = "Trade Details"
# The expiry time picker's buttons and heading (no test ids).
TIME_PICKER_OK = "OK"
TIME_PICKER_HOUR = "Hour"
# What the Place button reads while the panel loads a symbol, and while that symbol's market is closed.
# The site shows them in capitals (CSS); this is the text in the page.
PANEL_LOADING_MSG = "Stay Tuned"
MARKET_CLOSED_MSG = "Market Closed"

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
    """Order panel on the right of the trade page, for the symbol that is open.

    Two tabs: Trade (the order form) and, while one-click trading is on, One-Click.
    """

    def __init__(self, page: Page):
        self.page = page

        # Tabs
        self.trade_tab = page.get_by_test_id("tab-trade")
        self.specification_tab = page.get_by_test_id("tab-specification")
        self.one_click_tab = page.get_by_test_id("tab-one-click-trading")

        # The form itself. The Edit Order dialog repeats some of its fields (Price, expiry), so
        # those are looked up inside it.
        self.place_order_button = page.get_by_test_id("trade-button-order")
        self.form = self.place_order_button.locator(
            "xpath=ancestor::*[.//*[@data-testid='trade-dropdown-order-type']][1]")
        # While the market is closed, the Place button is disabled and reads "Market Closed". On the
        # One-Click tab the same button takes the place of BUY / SELL. For about 0.1s after a symbol
        # is selected it reads "Stay Tuned" instead.
        self.panel_loading = self.place_order_button.filter(has_text=exact(PANEL_LOADING_MSG))
        self.market_closed = self.place_order_button.filter(has_text=exact(MARKET_CLOSED_MSG))

        # Side and live prices
        self.buy_button = page.get_by_test_id("trade-button-order-buy")
        self.sell_button = page.get_by_test_id("trade-button-order-sell")
        self.buy_price = page.get_by_test_id("trade-live-buy-price")
        self.sell_price = page.get_by_test_id("trade-live-sell-price")

        # Order settings
        self.order_type_dropdown = page.get_by_test_id("trade-dropdown-order-type")
        self.order_type_options = options(self.order_type_dropdown)
        self.fill_policy_dropdown = page.get_by_test_id("trade-dropdown-fill-policy")
        self.fill_policy_options = options(self.fill_policy_dropdown)
        # The One-Click tab's volume box has the same test id; only one tab is shown at a time.
        self.volume_input = page.get_by_test_id("trade-input-volume")
        self.swap_to_units_button = page.get_by_test_id("trade-swap-to-units")
        self.volume_info_label = page.get_by_test_id("trade-volume-info-label")
        self.volume_info_min_value = page.get_by_test_id("trade-volume-info-min-value")
        self.one_point_equals_label = page.get_by_test_id("trade-one-point-equal-label")

        # Pending orders (Limit, Stop, Stop Limit). Price inputs have no test ids.
        self.price_input = self.form.locator("input[name='price']")
        self.stop_limit_price_input = self.form.locator("input[name='priceTrigger']")
        self.expiry_dropdown = self.form.get_by_test_id("trade-dropdown-expiry")
        self.expiry_options = options(self.expiry_dropdown)
        # Shown for Specified Date (and Time). Both start at the server's date and time.
        self.expiry_date_box = self.form.get_by_test_id("trade-input-expiry-date")
        self.expiry_time_box = self.form.get_by_test_id("trade-input-expiry-time")
        # The time picker (Hour and Minute dropdowns, Clear / OK) has no test ids.
        self.time_picker_ok = page.get_by_role("button", name=exact(TIME_PICKER_OK))
        self.time_picker = self.time_picker_ok.locator(
            f"xpath=ancestor::*[.//*[normalize-space(text())='{TIME_PICKER_HOUR}']][1]")

        # Stop loss / take profit
        self.stop_loss_price_input = page.get_by_test_id("trade-input-stoploss-price")
        self.stop_loss_points_input = page.get_by_test_id("trade-input-stoploss-points")
        self.take_profit_price_input = page.get_by_test_id("trade-input-takeprofit-price")
        self.take_profit_points_input = page.get_by_test_id("trade-input-takeprofit-points")

        # Validation messages under a field (e.g. "Minimum volume is 0.1."). Empty or missing when
        # there is no error.
        self.volume_error = error_under(self.volume_input)
        self.price_error = error_under(self.price_input)
        self.stop_limit_price_error = error_under(self.stop_limit_price_input)
        self.stop_loss_price_error = error_under(self.stop_loss_price_input)
        self.take_profit_price_error = error_under(self.take_profit_price_input)

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

        # One-Click tab: BUY / SELL trade at once, with the volume above.
        self.one_click_buy_button = page.get_by_test_id("trade-button-oct-order-buy")
        self.one_click_sell_button = page.get_by_test_id("trade-button-oct-order-sell")

    def trade_detail_value(self, label: str) -> Locator:
        """The value of a Trade Details row, by its label (e.g. "Potential Loss")."""
        return self.page.get_by_test_id(TRADE_DETAILS_ROWS[label]).locator("xpath=./div[2]")

    def expiry_calendar_day(self, day: date) -> Locator:
        """A day in the open expiry calendar (a react-calendar). Past days are disabled buttons."""
        label = f"{day:%B} {day.day}, {day.year}"  # "October 26, 2026"
        return self.page.locator("button.react-calendar__tile").filter(
            has=self.page.locator(f"abbr[aria-label='{label}']"))

    def choose_buy(self):
        self.buy_button.click()
        return self

    def choose_sell(self):
        self.sell_button.click()
        return self

    def choose_order_type(self, order_type: str):
        choose(self.order_type_dropdown, order_type)
        return self

    def open_order_type_list(self):
        selected(self.order_type_dropdown).click()
        return self

    def choose_fill_policy(self, fill_policy: str):
        choose(self.fill_policy_dropdown, fill_policy)
        return self

    def open_fill_policy_list(self):
        selected(self.fill_policy_dropdown).click()
        return self

    def choose_expiry(self, expiry: str):
        choose(self.expiry_dropdown, expiry)
        return self

    def open_expiry_list(self):
        selected(self.expiry_dropdown).click()
        return self

    def set_volume(self, volume: str):
        type_into(self.volume_input, volume)
        return self

    def set_price(self, price: str):
        type_into(self.price_input, price)
        return self

    def set_stop_limit_price(self, price: str):
        type_into(self.stop_limit_price_input, price)
        return self

    # A price is typed key by key and the field is then left without moving into its Points box.
    # While the Points box has focus, or after a price is pasted in one go, the site moves the
    # price with the market, so the order goes out with a different price (docs/site-notes.md).
    def set_stop_loss(self, price: str | None = None, points: str | None = None):
        if price is not None:
            type_into(self.stop_loss_price_input, price)
        if points is not None:
            type_into(self.stop_loss_points_input, points)
        return self

    def set_take_profit(self, price: str | None = None, points: str | None = None):
        if price is not None:
            type_into(self.take_profit_price_input, price)
        if points is not None:
            type_into(self.take_profit_points_input, points)
        return self

    def open_expiry_calendar(self):
        selected(self.expiry_date_box).click()
        return self

    def pick_expiry_date(self, day: date):
        self.open_expiry_calendar()
        self.expiry_calendar_day(day).click()
        return self

    def set_expiry_hour(self, hour: str):
        """Pick the hour ("00" to "23") in the expiry time picker and press OK."""
        selected(self.expiry_time_box).click()
        selected(self.time_picker).click()  # the Hour dropdown
        # The hour list opens outside the picker; its options are the only visible "00"…"23" texts.
        self.page.get_by_text(exact(hour)).filter(visible=True).last.click()
        self.time_picker_ok.click()
        return self

    def open_trade_details(self):
        if self.trade_details_expanded.count() == 0:
            self.trade_details_title.click()
        return self

    def place_order(self):
        self.place_order_button.click()
        return self

    def open_one_click_tab(self):
        self.one_click_tab.click()
        return self

    def open_trade_tab(self):
        self.trade_tab.click()
        return self

    def buy_with_one_click(self):
        self.one_click_buy_button.click()
        return self

    def sell_with_one_click(self):
        self.one_click_sell_button.click()
        return self

    def snapshot(self) -> dict:
        """Live prices, SL/TP inputs and Trade Details values (as shown), all read at the same moment."""
        return self.page.evaluate(_SNAPSHOT_JS, TRADE_DETAILS_ROWS)
