from playwright.sync_api import Page

from src.pages.base_page import BasePage

INVALID_CREDENTIALS_MSG = "Invalid credentials, please try again."


class LoginPage(BasePage):
    URL = "/web/login"

    def __init__(self, page: Page):
        super().__init__(page)
        self.account_id_input = page.get_by_test_id("login-user-id")
        self.password_input = page.get_by_test_id("login-password")
        self.login_button = page.get_by_test_id("login-submit")
        # The error toast has no test id, so it is matched by its (English) text.
        self.error_message = page.get_by_text(INVALID_CREDENTIALS_MSG)

    def enter_account_id(self, account_id: str):
        self.account_id_input.fill(account_id)
        return self

    def enter_password(self, password: str):
        self.password_input.fill(password)
        return self

    def submit(self):
        self.login_button.click()
        return self

    def login(self, username: str, password: str):
        return self.enter_account_id(username).enter_password(password).submit()
