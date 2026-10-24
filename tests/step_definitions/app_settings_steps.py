"""Steps for the settings menu: switching one-click trading on and off."""
from playwright.sync_api import expect
from pytest_bdd import given, then, when

from src.api.trading_api import TradingApi
from src.pages.trade_page import TradePage


@given("one-click trading is on")
def one_click_trading_on(account_settings: TradingApi):
    # Set before logging in, so the page loads with it. account_settings switches it off afterwards.
    account_settings.set_one_click_trading(True)


@when("I turn on one-click trading")
def turn_on_one_click(trade_page: TradePage, account_settings: TradingApi):
    trade_page.app_settings.turn_on_one_click()
    expect(trade_page.app_settings.terms_title).to_be_visible()


@when("I agree to the one-click trading terms")
def agree_to_terms(trade_page: TradePage):
    trade_page.app_settings.agree_to_terms()


@when("I decline the one-click trading terms")
def decline_terms(trade_page: TradePage):
    trade_page.app_settings.decline_terms()
    expect(trade_page.app_settings.terms_title).to_be_hidden()


@when("I turn off one-click trading")
def turn_off_one_click(trade_page: TradePage, account_settings: TradingApi):
    # It was on: the One-Click tab shows it, so the "off" checks below can't pass before anything happens.
    expect(trade_page.order_panel.one_click_tab).to_be_visible()
    trade_page.app_settings.turn_off_one_click()


@then("one-click trading should be on")
def one_click_is_on(trade_page: TradePage):
    # The tab first: the settings menu may still be closing after the switch was clicked.
    expect(trade_page.order_panel.one_click_tab).to_be_visible()
    expect(trade_page.app_settings.open().one_click_on).to_be_visible()
    trade_page.app_settings.close()  # it covers the order panel


@then("one-click trading should be off")
def one_click_is_off(trade_page: TradePage):
    expect(trade_page.order_panel.one_click_tab).to_be_hidden()
    expect(trade_page.app_settings.open().one_click_off).to_be_visible()
    trade_page.app_settings.close()
