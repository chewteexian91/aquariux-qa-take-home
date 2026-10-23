"""Steps for the trade page, shared by any feature that lands on it."""
import re

from playwright.sync_api import expect
from pytest_bdd import given, parsers, then

from src.api.trading_api import TradingApi
from src.pages.trade_page import TradePage


@given("one-click trading is off")
def one_click_trading_off(trading_api: TradingApi):
    # A server setting shared by every session. While it's on, Place trades at once, without the
    # Order Confirmation. Set before logging in, so the page loads with it. Off is the account's
    # normal state, so it isn't changed back afterwards.
    trading_api.set_one_click_trading(False)


@then("I should be on the trade page")
def on_trade_page(trade_page: TradePage):
    expect(trade_page.page).to_have_url(re.compile(re.escape(TradePage.URL)))


@then("I should see my account information")
def see_account_info(trade_page: TradePage):
    expect(trade_page.account_info).to_be_visible()
    expect(trade_page.account_type_tag).to_have_text("DEMO")


@then(parsers.parse('I should see the message "{message}"'))
def see_message(trade_page: TradePage, message: str):
    # Exact text, and any of the banners showing: an older one may still be on screen.
    banner = trade_page.toast.filter(has_text=re.compile(rf"^{re.escape(message)}$"))
    expect(banner.first).to_be_visible()
