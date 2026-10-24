from playwright.sync_api import Page

from src.pages.components.form_fields import button, dialog_titled

TITLE = "Confirm To Delete Order"


class DeleteOrderDialog:
    """The "Confirm To Delete Order" dialog, opened by a pending order's Delete button. No test ids."""

    def __init__(self, page: Page):
        self.page = page
        self.root = dialog_titled(page, TITLE)
        self.confirm_button = button(self.root, "Confirm")
        self.cancel_button = button(self.root, "Cancel")

    def confirm(self):
        self.confirm_button.click()
        return self

    def cancel(self):
        self.cancel_button.click()
        return self
