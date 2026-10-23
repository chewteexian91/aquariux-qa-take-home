from playwright.sync_api import Page

from src.pages.base_page import BasePage
from src.pages.components.open_positions import OpenPositions
from src.pages.components.order_confirmation import OrderConfirmation
from src.pages.components.order_panel import OrderPanel
from src.pages.components.symbol_search import SymbolSearch


class TradePage(BasePage):
    URL = "/web/trade"

    def __init__(self, page: Page):
        super().__init__(page)
        self.account_info = page.get_by_test_id("account-info")
        self.account_type_tag = page.get_by_test_id("account-type-tag")
        # Symbol name above the chart: the symbol currently open for trading.
        self.open_symbol = page.get_by_test_id("symbol-overview-id")
        # Message banner at the top after an action, e.g. "Position has been created." or an error.
        # Gone again after about 5 seconds.
        self.toast = page.get_by_test_id("notification-box-description")

        self.symbol_search = SymbolSearch(page)
        self.order_panel = OrderPanel(page)
        self.order_confirmation = OrderConfirmation(page)
        self.open_positions = OpenPositions(page)
