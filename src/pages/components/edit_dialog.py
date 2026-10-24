from playwright.sync_api import Page

from src.pages.components.form_fields import choose, error_under, type_into


class EditDialog:
    """The "Edit Position" and "Edit Order" dialogs, opened by a row's pencil.

    Edit Position has the test id `edit-confirmation-modal`, Edit Order has none, so the dialog is
    found from its Update button. Its Stop Loss / Take Profit inputs reuse the order panel's test
    ids, so they're looked up inside the dialog. Update opens the Order Confirmation.
    """

    def __init__(self, page: Page):
        self.page = page
        self.update_button = page.get_by_test_id("edit-button-order")  # "UPDATE POSITION" / "CONFIRM"
        self.cancel_button = page.get_by_test_id("edit-button-cancel")
        self.root = self.update_button.locator("xpath=ancestor::*[.//*[@data-testid='edit-symbol-value']][1]")

        self.symbol = page.get_by_test_id("edit-symbol-value")
        self.order_type = page.get_by_test_id("edit-order-type-value")
        self.order_id = page.get_by_test_id("edit-order-id-value")
        self.volume = page.get_by_test_id("edit-volume-value")
        self.units = page.get_by_test_id("edit-units-value")

        self.price_input = self.root.locator("input[name='price']")  # Edit Order only
        self.expiry_dropdown = page.get_by_test_id("edit-dropdown-expiry")  # Edit Order only
        self.stop_loss_price_input = self.root.get_by_test_id("trade-input-stoploss-price")
        self.take_profit_price_input = self.root.get_by_test_id("trade-input-takeprofit-price")

        self.price_error = error_under(self.price_input)
        self.stop_loss_price_error = error_under(self.stop_loss_price_input)
        self.take_profit_price_error = error_under(self.take_profit_price_input)

    def set_price(self, price: str):
        type_into(self.price_input, price)
        return self

    def set_stop_loss(self, price: str):
        type_into(self.stop_loss_price_input, price)
        return self

    def set_take_profit(self, price: str):
        type_into(self.take_profit_price_input, price)
        return self

    def choose_expiry(self, expiry: str):
        choose(self.expiry_dropdown, expiry)
        return self

    def update(self):
        self.update_button.click()
        return self

    def cancel(self):
        self.cancel_button.click()
        return self
