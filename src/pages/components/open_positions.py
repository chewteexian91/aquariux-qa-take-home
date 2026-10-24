from playwright.sync_api import Locator, Page

from src.pages.components.form_fields import exact

# What the Take Profit / Stop Loss cells show when the position has none (stored as 0).
NOT_SET = "--"
# Bulk Close menu items (no test ids).
BULK_CLOSE_OPTIONS = ("All Positions", "Profitable Positions", "Loss Positions")


class OpenPositions:
    """Open Positions table at the bottom of the trade page, with Bulk Close.

    Right after a page load the table says "You have no open positions." for a moment, even when
    there are some. So wait for a specific row rather than trusting an empty table.
    """

    def __init__(self, page: Page):
        self.page = page
        self.tab = page.get_by_test_id("tab-asset-order-type-open-positions")
        self.rows = page.get_by_test_id("asset-open-list-item")
        self.bulk_close_button = page.get_by_test_id("bulk-close")

    def open(self):
        self.tab.click()
        return self

    def row(self, order_id: str) -> Locator:
        # Exact match, so "2352327" doesn't also match "23523270".
        order_no = self.page.get_by_test_id("asset-open-column-order-id").filter(has_text=exact(order_id))
        return self.rows.filter(has=order_no)

    def cell(self, order_id: str, column: str) -> Locator:
        """A cell of the position's row, by the end of its test id: "symbol", "stop-loss", "take-profit"…"""
        return self.row(order_id).get_by_test_id(f"asset-open-column-{column}")

    def edit_button(self, order_id: str) -> Locator:
        return self.row(order_id).get_by_test_id("asset-open-button-edit")

    def close_button(self, order_id: str) -> Locator:
        return self.row(order_id).get_by_test_id("asset-open-button-close")

    def bulk_close_option(self, option: str) -> Locator:
        return self.page.get_by_text(exact(option))

    def edit(self, order_id: str):
        self.edit_button(order_id).click()
        return self

    def close(self, order_id: str):
        self.close_button(order_id).click()
        return self

    def bulk_close(self, option: str):
        """Open Bulk Close and pick an option. A confirmation dialog opens."""
        self.bulk_close_button.click()
        self.bulk_close_option(option).click()
        return self

    def profits(self) -> dict[str, str]:
        """Profit/Loss as shown for every listed position, by Order No., read at one moment."""
        return self.page.evaluate("""() => Object.fromEntries(
            [...document.querySelectorAll('[data-testid="asset-open-list-item"]')].map(row => [
              row.querySelector('[data-testid="asset-open-column-order-id"]')?.innerText.trim(),
              row.querySelector('[data-testid="asset-open-column-profit"]')?.innerText.trim()]))""")
