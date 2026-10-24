import os
import re
from urllib.parse import urlparse

import allure
import pytest
from playwright.sync_api import Browser, Page, Playwright, Request, expect
from playwright.sync_api import Error as PlaywrightError

from src.api.trading_api import MARKET_ORDER, PENDING_ORDER, TradingApi
from src.datas.user_data import get_user
from src.models.Order import Order
from src.pages.login_page import LoginPage
from src.pages.trade_page import TradePage

# Step files shared across features (one per page or page component).
pytest_plugins = [
    "tests.step_definitions.login_steps",
    "tests.step_definitions.trade_steps",
    "tests.step_definitions.app_settings_steps",
    "tests.step_definitions.symbol_search_steps",
    "tests.step_definitions.open_positions_steps",
    "tests.step_definitions.pending_orders_steps",
    "tests.step_definitions.order_panel_steps",
    "tests.step_definitions.order_confirmation_steps",
    "tests.step_definitions.edit_dialog_steps",
    "tests.step_definitions.close_position_dialog_steps",
    "tests.step_definitions.bulk_action_steps",
    "tests.step_definitions.order_history_steps",
    "tests.step_definitions.notifications_steps",
    "tests.step_definitions.request_failure_steps",
]

# Feature tag for scenarios that place orders on the shared demo account.
TRADING_TAG = "trading"
# With `pytest -n <workers> --dist loadgroup`, every test in this group runs on the same worker,
# one at a time, so two trading scenarios never change the account at once.
TRADING_GROUP = "demo_account"
# Scenario tag for a site defect: the scenario checks the right behaviour, so it fails until the
# site is fixed. The comment above the scenario says what's wrong; docs/defects.md has the details.
DEFECT_TAG = "defect"
# How long a check waits on GitHub (the CI variable is set) instead of expect's default 5 s. The
# runners are in the US, and each request to the site takes 10-20 times longer than from Asia:
# after login, the trade page took up to 5 s to show its first symbol there.
CI_EXPECT_TIMEOUT_MS = 15_000


def pytest_configure(config):
    if os.getenv("CI"):
        expect.set_options(timeout=CI_EXPECT_TIMEOUT_MS)


def pytest_bdd_apply_tag(tag: str, function):
    """`@trading`: one-at-a-time xdist group. `@defect`: expected to fail until the site is fixed."""
    if tag == TRADING_TAG:
        pytest.mark.trading(function)
        pytest.mark.xdist_group(TRADING_GROUP)(function)
        return True
    if tag == DEFECT_TAG:
        pytest.mark.defect(function)
        # strict: once the site is fixed the scenario passes, which fails the run, so the tag gets
        # removed. raises: only a failed check counts, not a test that broke for another reason.
        pytest.mark.xfail(strict=True, raises=AssertionError,
                          reason="Site defect, see docs/defects.md")(function)
        return True
    return None  # pytest-bdd's default: the tag becomes a marker of the same name


@pytest.hookimpl(tryfirst=True)  # before Allure closes the step, so the screenshot lands on it
def pytest_bdd_step_error(request: pytest.FixtureRequest):
    """In the Allure report, attach a screenshot of the page to the step that failed."""
    if "page" not in request.fixturenames:
        return
    try:
        screenshot = request.getfixturevalue("page").screenshot(full_page=True)
    except PlaywrightError:
        return  # the page is already gone; the step's error is still reported
    allure.attach(screenshot, name="Screenshot", attachment_type=allure.attachment_type.PNG)


@pytest.fixture
def login_page(page: Page) -> LoginPage:
    return LoginPage(page)


@pytest.fixture
def trade_page(page: Page) -> TradePage:
    return TradePage(page)


class SavedLogins:
    """The browser's login (its localStorage, which holds the token) per role, made once per run.

    Every UI login starts a new session, and the account keeps only about 10 (docs/site-notes.md),
    so scenarios reuse one login instead of logging in each time. The login feature still logs in.
    """

    def __init__(self, browser: Browser, base_url: str):
        self._browser = browser
        self._base_url = base_url
        self._storage: dict[str, dict] = {}

    def storage(self, role: str) -> dict:
        if role not in self._storage:
            self._storage[role] = self._log_in(role)
        return self._storage[role]

    def remember(self, role: str, page: Page):
        """Keep this page's login, e.g. after logging in again because the saved one expired."""
        self._storage[role] = _local_storage(page, self._base_url)

    def _log_in(self, role: str) -> dict:
        user = get_user(role)
        context = self._browser.new_context(base_url=self._base_url)
        try:
            page = context.new_page()
            LoginPage(page).open().login(user.username, user.password)
            trade_page = TradePage(page)
            expect(page).to_have_url(re.compile(re.escape(TradePage.URL)))
            expect(trade_page.open_symbol).not_to_be_empty()
            return _local_storage(page, self._base_url)
        finally:
            context.close()


def _local_storage(page: Page, base_url: str) -> dict:
    origin = urlparse(base_url)
    origin = f"{origin.scheme}://{origin.netloc}"
    for entry in page.context.storage_state()["origins"]:
        if entry["origin"] == origin:
            return {item["name"]: item["value"] for item in entry["localStorage"]}
    raise RuntimeError(f"No saved browser state for {origin}")


@pytest.fixture(scope="session")
def saved_logins(browser: Browser, base_url: str) -> SavedLogins:
    return SavedLogins(browser, base_url)


@pytest.fixture(scope="session")
def trading_api(playwright: Playwright, base_url: str):
    """API session on the demo account, for setup and cleanup.

    Starts by putting the account in its normal state: no open positions, no pending orders,
    one-click trading and Hide Other Symbols off. Leftovers from a crashed run would confuse the
    trading scenarios. Don't trade on the account by hand while tests run.
    """
    user = get_user("normal")
    api = TradingApi.log_in(playwright, base_url, user.username, user.password)
    api.close_positions(api.open_positions())
    api.delete_pending_orders(api.pending_orders())
    api.set_one_click_trading(False)
    api.set_hide_other_symbols(False)
    yield api
    api.dispose()


@pytest.fixture
def open_orders(trading_api: TradingApi):
    """Orders this test created. Whatever is still open or pending at the end goes, pass or fail.

    A pending order that filled became a position with the same Order No., so both are checked.
    """
    orders: list[Order] = []
    yield orders
    mine = {order.order_id for order in orders if order.order_id}
    trading_api.delete_pending_orders([o for o in trading_api.pending_orders() if o["orderId"] in mine])
    trading_api.close_positions([p for p in trading_api.open_positions() if p["orderId"] in mine])


@pytest.fixture
def account_settings(trading_api: TradingApi) -> TradingApi:
    """For scenarios that change one-click trading or Hide Other Symbols, which are saved on the
    server for the whole account. Both go back off at the end, pass or fail."""
    yield trading_api
    trading_api.set_one_click_trading(False)
    trading_api.set_hide_other_symbols(False)


@pytest.fixture
def order_requests(page: Page) -> list[Request]:
    """Every request this page sends to place a market or pending order, from the moment a step asks."""
    sent: list[Request] = []

    def record(request: Request):
        if request.method == "POST" and urlparse(request.url).path in (MARKET_ORDER, PENDING_ORDER):
            sent.append(request)

    page.on("request", record)
    return sent
