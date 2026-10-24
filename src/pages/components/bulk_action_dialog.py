from playwright.sync_api import Page

from src.pages.components.form_fields import button

# Every bulk dialog asks "Would you like to close / delete all …?".
QUESTION_START = "Would you like"


class BulkActionDialog:
    """The "Bulk Close" / "Bulk Delete" confirmation dialog ("Up to 30 … can be closed.").

    Only some of its buttons have test ids (`bulk-close-modal-button-submit-all` …), so they're found
    by their text inside the dialog.
    """

    def __init__(self, page: Page):
        self.page = page
        self.question = page.get_by_text(QUESTION_START)
        self.root = self.question.locator("xpath=ancestor::*[.//button][1]")
        self.confirm_button = button(self.root, "Confirm")
        self.cancel_button = button(self.root, "Cancel")

    def confirm(self):
        self.confirm_button.click()
        return self

    def cancel(self):
        self.cancel_button.click()
        return self
