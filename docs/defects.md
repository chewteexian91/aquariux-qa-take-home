# Defects

Site defects the suite tracks with `@defect` scenarios. Each scenario checks what the site
**should** do, so it fails today and runs as a strict xfail. Once the defect is fixed the scenario
passes, which fails the run, so the tag gets removed. `pytest -m defect` runs them all; each
defect below has the command for its own scenarios (add `--headed` to watch).

Numbers match `docs/findings.md`, which also lists the bugs reported without a scenario.
Found on https://aqxtrader.aquariux.com with the demo account on 2026-10-23 and 2026-10-24. Prices
in the steps are from then (UKOIL at about 112); today, use prices the same distance from the market.

## Before you start
- Log in at `/web/login` with the demo account (`normal` in `src/test_data/user.json`).
- UKOIL's market must be open (Monday to Friday, hours in `docs/api-notes.md`). If the Place
  button reads "Market Closed", try again later.
- One-click trading off (gear icon, top right), unless the steps say otherwise.
- The account is shared. Note the Order No. of everything you create, and close or delete it
  afterwards.
- Type prices, then click somewhere else on the page. Don't press Tab: with the Points box focused
  the price follows the market (findings #2).
- **Making a request fail** (#12, #13): in Chrome DevTools open **More tools > Network request
  blocking**, tick **Enable network request blocking** and add the pattern from the steps. A
  blocked request fails as a network error. #6 needs an error *answer* instead (HTTP 502/503),
  which needs a debugging proxy such as Charles, Fiddler or mitmproxy. The automated scenarios fake
  these in the browser, so they never reach the server.

## Summary

| # | Severity | Defect | Scenarios |
|---|---|---|---|
| [1](#1-a-stop-loss-or-take-profit-of-0000-is-accepted-and-means-none) | High | A Stop Loss / Take Profit of `0.000` is accepted and means "none" | 4 |
| [4](#4-usdsgd-cant-be-traded-the-margin-is-far-too-high) | High | USDSGD can't be traded: the margin is far too high | 2 |
| [5](#5-usdsgd-trade-details-show-singapore-dollars-as-usd) | Medium | USDSGD Trade Details show Singapore dollars as USD | 1 |
| [6](#6-a-gateway-error-page-shows-the-raw-request-path) | Medium | A gateway error page shows the raw request path | 2 |
| [9](#9-a-pending-order-priced-on-the-wrong-side-of-the-market-isnt-caught-by-the-form) | Medium | A pending order priced on the wrong side of the market isn't caught by the form | 4 |
| [10](#10-a-stop-limit-price-on-the-wrong-side-of-the-price-isnt-caught-by-the-form) | Medium | A Stop Limit Price on the wrong side of the Price isn't caught by the form | 2 |
| [11](#11-an-expiry-time-that-has-already-passed-can-be-chosen) | Low | An expiry time that has already passed can be chosen | 1 |
| [12](#12-switching-one-click-trading-fails-without-a-message) | Medium | Switching one-click trading fails without a message | 2 |
| [13](#13-a-list-that-fails-to-load-says-its-empty) | Medium | A list that fails to load says it's empty | 3 |
| [15](#15-a-capped-bulk-close-says-all-positions-were-closed) | Low | A capped bulk close says all positions were closed | 1 |

---

## #1 A Stop Loss or Take Profit of 0.000 is accepted and means "none"
**Severity:** High.
**Scenarios:** `features/market_order.feature`, "A \<side\> order rejects a \<field\> price of
\<price\>, which becomes 0.000" (Buy Stop Loss and Sell Take Profit, each `0.000` and `0.00000001`).
**Run:** `pytest -m defect -k becomes_0000`

**Steps to reproduce**
1. Open UKOIL. Order Type **Market**, click **BUY**, Volume `0.1`.
2. In the Stop Loss **Price** box type `0.000`, then click somewhere else.
3. Look under the Stop Loss box, then click **Place Buy Order**.
4. In the Order Confirmation, click **Confirm**.
5. Find the new position in Open Positions by its Order No.

Also: type `0.00000001` (the box rounds it to `0.000`), or click **SELL** and do the same in Take
Profit.

**Expected:** an error under Stop Loss at step 3, and Place doesn't open the confirmation.
**Actual:** no error. The confirmation shows "Stop Loss 0.000", the order is sent with
`"stopLoss": 0`, and the position opens with Stop Loss `--` (none).

**Why it's a defect:** The trader typed a Stop Loss and the confirmation showed one, but the
position has no protection. 0 can't be a real stop level for a ~112 price. The site treats the same
value as an error elsewhere: a Sell's Stop Loss of `0.000` gets "Stop Loss must be greater than Buy
Price.", and Edit Position rejects 0 with "Value must be greater than 0" (findings #17). Losing a
risk control the trader believes is set is why this is High.

**Clean up:** close the position.

---

## #4 USDSGD can't be traded: the margin is far too high
**Severity:** High.
**Scenarios:** `features/market_order.feature`, "A USDSGD market order goes through", and the Est.
Margin Required example of "USDSGD Trade Details show the \<detail\> in USD".
**Run:** `pytest -m defect -k "usdsgd_market_order or Margin"`

**Steps to reproduce**
1. Search `USDSGD` and open it. Order Type **Market**, click **BUY**, Volume `0.01`.
2. Expand **Trade Details** and read Est. Margin Required.
3. Click **Place Buy Order**, read Est. Margin Required in the confirmation, then click **Confirm**.

**Expected:** Est. Margin Required 10.00. 0.01 lot is 1,000 USD (USD is the base currency), and
at the account's 1:100 leverage the margin is 1,000 / 100. The position opens: "Position has been
created."
**Actual:** 1,277,800.00 in the panel and the confirmation. Confirm gets HTTP 400 "Not enough
money", shown as the banner "Insufficient balance". Fill or Kill and Immediate or Cancel both fail.

**Why it's a defect:** a 1,000 USD trade needs 10 USD of margin, and the account has about
970,000 USD of equity. The site asks for more than the whole account, so USDSGD can't be traded at
all, and the trader is told they lack money when they don't. The server agrees with the wrong
figure, so the symbol's setup on the server looks wrong too, not just the screen.

---

## #5 USDSGD Trade Details show Singapore dollars as USD
**Severity:** Medium.
**Scenario:** `features/market_order.feature`, the Trade Volume example of "USDSGD Trade Details
show the \<detail\> in USD".
**Run:** `pytest -m defect -k "usdsgd_trade_details and Volume"`

**Steps to reproduce**
1. Open USDSGD. Order Type **Market**, click **BUY**, Volume `0.01`.
2. Expand **Trade Details (USD)** and read Trade Volume, Potential Loss and Potential Gain.

**Expected:** Trade Volume 1,000.00 (0.01 lot × 100,000 units of USD).
**Actual:** about 1,277.80, the value in Singapore dollars (1,000 USD at about 1.278 SGD per USD).
Potential Loss and Gain are in SGD too.

**Why it's a defect:** the heading says the figures are in USD, but they're in SGD, so a trader
sizing a trade reads a value about 28% too high. It is probably the same cause as #4, whose margin
is worked out from this wrong figure.

---

## #6 A gateway error page shows the raw request path
**Severity:** Medium.
**Scenarios:** `features/market_order.feature`, "An order request that fails with a \<failure\>
tells the user" (502 and 503 gateway pages).
**Run:** `pytest -m defect -k tells_the_user`

**Steps to reproduce** (needs a debugging proxy)
1. In the proxy, answer `POST https://aqxtrader.aquariux.com/api/trade/trade/v1/market` with HTTP
   503, Content-Type `text/plain` and the body `Service Unavailable`. For the 502 case, answer with
   HTTP 502 and an HTML page such as `<h1>502 Bad Gateway</h1>`.
2. Open UKOIL. Order Type **Market**, click **BUY**, Volume `0.1`.
3. Click **Place Buy Order**, then **Confirm**.

**Expected:** the app's general error, as for an HTTP 500 answer: "Something went wrong. Please
contact customer support."
**Actual:** the banner shows the request path and the HTTP status, e.g.
"/api/trade/trade/v1/market POST (503 - Service Unavailable)".

**Why it's a defect:** a gateway or load balancer sends pages like these while the API is down or
being deployed, which is when users most need a clear message. The banner shows an internal API
path and HTTP jargon, and doesn't tell the user what to do. The app already has the right message
for a 500 answer. The expected wording is an assumption until the product owner confirms it
(findings, open questions).

---

## #9 A pending order priced on the wrong side of the market isn't caught by the form
**Severity:** Medium.
**Scenarios:** `features/pending_order.feature`, "A \<side\> \<type\> order priced on the wrong
side of the market is stopped in the form" (Buy Limit +20%, Sell Limit −20%, Buy Stop −20%, Sell
Stop +20%).
**Run:** `pytest -m defect -k wrong_side_of_the_market`

**Steps to reproduce**
1. Open UKOIL. Order Type **Limit**, click **BUY**, Volume `0.1`.
2. Price: about 20% above the Buy price (e.g. `134.400` with UKOIL at 112). Click somewhere else.
3. Look under the Price box, then click **Place Buy Order**, then **Confirm**.

Also: Sell Limit 20% below the market, Buy Stop 20% below, Sell Stop 20% above.

**Expected:** an error under Price at step 3 (a Buy Limit must be below the market, a Buy Stop above
it), and Place doesn't open the confirmation.
**Actual:** no error. The confirmation opens, and Confirm gets HTTP 400 (`MT4_1009`) with the
banner "Metatrader Invalid Price".

**Why it's a defect:** the form lets the trader build and confirm an order the server always turns
down, though it already checks Stop Loss and Take Profit the same way. The rejection names the
trading back end ("Metatrader", an MT4 term on an MT5 account) instead of saying which price is
wrong and why. Edit Order has the same gap.

---

## #10 A Stop Limit Price on the wrong side of the Price isn't caught by the form
**Severity:** Medium.
**Scenarios:** `features/pending_order.feature`, "A \<side\> Stop Limit order with the Stop Limit
Price on the wrong side is stopped in the form" (Buy: Price +20%, Stop Limit Price +21%. Sell:
−20% and −21%).
**Run:** `pytest -m defect -k stop_limit_price_on_the_wrong_side`

**Steps to reproduce**
1. Open UKOIL. Order Type **Stop Limit**, click **BUY**, Volume `0.1`.
2. Price 20% above the Buy price (e.g. `134.400`), Stop Limit Price 21% above it (e.g.
   `135.520`). Click somewhere else.
3. Look under the Stop Limit Price box, then click **Place Buy Order**, then **Confirm**.

Also: **SELL** with Price 20% below the Sell price and Stop Limit Price 21% below.

**Expected:** an error under Stop Limit Price (for a Buy Stop Limit it must be below the Price, for
a Sell above), and Place doesn't open the confirmation.
**Actual:** no error. The confirmation opens, and Confirm gets HTTP 400 (`10015`) with the banner
"Invalid price".

**Why it's a defect:** as in #9, the form accepts an order the server always turns down. The
message doesn't say which of the order's two prices is wrong, so the trader has to guess.

---

## #11 An expiry time that has already passed can be chosen
**Severity:** Low.
**Scenario:** `features/pending_order.feature`, "An expiry time that has already passed today is
stopped in the form".
**Run:** `pytest -m defect -k already_passed_today`

**Steps to reproduce**
1. Note the server time at the top right (e.g. "Server Time : 2026-10-23 14:20:05").
2. Open UKOIL. Order Type **Limit**, click **BUY**, Volume `0.1`, Price 20% below the market (e.g.
   `90.000`).
3. Expiry: **Specified Date and Time**. Leave today's date. Open the time box, pick an hour before
   the server's current hour (e.g. `00`), and click **OK**.
4. Click **Place Buy Order**, then **Confirm**.

Not reproducible in the first hour after midnight, server time: no hour of today has passed yet.

**Expected:** past hours are greyed out in the time picker, as past days are in the calendar, or
the form shows an error and Place doesn't open the confirmation.
**Actual:** past hours can be picked and the form says nothing. The confirmation opens, and only
Confirm gets the banner "Invalid Expiration Date. Please try again."

**Why it's a defect:** the time picker doesn't match the calendar next to it (past days are
disabled), and the trader can build an order that can only be turned down. Low: the server catches
it and its message is clear.

---

## #12 Switching one-click trading fails without a message
**Severity:** Medium.
**Scenarios:** `features/one_click_trading.feature`, "Turning on one-click trading tells me when it
fails" and "Turning off one-click trading tells me when it fails" (the setting request answered
with HTTP 500).
**Run:** `pytest -m defect -k oneclick_trading_tells_me`

**Steps to reproduce** (turning it on)
1. Load the trade page. In DevTools, block `*/api/user/setting/v1/preference*` (see "Before you
   start").
2. Gear icon > switch **One Click Trading** on > **Agree and continue**.
3. Look for a message, then open the gear menu again.

Turning it off: switch it on first without blocking, then block the pattern and switch it off.

**Expected:** an error message saying the setting couldn't be saved, and the switch stays as it was.
**Actual:** the switch stays as it was, but no message shows.

**Why it's a defect:** the trader agreed to the terms and switched it on, and nothing says it
didn't work. Turning it off is worse: the trader believes orders will ask for confirmation again,
but one-click is still on, so the next Place sends an order at once. Every other failed action shows
an error banner. The scenarios use an HTTP 500 answer; a blocked request (network error) shows the
same silence. The right wording isn't known, so the scenarios accept any error message.

**Clean up:** turn blocking off and switch one-click trading off. The setting is saved on the
account.

---

## #13 A list that fails to load says it's empty
**Severity:** Medium.
**Scenarios:** `features/trading_history.feature`, "A failed Orders & Deals load is reported as an
error" (HTTP 500), "A failed Positions History load is reported as an error" (network error), "A
failed notifications load is reported as an error" (HTTP 500).
**Run:** `pytest -m defect -k is_reported_as_an_error`

**Steps to reproduce**
1. Load the trade page. In DevTools, block one of these:
   - Orders & Deals: `*/api/trade/order/v1/deal/histories*`
   - Positions History: `*/api/order/v3/histories*`
   - Notifications: `*/api/notification/v2*`
2. Click the **Orders & Deals** tab (or **Positions History**, or the bell icon).

**Expected:** an error saying the list couldn't be loaded, not the empty-list message.
**Actual:** "You have no orders & deals history.", "You have no order histories." or "No new
notifications.", with no error.

**Why it's a defect:** a trader with trades is told they have none. They may think their trades
are lost, or act on it, e.g. place again an order they think never went through. A failed load
must not look like a successful empty one. The right wording isn't known, so the scenarios accept
any error message.

---

## #15 A capped bulk close says all positions were closed
**Severity:** Low.
**Scenario:** `features/bulk_actions.feature`, "When some positions are left over, the message says
how many were closed".
**Run:** `pytest -m defect -k left_over`

**Steps to reproduce**
1. Make sure no one else is using the account: Bulk Close closes everyone's positions.
2. Open 31 UKOIL Buy positions of 0.1 lot. Quickest: switch one-click trading on and click **BUY**
   on the One-Click tab 31 times.
3. In Open Positions, click **Bulk Close** > **All Positions**. The dialog says "Up to 30 positions
   can be closed." Click **Confirm**.
4. Read the toast and the Open Positions count.

**Expected:** a message with the number closed, e.g. "30 positions have been closed." (the app has
a "{n} positions have been closed." text), so the trader knows one is still open.
**Actual:** "All positions have been closed." while Open Positions still shows 1.

**Why it's a defect:** the message is false: a position is still open and still moving with the
market. Low: the dialog warns about the cap and the table shows what's left. The expected wording is
an assumption until the product owner confirms it.

**Clean up:** close the remaining position and switch one-click trading off.
