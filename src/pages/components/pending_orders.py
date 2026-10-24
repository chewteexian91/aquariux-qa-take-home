from playwright.sync_api import Locator, Page

from src.pages.components.form_fields import exact

# Bulk Delete menu items (no test ids).
BULK_DELETE_OPTIONS = ("All Orders", "Limit Orders", "Stop Orders", "Stop Limit Orders")


class PendingOrders:
    """Pending Orders table at the bottom of the trade page, with Bulk Delete.

    Like Open Positions, it says it's empty for a moment after a page load, so wait for a
    specific row rather than trusting an empty table.
    """

    def __init__(self, page: Page):
        self.page = page
        self.tab = page.get_by_test_id("tab-asset-order-type-pending-orders")
        self.rows = page.get_by_test_id("asset-pending-list-item")
        self.bulk_delete_button = page.get_by_test_id("bulk-delete")

    def open(self):
        self.tab.click()
        return self

    def row(self, order_id: str) -> Locator:
        # Exact match, so "2352327" doesn't also match "23523270".
        order_no = self.page.get_by_test_id("asset-pending-column-order-id").filter(has_text=exact(order_id))
        return self.rows.filter(has=order_no)

    def cell(self, order_id: str, column: str) -> Locator:
        """A cell of the order's row, by the end of its test id: "order-type", "expiry-date", "entry-price"…"""
        return self.row(order_id).get_by_test_id(f"asset-pending-column-{column}")

    # The row buttons reuse the Open Positions test ids, so they're looked up inside the row.
    def edit_button(self, order_id: str) -> Locator:
        return self.row(order_id).get_by_test_id("asset-open-button-edit")

    def delete_button(self, order_id: str) -> Locator:
        return self.row(order_id).get_by_test_id("asset-open-button-close")

    def bulk_delete_option(self, option: str) -> Locator:
        """A Bulk Delete menu item. Kinds with no orders are greyed out (cursor "not-allowed")."""
        return self.page.get_by_text(exact(option))

    def edit(self, order_id: str):
        self.edit_button(order_id).click()
        return self

    def delete(self, order_id: str):
        self.delete_button(order_id).click()
        return self

    def open_bulk_delete_menu(self):
        self.bulk_delete_button.click()
        return self

    def bulk_delete(self, option: str):
        """Open Bulk Delete and pick an option. A confirmation dialog opens."""
        self.open_bulk_delete_menu()
        self.bulk_delete_option(option).click()
        return self
