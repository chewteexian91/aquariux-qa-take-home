import re

from playwright.sync_api import Locator, Page

# What the Take Profit / Stop Loss cells show when the position has none (stored as 0).
NOT_SET = "--"


class OpenPositions:
    """Open Positions table at the bottom of the trade page.

    Right after a page load the table says "You have no open positions." for a moment, even when
    there are some. So wait for a specific row rather than trusting an empty table.
    """

    def __init__(self, page: Page):
        self.page = page
        self.rows = page.get_by_test_id("asset-open-list-item")

    def row(self, order_id: str) -> Locator:
        # Exact match, so "2352327" doesn't also match "23523270".
        order_no = self.page.get_by_test_id("asset-open-column-order-id").filter(
            has_text=re.compile(rf"^{re.escape(order_id)}$"))
        return self.rows.filter(has=order_no)

    def cell(self, order_id: str, column: str) -> Locator:
        """A cell of the position's row, by the end of its test id: "symbol", "stop-loss", "take-profit"…"""
        return self.row(order_id).get_by_test_id(f"asset-open-column-{column}")
