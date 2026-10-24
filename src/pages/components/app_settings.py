import re

from playwright.sync_api import Page

from src.pages.components.form_fields import exact

# The one-click terms dialog has no test ids.
TERMS_TITLE = "Terms and Conditions"
AGREE_BUTTON = "Agree and continue"
DECLINE_BUTTON = "Cancel"


class AppSettings:
    """The settings menu behind the gear icon (top right), with the One Click Trading switch.

    One-click trading is saved on the server for the account, so it changes every session.
    """

    def __init__(self, page: Page):
        self.page = page
        self.trigger = page.get_by_test_id("app-setting-dropdown-trigger")
        # The switch has a different test id when on.
        self.one_click_off = page.get_by_test_id("toggle-oct")
        self.one_click_on = page.get_by_test_id("toggle-oct-checked")
        self.one_click_switch = self.one_click_off.or_(self.one_click_on)

        # Shown when the switch is turned on.
        # The terms text links to "Terms and Conditions" too; the title comes first.
        self.terms_title = page.get_by_text(exact(TERMS_TITLE)).first
        self.terms_dialog = self.terms_title.locator("xpath=ancestor::*[.//button][1]")
        self.agree_button = page.get_by_role("button", name=re.compile(rf"^{AGREE_BUTTON}$", re.I))
        self.decline_button = self.terms_dialog.get_by_role("button", name=re.compile(rf"^{DECLINE_BUTTON}$", re.I))

    def open(self):
        if not self.one_click_switch.is_visible():
            self.trigger.click()
        self.one_click_switch.wait_for()
        return self

    def close(self):
        if self.one_click_switch.is_visible():
            self.trigger.click()
        self.one_click_switch.wait_for(state="hidden")
        return self

    def turn_on_one_click(self):
        """Click the switch while it's off. The terms dialog opens; agree or decline next."""
        self.open().one_click_off.click()
        return self

    def turn_off_one_click(self):
        self.open().one_click_on.click()
        return self

    def agree_to_terms(self):
        self.agree_button.click()
        return self

    def decline_terms(self):
        self.decline_button.click()
        return self
