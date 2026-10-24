"""Steps for Bulk Close (Open Positions) and Bulk Delete (Pending Orders).

Bulk actions act on every order on the account, not just a test's own. Trading scenarios run one
at a time (`@trading`), and each bulk scenario first checks the account holds nothing else.
"""
import time
from urllib.parse import urlparse

import pytest
from playwright.sync_api import Request, expect
from pytest_bdd import given, parsers, then, when

from src.api.trading_api import BULK_CLOSE, BULK_DELETE, TradingApi
from src.models.Order import Order
from src.pages.trade_page import TradePage
from tests.step_definitions.live_prices import number
from tests.step_definitions.orders import let_tables_update, send_and_finish

# Kinds of pending order each Bulk Delete option covers.
DELETE_KINDS = {"All Orders": ("Limit", "Stop", "Stop Limit"), "Limit Orders": ("Limit",),
                "Stop Orders": ("Stop",), "Stop Limit Orders": ("Stop Limit",)}
# A bulk close of 30 positions takes about 6 s on the server.
BULK_DONE_TIMEOUT_S = 30
# The tables show this many rows per page; bulk actions act on at most this many.
ROWS_PER_PAGE = 30
# After clicking a greyed-out menu item, how long to watch for a dialog.
DIALOG_WAIT_MS = 1000


@given("the account has no other open positions or pending orders")
def account_is_empty(trading_api: TradingApi):
    others = [p["orderId"] for p in trading_api.open_positions()] + [o["orderId"] for o in trading_api.pending_orders()]
    if others:
        pytest.skip(f"Other orders are on the account ({others}); a bulk action would close or delete them")


@when(parsers.parse('I bulk close "{option}"'))
def bulk_close(trade_page: TradePage, open_orders: list[Order], option: str):
    table = trade_page.open_positions.open()
    _wait_until_listed(table, _shown(trade_page, _positions(open_orders)))  # so the action sees them all
    table.bulk_close(option)
    expect(trade_page.bulk_action_dialog.question).to_be_visible()


@when(parsers.parse('I bulk delete "{option}"'))
def bulk_delete(trade_page: TradePage, open_orders: list[Order], option: str):
    table = trade_page.pending_orders.open()
    _wait_until_listed(table, _shown(trade_page, _pending(open_orders)))
    table.bulk_delete(option)
    expect(trade_page.bulk_action_dialog.question).to_be_visible()


@then(parsers.parse('the bulk dialog should say "{text}"'))
def bulk_dialog_says(trade_page: TradePage, text: str):
    expect(trade_page.bulk_action_dialog.root).to_contain_text(text)


@when("I confirm the bulk action")
def confirm_bulk(trade_page: TradePage):
    send_and_finish(trade_page.page, _is_bulk, trade_page.bulk_action_dialog.confirm)


@when("I confirm the bulk action, noting which positions are at a loss", target_fixture="losing")
def confirm_bulk_noting_losses(trade_page: TradePage, open_orders: list[Order]) -> set[str]:
    # The site works out profit and loss in the browser when Confirm is clicked, so read them just before.
    profits = trade_page.open_positions.profits()
    send_and_finish(trade_page.page, _is_bulk, trade_page.bulk_action_dialog.confirm)
    return {o.order_id for o in _positions(open_orders) if number(profits[o.order_id]) < 0}


@when("I cancel the bulk action")
def cancel_bulk(trade_page: TradePage):
    trade_page.bulk_action_dialog.cancel()
    expect(trade_page.bulk_action_dialog.question).to_be_hidden()


@then("all my positions should be closed")
def all_positions_closed(trade_page: TradePage, open_orders: list[Order]):
    for order in _positions(open_orders):
        expect(trade_page.open_positions.row(order.order_id)).to_have_count(0)


@then("my positions should all still be open")
def positions_still_open(trade_page: TradePage, open_orders: list[Order]):
    let_tables_update(trade_page.page)
    for order in _positions(open_orders):
        expect(trade_page.open_positions.row(order.order_id)).to_be_visible()


@then("my positions that were at a loss should be closed, and any others still open")
def losing_closed(trade_page: TradePage, open_orders: list[Order], losing: set[str]):
    assert losing, "None of my positions was at a loss when Confirm was clicked"
    for order in _positions(open_orders):
        row = trade_page.open_positions.row(order.order_id)
        if order.order_id in losing:
            expect(row).to_have_count(0)
        else:
            expect(row).to_be_visible()


@then(parsers.parse('only my "{option}" should be deleted'))
def only_kind_deleted(trade_page: TradePage, open_orders: list[Order], option: str):
    for order in _pending(open_orders):
        row = trade_page.pending_orders.row(order.order_id)
        if order.order_type in DELETE_KINDS[option]:
            expect(row).to_have_count(0)
        else:
            expect(row).to_be_visible()


@then("my pending orders should all still be pending")
def pending_still_there(trade_page: TradePage, open_orders: list[Order]):
    let_tables_update(trade_page.page)
    for order in _pending(open_orders):
        expect(trade_page.pending_orders.row(order.order_id)).to_be_visible()


