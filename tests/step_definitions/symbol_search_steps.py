"""Steps for the symbol search bar, used to open a symbol for trading."""
from playwright.sync_api import expect
from pytest_bdd import given, parsers

from src.pages.trade_page import TradePage


@given(parsers.parse('"{symbol}" is open for trading'))
def symbol_is_open(trade_page: TradePage, symbol: str):
    trade_page.symbol_search.search(symbol).select(symbol)
    expect(trade_page.open_symbol).to_have_text(symbol)
