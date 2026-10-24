"""Steps that make one of the site's requests fail (mocked in the browser, see request_failures.py)."""
from pytest_bdd import given, parsers

from src.pages.trade_page import TradePage
from tests.step_definitions.request_failures import answer_with, fail_requests, failure


@given(parsers.parse('the "{request}" request is mocked to answer {status:d} with "{message}"'))
def request_mocked_to_answer(trade_page: TradePage, request: str, status: int, message: str):
    fail_requests(trade_page.page, request, answer_with(status, message))


@given(parsers.parse('the "{request}" request is mocked to fail with a "{kind}"'))
def request_mocked_to_fail(trade_page: TradePage, request: str, kind: str):
    fail_requests(trade_page.page, request, failure(kind))
