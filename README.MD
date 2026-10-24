# AQX Trader UI tests

Automated UI tests for the [AQX Trader](https://aqxtrader.aquariux.com) web app, written with
Playwright, pytest and pytest-bdd (Gherkin). They run against the live site on a demo account.

You can run them three ways:

- [on your machine](#run-on-your-machine)
- [in Docker](#run-in-docker)
- [on GitHub Actions](#run-on-github-actions), which runs the smoke tests on every push

## Before you start: the decryption key

The test user's password in `src/test_data/user.json` is encrypted. To decrypt it, the tests need
the key `AQX_ENCRYPTION_KEY`. The key isn't in the repository, so get it from the repository owner.

Copy `.env.example` to `.env` and put the key in it:

```
AQX_ENCRYPTION_KEY=<the key>
```

`.env` is ignored by git and left out of the Docker image. Never commit it.

## Run on your machine

You need Python 3.12 or newer. The Allure report also needs Node.js.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

Then:

| Command | What it runs |
|---|---|
| `pytest` | everything |
| `pytest -n 4 --dist loadgroup` | everything, 4 tests at a time (scenarios that trade still run one at a time) |
| `pytest -m smoke` | one scenario per feature: its main flow |
| `pytest -m login` | one feature. The other features are `market_order`, `one_click`, `pending_order`, `open_positions`, `bulk_actions`, `trading_history`, `trade_records` and `market_closed` |
| `pytest -m defect` | the scenarios that track site defects (see [Results](#reading-the-results)) |
| `pytest -k "invalid_password"` | scenarios whose name contains the text |

Add `--headed` to watch the browser.

`pytest --collect-only -q` lists the tests without running them. It fails if a Gherkin step has no
code behind it.

### HTML report

Every run saves Allure results in `allure-results/`, replacing the last run's. To build the report:

```bash
npx allure@3.20.1 generate allure-results
```

This writes `allure-report/index.html`, a single file you can open in a browser. Tests are grouped
by feature, then scenario, then step, and the step that failed has a screenshot.

## Run in Docker

The image holds Python, the packages and Chromium. The key is passed in when the container runs,
never built into the image.

```bash
docker build -t aqx-tests .
docker run --rm --env-file .env aqx-tests -m smoke
```

Anything after `aqx-tests` goes to pytest, so the commands in the table above work too, for
example `docker run --rm --env-file .env aqx-tests -m login`. The exception is `--headed`: the
container has no screen.

To keep the Allure results, mount the folder:

```bash
# macOS / Linux
docker run --rm --env-file .env -v "$PWD/allure-results:/app/allure-results" aqx-tests -m smoke
```

```powershell
# Windows PowerShell
docker run --rm --env-file .env -v "${PWD}/allure-results:/app/allure-results" aqx-tests -m smoke
```

Rebuild the image after changing the code: the code is copied in when the image is built.

## Run on GitHub Actions

`.github/workflows/smoke.yml` runs the smoke tests (`pytest -m smoke`) in the Docker image. It
runs:

- on every push to `master` or `development`
- on every pull request to `master`
- by hand: on GitHub, Actions > Smoke tests > Run workflow, or `gh workflow run smoke.yml --ref development`

### One-time setup

Add the key as a repository secret named `AQX_ENCRYPTION_KEY`. Either:

- on GitHub, Settings > Secrets and variables > Actions > New repository secret, or
- `gh secret set AQX_ENCRYPTION_KEY`, then paste the key when asked

Without it, every test that logs in fails with `AQX_ENCRYPTION_KEY is missing`.

### Results

The run's log lists each test, with the reason for any skip. Two downloads are saved with the run,
under Artifacts on its page:

- `allure-report`: the HTML report. Unzip it and open `index.html` in a browser.
- `allure-results`: the raw results, if you want to rebuild the report.

Or from the command line: `gh run download <run-id> -n allure-report`

### Differences from a local run

- Checks wait up to 15 seconds instead of Playwright's usual 5. GitHub's runners are in the US, and
  the site is much slower from there: after login, the trade page took up to 5 seconds to show
  its first symbol. GitHub sets the `CI` variable, which turns this on (`tests/conftest.py`).
- Runs wait for each other rather than overlapping, because they all trade on the same demo account.

## Reading the results

- **Skipped while the market is closed.** Scenarios that place orders need the symbol's market
  open, so they check the server's live market status first and skip while it's closed. A run at
  the weekend skips most trading scenarios. The skip reason says so, for example
  `UKOIL market is closed: no order can be placed`. UKOIL's trading hours are in `docs/api-notes.md`.
  The `market_closed` scenarios are the exception: they test the closed market and run at any time.
- **Expected failures (`@defect`).** Some scenarios check what the site should do but doesn't yet.
  They're marked as expected to fail ("xfailed") until the site is fixed. If one starts passing,
  the run fails, so the tag can be removed. In the Allure report they show as Skipped.
  `docs/defects.md` has the steps to reproduce each defect by hand.
- **One run at a time on the demo account.** Trading scenarios open and close orders on the shared
  demo account, and a run starts by closing every position on it. Don't run the trading scenarios
  on your machine while the GitHub workflow is running.

## Project layout

| Path | What's there |
|---|---|
| `features/` | Gherkin scenarios, one file per feature |
| `tests/step_definitions/` | the code behind the Gherkin steps |
| `src/pages/` | page objects: the locators and actions for each page and widget |
| `src/api/trading_api.py` | the site's trading API, used to set up and clean up orders |
| `src/test_data/user.json` | the test user, with the password encrypted |
| `docs/` | notes on the site, its API, the conventions, and the defects found |

To encrypt a new password for `user.json`:

```bash
python -m src.utils.crypto encrypt "<password>"
```

## More detail

- `docs/defects.md`: each defect, with steps to reproduce it by hand, expected vs actual, and why it's a defect
- `docs/findings.md`: all bugs found, open questions, coverage gaps and the suite's limits
- `docs/manual-test-steps.md`: how to do each trading flow by hand, and what to expect
- `docs/conventions.md`: how the page objects, steps and Gherkin are written
- `docs/site-notes.md`: what's known about the site (test ids, timing quirks, test symbols)
- `docs/api-notes.md`: the site's internal trading API
