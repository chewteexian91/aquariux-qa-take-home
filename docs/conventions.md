# Conventions

## Page objects (`src/pages/`)
- Subclass `BasePage` and set `URL` (a path relative to `base_url` in `pytest.ini`).
- Locate by test id: `page.get_by_test_id(...)`. Use text only when there is no test id, and keep that
  text in a module constant (e.g. `INVALID_CREDENTIALS_MSG` in `login_page.py`).
- Locators are attributes set in `__init__`. A locator that needs a value is a method
  (e.g. `SymbolSearch.result(symbol)`).
- Actions return `self` so they chain: `login_page.open().login(username, password)`.
- No assertions in page objects. `expect` belongs in steps.
- A widget with its own job (search bar, order panel) is a component in `src/pages/components/`.
  The page holds it as an attribute: `trade_page.symbol_search`, `trade_page.order_panel`.

## Steps (`tests/step_definitions/`)
- Get pages from the fixtures in `tests/conftest.py` (`login_page`, `trade_page`). Get components through the page.
- Use `parsers.parse` with quoted values: `'I log in as the "{role}" user'`. Use `parsers.re` only when a value can be empty.
- Assert with Playwright `expect` (it retries). Don't use plain `assert` on what a locator shows.
- Live prices change all the time: check their format with a regex, never exact values.
- A shared setup step (e.g. `Given I am logged in as the "normal" user`) lives in the step file of the page it starts from.
  A `Given` that creates orders through the API lives in the step file of the table it fills.
- Helpers shared by step files go in plain modules that hold no steps (not in `pytest_plugins`):
  `live_prices.py`, `orders.py` (placing, API setup, waiting for a request), `trading_data.py`
  (prices for API-created orders), `request_failures.py`. Step files don't import from each other.
- A `When` that confirms something waits until the request has finished (`orders.send_and_finish`),
  answered or failed, so the `Then` steps see what the site did with the answer.
- A check that nothing changed says "still" ("my order should still be pending") and waits for the
  tables to update first (`orders.let_tables_update`): right after an action they show the old state.
- Failed requests: `Given the "<request>" request is mocked to fail with a "<failure>"` (names and
  kinds in `request_failures.py`: "400 answer", "500 answer", "network error"…). Mocked in the
  browser. When the failure is on the confirm itself:
  `When I confirm the order, with its request mocked to fail with a "<failure>"`.

## Gherkin (`features/`)
- Feature header: "As a … I want … So that …".
- Steps describe behaviour, not clicks on test ids.
- Same flow with different data: use a `Scenario Outline` with an `Examples` table.
- Each row of an outline needs its own title, so a report reader can tell which row failed. The
  report fills the title's `<placeholders>` from the row, so use enough of them that no two rows
  get the same title: `Place a <side> <type> order`. If no column reads well in a title, add one
  just for the title (the `empty` column in `login.feature`).
- Tag the feature with its marker and register the marker in `pytest.ini`.
- A check the site fails today gets `@defect` (a strict xfail) and a comment above the scenario
  saying what's wrong ("Defect #n: …"). Add the defect to `docs/defects.md` with steps to reproduce
  it by hand. The scenario describes the right behaviour. When it starts passing, the run fails,
  so the tag gets removed.
- A scenario that only checks the market-closed UI mocks the closed market
  (`Given the "<symbol>" market is mocked as closed`), so it runs at any time. A mocked state says
  "mocked" in the step text, so a reader never takes it for the real one.
- Market tags pick when a scenario runs (`src/datas/market_hours.py` works out which, from the
  published hours). No tag: it needs the market open. `@any_market`: it doesn't trade or it fakes
  the market's state. `@closed_market`: it needs the market really closed. Put them on the
  scenario, not the feature: a feature tag would also land on scenarios that need another state.
  Steps never skip because a market is closed: during the hours that's a failure
  (`Given "<symbol>" is open for trading` fails on it). A new symbol's hours go into `TRADING_HOURS`.
- Values worked out from the live price (Trade Details, SL/TP from points) can't use `expect` with
  a fixed value. Use `live_check` in `tests/step_definitions/live_prices.py`, which recomputes the
  expected value from the same snapshot each time it reads.

## Trading data (shared demo account)
All tests use one demo account, so anything that places orders follows these rules:
- **Tag the feature `@trading`.** Those scenarios run one at a time on a single xdist worker
  (`pytest -n 4 --dist loadgroup`), while login runs in parallel.
- **No scenario relies on another one having run.** Create the starting state in a `Given`, through
  the API (`trading_api`, see `docs/api-notes.md`): e.g. open a position with
  `trading_api.open_market_order`. Use the UI only for the behaviour the scenario checks.
- **Register every order you open or place in `open_orders`.** Teardown deletes the pending ones and
  closes the positions by Order No., pass or fail. The first trading test of a run closes every open
  position and deletes every pending order on the account (leftovers from a crash).
- **Create API orders before logging in** (`Given I have …` before `Given I am logged in …`), so the
  page loads with them.
- **Logging in reuses one saved browser login per worker** (`SavedLogins` in `tests/conftest.py`):
  every login starts a session and the account keeps only about 10.
- **Find rows by Order No.** (`trade_page.open_positions.row(order_id)`), never "first row" or by
  symbol. Never check total row counts: other tests' orders may be there.
- **Confirm a row was there before checking it's gone.** Right after a page load the tables say
  they're empty for a moment, so an absence check can pass without anything happening.
- **Account settings are shared.** One-click trading and "Hide Other Symbols" are saved on the
  server. A step that changes one takes the `account_settings` fixture, which switches both off in
  teardown.
- **Bulk actions hit everyone's orders.** A bulk scenario's Background starts with
  `Given the account has no other open positions or pending orders`, which skips the scenario if
  anything else is there.

## Prove it can fail
A check that never fails tests nothing. After adding checks, write a few scenarios with wrong expected
values in a scratch folder (not in the repo) and run them with the real step code:

    pytest -q -p no:cacheprovider -o addopts="" -o "bdd_features_base_dir=<scratch folder>"

`-o addopts=""` turns off the Allure results: Allure only takes feature files inside the project.

Every one should fail. If one passes, the check has a race or a wrong locator. Fix it before reporting done.