@then(parsers.parse('only my "{symbol}" positions should be closed'))
def only_symbol_closed(trade_page: TradePage, trading_api: TradingApi, open_orders: list[Order], symbol: str):
    for order in _positions(open_orders):
        if order.symbol == symbol:
            expect(trade_page.open_positions.row(order.order_id)).to_have_count(0)
    # Hide Other Symbols hides the other symbols' rows, so the server's list says if they're still open.
    still_open = {p["orderId"] for p in trading_api.open_positions()}
    closed_too = [o.order_id for o in _positions(open_orders) if o.symbol != symbol and o.order_id not in still_open]
    assert not closed_too, f"Positions on other symbols were closed too: {closed_too}"


@then(parsers.parse('only my "{symbol}" pending orders should be deleted'))
def only_symbol_deleted(trade_page: TradePage, trading_api: TradingApi, open_orders: list[Order], symbol: str):
    for order in _pending(open_orders):
        if order.symbol == symbol:
            expect(trade_page.pending_orders.row(order.order_id)).to_have_count(0)
    still_pending = {o["orderId"] for o in trading_api.pending_orders()}
    deleted_too = [o.order_id for o in _pending(open_orders) if o.symbol != symbol and o.order_id not in still_pending]
    assert not deleted_too, f"Orders on other symbols were deleted too: {deleted_too}"


@then(parsers.parse('the "{option}" option should be selectable'))
def option_selectable(trade_page: TradePage, option: str):
    expect(_delete_menu_item(trade_page, option)).to_have_css("cursor", "pointer")


@then(parsers.parse('the "{option}" option should not be selectable'))
def option_not_selectable(trade_page: TradePage, option: str):
    item = _delete_menu_item(trade_page, option)
    expect(item).to_have_css("cursor", "not-allowed")
    item.click()
    trade_page.page.wait_for_timeout(DIALOG_WAIT_MS)
    expect(trade_page.bulk_action_dialog.question).to_be_hidden()


@then(parsers.parse('{closed:d} of my positions should be closed and {left:d} still open'))
def positions_closed_count(trading_api: TradingApi, open_orders: list[Order], closed: int, left: int):
    mine = {o.order_id for o in _positions(open_orders)}
    assert len(mine) == closed + left, f"The scenario opened {len(mine)} positions, not {closed + left}"
    still = _wait_for_count(lambda: [p["orderId"] for p in trading_api.open_positions() if p["orderId"] in mine], left)
    assert len(still) == left, f"{len(mine) - len(still)} of my positions were closed, expected {closed}"


@then(parsers.parse('{deleted:d} of my pending orders should be deleted and {left:d} still pending'))
def pending_deleted_count(trading_api: TradingApi, open_orders: list[Order], deleted: int, left: int):
    mine = {o.order_id for o in _pending(open_orders)}
    assert len(mine) == deleted + left, f"The scenario placed {len(mine)} orders, not {deleted + left}"
    still = _wait_for_count(lambda: [o["orderId"] for o in trading_api.pending_orders() if o["orderId"] in mine], left)
    assert len(still) == left, f"{len(mine) - len(still)} of my orders were deleted, expected {deleted}"


def _delete_menu_item(trade_page: TradePage, option: str):
    table = trade_page.pending_orders
    if not table.bulk_delete_option(option).is_visible():
        table.open_bulk_delete_menu()
    return table.bulk_delete_option(option)


def _positions(orders: list[Order]) -> list[Order]:
    return [o for o in orders if o.order_type == "Market"]


def _pending(orders: list[Order]) -> list[Order]:
    return [o for o in orders if o.order_type != "Market"]


def _shown(trade_page: TradePage, orders: list[Order]) -> list[Order]:
    """The orders the table lists: all of them, or only the open symbol's with Hide Other Symbols on."""
    if trade_page.hide_other_symbols_on.is_visible():
        symbol = trade_page.open_symbol.inner_text().strip()
        orders = [o for o in orders if o.symbol == symbol]
    return orders


def _wait_until_listed(table, orders: list[Order]):
    """Wait for the table to list these orders. It shows 30 rows per page, and with more than that
    which ones make the first page isn't predictable, so then the tab's count is used instead."""
    if len(orders) > ROWS_PER_PAGE:
        expect(table.tab).to_contain_text(f"({len(orders)})")
        return
    for order in orders:
        expect(table.row(order.order_id)).to_be_visible()


def _wait_for_count(read, count: int) -> list:
    """Re-read until the list has `count` items or the bulk action had time to finish."""
    deadline = time.monotonic() + BULK_DONE_TIMEOUT_S
    items = read()
    while len(items) != count and time.monotonic() < deadline:
        time.sleep(1)
        items = read()
    return items


def _is_bulk(request: Request) -> bool:
    return request.method == "PUT" and urlparse(request.url).path in (BULK_CLOSE, BULK_DELETE)
