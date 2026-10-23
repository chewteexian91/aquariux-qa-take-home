"""Steps for the login page, shared by any feature that starts from it."""
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
def logged_in_as(login_page: LoginPage, trade_page: TradePage, role: str):
    user = get_user(role)
    login_page.open().login(user.username, user.password)
    expect(trade_page.page).to_have_url(re.compile(re.escape(TradePage.URL)))
    # The open symbol shows once symbol data has loaded, so searches have data to search.
    expect(trade_page.open_symbol).not_to_be_empty()


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
