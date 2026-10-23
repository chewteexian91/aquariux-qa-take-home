from playwright.sync_api import Page


class BasePage:
    # Path relative to base_url (set in pytest.ini or via --base-url).
    URL: str = "/"

    def __init__(self, page: Page):
        self.page = page

    def open(self):
        self.page.goto(self.URL)
        return self
