import re

from playwright.sync_api import Locator, Page

from src.pages.components.form_fields import button, exact

EMPTY = "No new notifications."


class Notifications:
    """The notifications panel behind the bell icon (top right).

    The Positions tab lists "Position Created" and "Position Closed" items, newest first. They
    carry the position's Order No., closes too.
    """

    def __init__(self, page: Page):
        self.page = page
        self.bell = page.get_by_test_id("notification-selector")
        self.panel = page.get_by_test_id("notification-dropdown-result")
        self.positions_tab = page.get_by_test_id("tab-notification-type-order")
        self.items = page.get_by_test_id("notification-list-result-item")
        self.empty = self.panel.get_by_text(exact(EMPTY))

        self.details = page.get_by_test_id("notification-order-details-modal")
        self.details_close_button = button(self.details, "Close")

    def open(self):
        if not self.panel.is_visible():
            self.bell.click()
        return self

    def items_for(self, order_id: str, title: str) -> Locator:
        """Items with this title ("Position Created" / "Position Closed") for an Order No."""
        meta = self.page.get_by_test_id("notification-list-result-item-meta").filter(
            has_text=re.compile(rf"Order No\. {re.escape(order_id)}$"))
        heading = self.page.get_by_test_id("notification-list-result-item-title").filter(has_text=exact(title))
        return self.items.filter(has=meta).filter(has=heading)

    def details_value(self, label: str) -> Locator:
        """A value in the Order Details dialog, by its label ("Volume", "Entry Price"…). No test ids."""
        return self.details.get_by_text(exact(label)).locator("xpath=following-sibling::*[1]")

    def open_details(self, item: Locator):
        item.click()
        return self

    def close_details(self):
        self.details_close_button.click()
        return self
