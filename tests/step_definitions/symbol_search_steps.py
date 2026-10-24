"""Steps for the symbol search bar, used to open a symbol, and for the symbol's market being open or closed."""
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Page, Route, expect
from pytest_bdd import given, parsers

from src.api.trading_api import MARKET_CLOSED, MARKET_OPEN, SYMBOL_DETAIL
from src.pages.components.order_panel import MARKET_CLOSED_MSG
from src.pages.trade_page import TradePage


@given(parsers.parse('"{symbol}" is open for trading'))
def symbol_is_open(trade_page: TradePage, symbol: str):
    # These scenarios run only during the symbol's published hours (src/datas/market_hours.py).
    _open_symbol(trade_page, symbol)
    expect(trade_page.order_panel.market_closed,
           f'{symbol} shows "{MARKET_CLOSED_MSG}" during its trading hours').to_have_count(0)


@given(parsers.parse('I open "{symbol}"'))
def open_symbol(trade_page: TradePage, symbol: str):
    """Open the symbol whether its market is open or not."""
    _open_symbol(trade_page, symbol)


@given(parsers.parse('the "{symbol}" market is mocked as closed'))
def market_mocked_closed(trade_page: TradePage, symbol: str):
    # Mocked in the browser, so the scenario runs at any time. Set before the symbol opens.
    _mock_market_status(trade_page.page, symbol, MARKET_CLOSED)


@given(parsers.parse('the "{symbol}" market is closed, but mocked as open on my page'))
def market_mocked_open(trade_page: TradePage, symbol: str):
    # The order has to reach the server while the market is really closed: the scenario is
    # tagged @closed_market, so it runs only outside the published hours.
    _mock_market_status(trade_page.page, symbol, MARKET_OPEN)


def _open_symbol(trade_page: TradePage, symbol: str):
    trade_page.symbol_search.search(symbol).select(symbol)
    expect(trade_page.open_symbol).to_have_text(symbol)
    expect(trade_page.order_panel.panel_loading).to_have_count(0)


def _mock_market_status(page: Page, symbol: str, status: str):
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
