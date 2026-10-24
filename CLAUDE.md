# AQX Trader UI tests

Playwright + pytest-bdd tests for the AQX Trader web app (https://aqxtrader.aquariux.com), run against a demo account.

## Scope: build only what was asked
- Write exactly the scenarios, steps and checks the user asks for. No extra edge cases, negative cases or "nice to have" scenarios.
- Page objects get the locators and actions the request needs, plus locators from any HTML the user pastes.
- Use the names the user gives (symbols, users, test data). If one doesn't exist on the site, ask before using a different one.
- Ideas for more coverage go in one line at the end of the reply. Don't build them.

## Commands
- Setup: `pip install -r requirements.txt`, then `playwright install chromium`
- `pytest` runs everything. `pytest -m <marker>` runs one feature: `login`, `market_order`, `one_click`,
  `pending_order`, `open_positions`, `bulk_actions`, `trading_history`, `trade_records`, `market_closed`.
  Add `--headed` to watch.
- `pytest -m smoke`: one scenario per feature (its main flow). GitHub runs it on push and PR
  (`.github/workflows/smoke.yml`, needs the repository secret `AQX_ENCRYPTION_KEY`) and saves the
  Allure HTML report with the run. With `CI` set (as on GitHub), checks wait 15 s instead of 5:
  the site is slow from GitHub's US runners.
- `@defect` scenarios are strict xfails: `pytest -m defect` runs the site defects they track.
- Market hours decide what runs, never the site's live status. Untagged scenarios need the market
  open, `@any_market` ones run any time, `@closed_market` ones need it closed.
  `pytest -m "$(python -m src.datas.market_hours)"` runs what fits now (the published hours in
  `src/datas/market_hours.py`); GitHub adds it to `-m smoke`. Steps don't skip on a closed market:
  they fail.
- Docker: `docker build -t aqx-tests .`, then `docker run --rm --env-file .env aqx-tests -m smoke`.
  Arguments after the image name go to pytest. Add `-v "$PWD/allure-results:/app/allure-results"`
  to keep the results.
- In parallel: `pytest -n 4 --dist loadgroup`. `@trading` scenarios still run one at a time on one worker.
- `pytest --collect-only -q` fails if a Gherkin step has no matching step code.
- HTML report: every run records Allure results in `allure-results/` (last run only). `npx allure@3.20.1 generate allure-results`
  writes `allure-report/index.html`, one file that opens in a browser: Feature > Scenario > steps, with a screenshot
  on the step that failed. `@defect` xfails show as Skipped. Settings: `allurerc.json`.
- Passwords in `src/test_data/user.json` are encrypted. The key is `AQX_ENCRYPTION_KEY` in `.env` (see `.env.example`).
  Encrypt a new one with `python -m src.utils.crypto encrypt "<password>"`.

## Layout
- `features/*.feature`: one file per feature, tagged with a marker registered in `pytest.ini`
- `src/pages/`: one page object per page. `src/pages/components/`: one class per widget on a page.
- `tests/step_definitions/*_steps.py`: one per page or component, registered in `pytest_plugins` in `tests/conftest.py`
- `tests/step_definitions/test_features.py` picks up new feature files automatically. Don't edit it.
- `src/datas/user_data.py`: `get_user(role)` returns a test user with the password decrypted
- `src/api/trading_api.py`: the site's trading API, used by fixtures to set up and clean up orders
- `tests/step_definitions/` also holds helper modules with no steps: `orders.py`, `trading_data.py`,
  `live_prices.py`, `request_failures.py`

## Workflow
1. Take locators from the `data-testid`s in HTML the user pastes. For parts not pasted, read the live DOM
   with a throwaway script in the scratchpad (see `docs/site-notes.md`).
2. Write the code following `docs/conventions.md`.
3. Check: `pytest --collect-only -q`, then the feature's marker, then the full suite.
4. Make sure each new check can fail (`docs/conventions.md`, "Prove it can fail").
5. Don't commit unless asked.

## More detail
- `docs/conventions.md`: page object, step and Gherkin conventions
- `docs/site-notes.md`: what's known about the site (test ids, timing quirks, test symbols)
- `docs/manual-test-steps.md`: how to do each trading flow by hand, and what to expect
- `docs/api-notes.md`: the site's internal trading API (captured from the web app), usable for test setup
- `docs/findings.md`: bugs found, open questions, coverage gaps and test suite limits
- `docs/defects.md`: each `@defect`: steps to reproduce it by hand, expected vs actual, and why it's a defect
