"""Steps that make one of the site's requests fail (faked in the browser, see request_failures.py)."""
from pytest_bdd import given, parsers

from src.pages.trade_page import TradePage
from tests.step_definitions.request_failures import answer_with, fail_requests, failure


@given(parsers.parse('the "{request}" request will be answered {status:d} with "{message}"'))
def request_answered_with(trade_page: TradePage, request: str, status: int, message: str):
    fail_requests(trade_page.page, request, answer_with(status, message))


@given(parsers.parse('the "{request}" request will fail with a "{kind}"'))
def request_fails_with(trade_page: TradePage, request: str, kind: str):
    fail_requests(trade_page.page, request, failure(kind))
