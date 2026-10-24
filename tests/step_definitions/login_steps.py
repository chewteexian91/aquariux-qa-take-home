"""Steps for the login page, shared by any feature that starts from it."""
import json
import re

from playwright.sync_api import expect
from pytest_bdd import given, parsers, then, when

from src.datas.user_data import get_user
from src.pages.login_page import LoginPage
from src.pages.trade_page import TradePage


@given("I am on the login page")
def open_login_page(login_page: LoginPage):
    login_page.open()


@given(parsers.parse('I am logged in as the "{role}" user'))
def logged_in_as(login_page: LoginPage, trade_page: TradePage, saved_logins, role: str):
    # Reuse the run's saved login (conftest.SavedLogins): the token lives in localStorage, which
    # is filled in before the site's own scripts run.
    page = trade_page.page
    page.context.add_init_script(_RESTORE_STORAGE_JS % json.dumps(saved_logins.storage(role)))
    trade_page.open()
    loaded = trade_page.open_symbol.filter(has_text=re.compile(r"\S"))
    expect(loaded.or_(login_page.login_button)).to_be_visible(timeout=PAGE_LOAD_TIMEOUT_MS)
    if login_page.login_button.is_visible():
        # The saved session was logged out (too many sessions on the account): log in again.
        user = get_user(role)
        login_page.login(user.username, user.password)
        expect(page).to_have_url(re.compile(re.escape(TradePage.URL)))
        saved_logins.remember(role, page)
    expect(page).to_have_url(re.compile(re.escape(TradePage.URL)))
    # The open symbol shows once symbol data has loaded, so searches have data to search.
    expect(trade_page.open_symbol).not_to_be_empty()


# The trade page sometimes takes longer than expect's default 5 s to load its symbols.
PAGE_LOAD_TIMEOUT_MS = 20_000

# Sets the saved items only where the site hasn't set its own, so a refreshed token survives reloads.
_RESTORE_STORAGE_JS = """(items => {
  for (const [key, value] of Object.entries(items))
    if (localStorage.getItem(key) === null) localStorage.setItem(key, value);
})(%s);"""


@when(parsers.parse('I log in as the "{role}" user'))
def log_in_as(login_page: LoginPage, role: str):
    user = get_user(role)
    login_page.login(user.username, user.password)


@when(parsers.parse('I log in as the "{role}" user with password "{password}"'))
def log_in_with_password(login_page: LoginPage, role: str, password: str):
    login_page.login(get_user(role).username, password)


# parsers.re (not parse) so empty values from the Examples table still match.
@when(parsers.re(r'I enter account ID "(?P<account_id>[^"]*)" and password "(?P<password>[^"]*)"'))
def enter_credentials(login_page: LoginPage, account_id: str, password: str):
    login_page.enter_account_id(account_id).enter_password(password)


@then("I should see the invalid credentials error")
def see_invalid_credentials_error(login_page: LoginPage):
    expect(login_page.error_message).to_be_visible()


@then("I should remain on the login page")
def remain_on_login_page(login_page: LoginPage):
    expect(login_page.page).to_have_url(re.compile(re.escape(LoginPage.URL)))
    expect(login_page.login_button).to_be_visible()


@then("the log in button should be disabled")
def login_button_disabled(login_page: LoginPage):
    expect(login_page.login_button).to_be_disabled()
