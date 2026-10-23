import pytest
from playwright.sync_api import Page, Playwright

from src.api.trading_api import TradingApi
from src.datas.user_data import get_user
from src.models.Order import Order
from src.pages.login_page import LoginPage
from src.pages.trade_page import TradePage

# Step files shared across features (one per page or page component).
pytest_plugins = [
    "tests.step_definitions.login_steps",
    "tests.step_definitions.trade_steps",
    "tests.step_definitions.symbol_search_steps",
    "tests.step_definitions.open_positions_steps",
    "tests.step_definitions.order_panel_steps",
    "tests.step_definitions.order_confirmation_steps",
]

# Feature tag for scenarios that place orders on the shared demo account.
TRADING_TAG = "trading"
# With `pytest -n <workers> --dist loadgroup`, every test in this group runs on the same worker,
# one at a time, so two trading scenarios never change the account at once.
TRADING_GROUP = "demo_account"
# Scenario tag for a check the site fails today. The comment above the scenario says what's wrong.
KNOWN_BUG_TAG = "known_bug"


def pytest_bdd_apply_tag(tag: str, function):
    """`@trading`: one-at-a-time xdist group. `@known_bug`: expected to fail until the site is fixed."""
    if tag == TRADING_TAG:
        pytest.mark.trading(function)
        pytest.mark.xdist_group(TRADING_GROUP)(function)
        return True
    if tag == KNOWN_BUG_TAG:
        pytest.mark.known_bug(function)
        # strict: once the site is fixed the scenario passes, which fails the run, so the tag gets
        # removed. raises: only a failed check counts, not a test that broke for another reason.
        pytest.mark.xfail(strict=True, raises=AssertionError,
                          reason="Known site bug, see the comment above the scenario")(function)
        return True
    return None  # pytest-bdd's default: the tag becomes a marker of the same name


@pytest.fixture
def login_page(page: Page) -> LoginPage:
    return LoginPage(page)


@pytest.fixture
def trade_page(page: Page) -> TradePage:
    return TradePage(page)


@pytest.fixture(scope="session")
def trading_api(playwright: Playwright, base_url: str):
    """API session on the demo account, for setup and cleanup.

    Starts by closing every open position on the account: leftovers from a crashed run would
    confuse the trading scenarios. Don't trade on the account by hand while tests run.
    """
    user = get_user("normal")
    api = TradingApi.log_in(playwright, base_url, user.username, user.password)
    api.close_positions(api.open_positions())
    yield api
    api.dispose()


@pytest.fixture
def open_orders(trading_api: TradingApi):
    """Orders this test opened. Whatever is still open at the end is closed, pass or fail."""
    orders: list[Order] = []
    yield orders
    mine = {order.order_id for order in orders}
    trading_api.close_positions([p for p in trading_api.open_positions() if p["orderId"] in mine])
