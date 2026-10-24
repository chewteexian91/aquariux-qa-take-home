import re

from playwright.sync_api import Page

from src.pages.base_page import BasePage
from src.pages.components.app_settings import AppSettings
from src.pages.components.bulk_action_dialog import BulkActionDialog
from src.pages.components.close_position_dialog import ClosePositionDialog
from src.pages.components.delete_order_dialog import DeleteOrderDialog
from src.pages.components.edit_dialog import EditDialog
from src.pages.components.notifications import Notifications
from src.pages.components.open_positions import OpenPositions
from src.pages.components.order_confirmation import OrderConfirmation
from src.pages.components.order_history import OrderHistory
from src.pages.components.order_panel import OrderPanel
from src.pages.components.pending_orders import PendingOrders
from src.pages.components.symbol_search import SymbolSearch

SERVER_TIME_LABEL = "Server Time"


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
        # "Server Time : 2026-10-23 18:37:43" (top right, no test id). Expiry dates use this clock (UTC+3).
        self.server_time = page.get_by_text(re.compile(rf"^{SERVER_TIME_LABEL}"))
        # Checkbox above the tables: show only the open symbol's orders (a server setting).
        self.hide_other_symbols_off = page.get_by_test_id("hide-other-symbols-button")
        self.hide_other_symbols_on = page.get_by_test_id("hide-other-symbols-button-checked")

        self.app_settings = AppSettings(page)
        self.symbol_search = SymbolSearch(page)
        self.order_panel = OrderPanel(page)
        self.order_confirmation = OrderConfirmation(page)
        self.open_positions = OpenPositions(page)
        self.pending_orders = PendingOrders(page)
        self.edit_dialog = EditDialog(page)
        self.close_position_dialog = ClosePositionDialog(page)
        self.delete_order_dialog = DeleteOrderDialog(page)
        self.bulk_action_dialog = BulkActionDialog(page)
        self.order_history = OrderHistory(page)
        self.notifications = Notifications(page)

    def hide_other_symbols(self):
        self.hide_other_symbols_off.click()
        return self
