import re

from playwright.sync_api import Locator, Page

NO_RESULTS_MSG = "No search result"
ALL_KINDS = "All"

# Selecting a symbol reloads the order panel. While it loads, "One point equals" shows 0, and
# anything typed into the panel before the symbol's own value appears is dropped. This watches
# for that loading state followed by the loaded one. It's set up before the click, because the
# loading state lasts only about 0.15s.
_WATCH_PANEL_RELOAD_JS = r"""() => {
  window.__orderPanelReloaded = false;
  let sawLoading = false;
  const label = () => document.querySelector('[data-testid="trade-one-point-equal-label"]')?.innerText.trim() ?? '';
  const observer = new MutationObserver(() => {
    if (/:\s*0$/.test(label())) sawLoading = true;
    else if (sawLoading) { window.__orderPanelReloaded = true; observer.disconnect(); }
  });
  observer.observe(document.body, {subtree: true, childList: true, characterData: true});
}"""
PANEL_RELOAD_TIMEOUT_MS = 10_000
ONE_POINT_LABEL = "trade-one-point-equal-label"
OPEN_SYMBOL = "symbol-overview-id"
# On the One-Click tab, time for the panel to finish loading the new symbol (no loading state to watch).
ONE_CLICK_SETTLE_MS = 1000


class SymbolSearch:
    """Search bar at the top of the trade page, with its results dropdown.

    The dropdown has kind tabs (All / Forex / Commodities) that filter the results.
    """

    def __init__(self, page: Page):
        self.page = page
        self.input = page.get_by_test_id("symbol-input-search")
        self.dropdown = page.get_by_test_id("symbol-dropdown-result")
        self.results = self.dropdown.get_by_test_id("symbol-input-search-items-symbol")
        # The kind tabs and the empty state have no test ids, so they are matched by (English) text.
        self.no_results = self.dropdown.get_by_text(NO_RESULTS_MSG)

    def search(self, text: str):
        self.input.fill(text)
        return self

    def result(self, symbol: str) -> Locator:
        # Exact match, so "UKOIL" doesn't also match a longer symbol that contains it.
        return self.results.filter(has_text=re.compile(rf"^{re.escape(symbol)}$"))

    def kind_tab(self, kind: str) -> Locator:
        return self.dropdown.get_by_text(kind, exact=True)

    def filter_by_kind(self, kind: str):
        self.kind_tab(kind).click()
        return self

    def select(self, symbol: str):
        """Open the symbol from the results, and wait until the order panel has loaded it."""
        self.result(symbol).wait_for()
        # The One-Click tab (shown first while one-click trading is on) has no "One point equals"
        # label to watch. There, wait for the open symbol to change instead.
        trade_form_shown = self.page.get_by_test_id(ONE_POINT_LABEL).is_visible()
        self.page.evaluate(_WATCH_PANEL_RELOAD_JS)
        self.result(symbol).click()
        if trade_form_shown:
            self.page.wait_for_function("window.__orderPanelReloaded === true", timeout=PANEL_RELOAD_TIMEOUT_MS)
        else:
            self.page.get_by_test_id(OPEN_SYMBOL).filter(has_text=re.compile(rf"^{re.escape(symbol)}$")).wait_for(
                timeout=PANEL_RELOAD_TIMEOUT_MS)
            self.page.wait_for_timeout(ONE_CLICK_SETTLE_MS)
        return self
