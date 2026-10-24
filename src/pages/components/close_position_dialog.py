from playwright.sync_api import Page

from src.pages.components.form_fields import button, dialog_titled, error_under, type_into

TITLE = "Confirm To Close Position"


class ClosePositionDialog:
    """The "Confirm To Close Position" dialog, opened by a position's Close button.

    Confirm stays disabled while the volume is empty or shows an error.
    """

    def __init__(self, page: Page):
        self.page = page
        self.root = dialog_titled(page, TITLE)
        # The order panel's volume box has the same name, so this one is looked up in the dialog.
        self.volume_input = self.root.locator("input[name='lotSize']")
        self.volume_error = error_under(self.volume_input)
        self.min_button = page.get_by_test_id("close-order-input-volume-static-min")
        self.max_button = page.get_by_test_id("close-order-input-volume-static-max")
        self.fill_policy = page.get_by_test_id("edit-dropdown-fill-policy")
        self.confirm_button = button(self.root, "Confirm")
        self.cancel_button = button(self.root, "Cancel")

    def set_volume(self, volume: str):
        type_into(self.volume_input, volume)
        return self

    def use_min(self):
        self.min_button.click()
        return self

    def use_max(self):
        self.max_button.click()
        return self

    def confirm(self):
        self.confirm_button.click()
        return self

    def cancel(self):
        self.cancel_button.click()
        return self
