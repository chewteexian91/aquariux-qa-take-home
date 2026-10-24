"""Mock the site's requests failing in the browser, for the failed-request scenarios.

Not a step file: it holds no steps, so it isn't registered in `pytest_plugins`. Nothing mocked
here reaches the server.
"""
from urllib.parse import urlparse

from playwright.sync_api import Page, Route

from src.api.trading_api import (BULK_CLOSE, BULK_DELETE, CLOSE_OR_DELETE, MARKET_ORDER, NOTIFICATIONS,
                                 ORDERS_AND_DEALS, PENDING_ORDER, POSITIONS_HISTORY, PREFERENCE)

# The requests a scenario can make fail, by the name the feature files use.
REQUESTS = {
    "place market order": ("POST", MARKET_ORDER),
    "place pending order": ("POST", PENDING_ORDER),
    "modify pending order": ("PATCH", PENDING_ORDER),
    "delete pending order": ("DELETE", CLOSE_OR_DELETE),
    "modify position": ("PATCH", MARKET_ORDER),
    "close position": ("PUT", CLOSE_OR_DELETE),
    "bulk close": ("PUT", BULK_CLOSE),
    "bulk delete": ("PUT", BULK_DELETE),
    "one-click setting": ("PATCH", PREFERENCE),
    "positions history": ("GET", POSITIONS_HISTORY),
    "orders and deals": ("GET", ORDERS_AND_DEALS),
    "notifications": ("GET", NOTIFICATIONS),
}

# The message a mocked "400 answer" carries, in the API's error format.
REJECTED_MESSAGE = "Rejected for this test."

# Ways for a request to fail: an error answer in the API's format, or no answer from the API.
FAILURES = {
    "400 answer": lambda route: answer_with(400, REJECTED_MESSAGE)(route),
    "500 answer": lambda route: answer_with(500, "Internal Server Error")(route),
    "network error": lambda route: route.abort("failed"),
    "blocked request": lambda route: route.abort("blockedbyclient"),
    "timeout": lambda route: route.abort("timedout"),
    # What a gateway in front of the API sends when the API is down: a page, not the API's JSON.
    "502 gateway page": lambda route: route.fulfill(
        status=502, content_type="text/html", body="<html><body><h1>502 Bad Gateway</h1></body></html>"),
    "503 gateway page": lambda route: route.fulfill(
        status=503, content_type="text/plain", body="Service Unavailable"),
}


def answer_with(status: int, message: str):
    """An error answer in the API's own format: {"code": "<status>", "message": "<message>"}."""
    return lambda route: route.fulfill(status=status, json={"code": str(status), "message": message})


def failure(name: str):
    if name not in FAILURES:
        raise ValueError(f"Unknown failure '{name}'. Use one of: {', '.join(FAILURES)}")
    return FAILURES[name]


def fail_requests(page: Page, request: str, handle):
    """From now on, answer every `request` this page sends with `handle` instead of sending it.

    Left in place until the scenario ends: each scenario gets a new page.
    """
    if request not in REQUESTS:
        raise ValueError(f"Unknown request '{request}'. Use one of: {', '.join(REQUESTS)}")
    method, path = REQUESTS[request]

    def route(route: Route):
        if route.request.method == method:
            handle(route)
        else:
            route.fallback()

    page.route(lambda url: urlparse(url).path == path, route)
