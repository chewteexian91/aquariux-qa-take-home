"""Steps for the symbol search bar, used to open a symbol, and for the symbol's market being open or closed."""
from urllib.parse import parse_qs, urlparse

import pytest
from playwright.sync_api import Page, Route, expect
from pytest_bdd import given, parsers

from src.api.trading_api import MARKET_CLOSED, MARKET_OPEN, SYMBOL_DETAIL, TradingApi
from src.pages.components.order_panel import MARKET_CLOSED_MSG
from src.pages.trade_page import TradePage


@given(parsers.parse('"{symbol}" is open for trading'))
def symbol_is_open(trade_page: TradePage, symbol: str):
    _open_symbol(trade_page, symbol)
    # Outside the symbol's trading hours (e.g. at the weekend) no order can be placed.
    if trade_page.order_panel.market_closed.count():
        pytest.skip(f'{symbol} market is closed: the order panel shows "{MARKET_CLOSED_MSG}"')


@given(parsers.parse('I open "{symbol}"'))
def open_symbol(trade_page: TradePage, symbol: str):
    """Open the symbol whether its market is open or not."""
    _open_symbol(trade_page, symbol)


@given(parsers.parse('the "{symbol}" market is closed'))
def market_closed(trade_page: TradePage, symbol: str):
    # Faked in the browser, so the scenario runs at any time. Set before the symbol opens.
    _fake_market_status(trade_page.page, symbol, MARKET_CLOSED)


@given(parsers.parse('the "{symbol}" market has closed, but my page still shows it open'))
def market_closed_behind_page(trade_page: TradePage, trading_api: TradingApi, symbol: str):
    # The order has to reach the server while the market is really closed.
    if trading_api.market_is_open(symbol):
        pytest.skip(f"{symbol} market is open: this scenario needs it closed")
    _fake_market_status(trade_page.page, symbol, MARKET_OPEN)


def _open_symbol(trade_page: TradePage, symbol: str):
    trade_page.symbol_search.search(symbol).select(symbol)
    expect(trade_page.open_symbol).to_have_text(symbol)
    expect(trade_page.order_panel.panel_loading).to_have_count(0)


def _fake_market_status(page: Page, symbol: str, status: str):
    """Make the page see the symbol's market as open or closed. The server isn't told: orders still go to it.

    The order panel takes the market's state from the symbol's details, read once when the symbol
    opens (docs/site-notes.md). Left in place until the scenario ends: each scenario gets a new page.
    """

    def is_symbol_detail(url: str) -> bool:
        parts = urlparse(url)
        return parts.path == SYMBOL_DETAIL and parse_qs(parts.query).get("symbol") == [symbol]

    def answer(route: Route):
        response = route.fetch()
        body = response.json()
        # The server sends both: "TRADING" with online true, "CLOSED" with online false.
        body["result"]["status"] = status
        body["result"]["online"] = status == MARKET_OPEN
        route.fulfill(response=response, json=body)

    page.route(is_symbol_detail, answer)
