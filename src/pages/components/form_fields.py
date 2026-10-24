"""How to fill the site's form fields, shared by the order panel and the dialogs.

Not a component: plain functions on locators.
"""
import re

from playwright.sync_api import Locator


def type_into(box: Locator, value: str):
    """Type a value key by key, then leave the field so the site formats and checks it.

    Blur rather than Tab: Tab from a Stop Loss / Take Profit price moves into its Points box, and
    the price then follows the market (docs/site-notes.md).
    """
    box.clear()
    if value:
        box.press_sequentially(value)
    box.blur()


def error_under(box: Locator) -> Locator:
    """The validation message under a field. No test ids: it's the element after the input's wrapper."""
    return box.locator("xpath=../following-sibling::div[1]")


def selected(dropdown: Locator) -> Locator:
    """The box showing a dropdown's selected value (its first focusable element)."""
    return dropdown.locator("[tabindex='0']").first


def options(dropdown: Locator) -> Locator:
    """A dropdown's options while it's open. They sit in its second child and have no test ids."""
    return dropdown.locator("xpath=./div[2]//div[@tabindex='0']")


def choose(dropdown: Locator, option: str):
    # The open list also contains the selected value, so leave it alone if it's already chosen.
    if selected(dropdown).inner_text().strip() == option:
        return
    if not options(dropdown).first.is_visible():
        selected(dropdown).click()
    options(dropdown).filter(has_text=re.compile(rf"^{re.escape(option)}$")).click()


def exact(text: str) -> re.Pattern:
    return re.compile(rf"^{re.escape(text)}$")


def dialog_titled(page_or_locator, title: str) -> Locator:
    """A dialog with no test ids, found by its title: the smallest element holding the title and
    the dialog's buttons."""
    return page_or_locator.get_by_text(exact(title)).locator("xpath=ancestor::*[.//button][1]")


def button(container, name: str) -> Locator:
    """A button by its text, ignoring case (the site shows "CONFIRM" for a "Confirm" button)."""
    return container.get_by_role("button", name=re.compile(rf"^{re.escape(name)}$", re.I))
