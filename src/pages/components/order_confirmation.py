import re

from playwright.sync_api import Locator, Page


class OrderConfirmation:
    """The Order Confirmation dialog that opens after "Place … Order" (or "Update Position").

    It isn't shown while one-click trading is on. Rows the order doesn't have (e.g. no Stop Loss)
    are left out.
    """

    def __init__(self, page: Page):
        self.page = page
        self.symbol = page.get_by_test_id("trade-confirmation-symbol")
        self.order_type = page.get_by_test_id("trade-confirmation-order-type")  # BUY, SELL, BUY LIMIT…
        self.labels = page.get_by_test_id("trade-confirmation-label")
        self.confirm_button = page.get_by_test_id("trade-confirmation-button-confirm")
        self.cancel_button = page.get_by_test_id("trade-confirmation-button-close")

    def label(self, label: str) -> Locator:
        return self.labels.filter(has_text=re.compile(rf"^{re.escape(label)}$"))

    def value(self, label: str) -> Locator:
        """The value next to a label, e.g. value("Stop Loss") -> "77.500"."""
        return self.label(label).locator("xpath=following-sibling::*[@data-testid='trade-confirmation-value'][1]")

    def confirm(self):
        self.confirm_button.click()
        return self

    def cancel(self):
        self.cancel_button.click()
        return self
