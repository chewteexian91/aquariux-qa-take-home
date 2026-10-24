from playwright.sync_api import Locator, Page

from src.pages.components.form_fields import exact

# Empty states (no test ids). A failed load shows them too (docs/findings.md #13).
POSITIONS_HISTORY_EMPTY = "You have no order histories."
ORDERS_AND_DEALS_EMPTY = "You have no orders & deals history."


class OrderHistory:
    """The Positions History and Orders & Deals tabs at the bottom of the trade page.

    Both use the same row and cell test ids, show 30 rows per page (newest first) and share the
    date range picker. The default range is the last 30 days.
    """

    def __init__(self, page: Page):
        self.page = page
        self.positions_history_tab = page.get_by_test_id("tab-asset-order-type-history-positions-history")
        self.orders_and_deals_tab = page.get_by_test_id("tab-asset-order-type-history-orders-and-deals")
        self.rows = page.get_by_test_id("asset-history-position-list-item")
        self.positions_history_empty = page.get_by_text(exact(POSITIONS_HISTORY_EMPTY))
        self.orders_and_deals_empty = page.get_by_text(exact(ORDERS_AND_DEALS_EMPTY))

        self.date_range_button = page.get_by_test_id("orders-date-picker-icon-calendar")
        self.date_range_menu = page.get_by_test_id("orders-date-picker-dropdown")
        self.date_range_apply = page.get_by_test_id("orders-date-picker-button-apply")

    def open_positions_history(self):
        self.positions_history_tab.click()
        return self

    def open_orders_and_deals(self):
        self.orders_and_deals_tab.click()
        return self

    def row(self, order_id: str) -> Locator:
        """The row for an Order No. In Positions History that's the position's own number."""
        order_no = self.page.get_by_test_id("asset-history-column-order-id").filter(has_text=exact(order_id))
        return self.rows.filter(has=order_no)

    def cell(self, order_id: str, column: str) -> Locator:
        """A cell by the end of its test id: "state", "volume", "close-price", "profit"…"""
        return self.row(order_id).get_by_test_id(f"asset-history-column-{column}")

    def deal_row(self, order_id: str) -> Locator:
        """The first deal under an expanded Orders & Deals row (deal rows have no test ids)."""
        return self.row(order_id).locator("xpath=following-sibling::*[1]")

    def expand(self, order_id: str):
        self.row(order_id).get_by_test_id("asset-history-position-list-item-expand").click()
        return self

    def choose_date_range(self, preset: str):
        """Pick a preset date range ("Last 7 days", "Last year"…) and apply it."""
        self.date_range_button.click()
        self.date_range_menu.get_by_text(exact(preset)).click()
        self.date_range_apply.click()
        return self
