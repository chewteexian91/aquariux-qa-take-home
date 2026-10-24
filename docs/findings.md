# Findings

Found on the live demo site on 2026-10-23: #1-#8 while building `features/market_order.feature`,
#9-#22 while exploring and building the rest of the trading scope (one-click, pending orders, positions, bulk
actions, history, notifications). Details, test ids and formulas are in `docs/site-notes.md` and
`docs/api-notes.md`. Bugs with a scenario are tagged `@defect` (strict xfail): `pytest -m defect`
runs them, and `docs/defects.md` has steps to reproduce each one by hand.

## Bugs

| # | Severity | Bug | Tested by |
|---|---|---|---|
| 1 | High | A Stop Loss / Take Profit that is or rounds to `0.000` is accepted and opens the position with **no** SL/TP | `@defect` (4 scenarios) |
| 2 | Medium | A typed SL/TP price follows the market once its Points box gets focus (e.g. after Tab) | reported only |
| 3 | High | Sell with SL `0.000`, then Tab: Place sends the order with **no** Stop Loss despite the error | reported only |
| 4 | High | USDSGD can't be traded: margin shown as 1,277,800.00 USD for 0.01 lot, orders rejected | `@defect` (2 scenarios) |
| 5 | Medium | USDSGD Trade Details show SGD amounts under "Trade Details (USD)" | `@defect` (1 scenario) |
| 6 | Medium | A 502/503 page from a gateway shows the raw request path in the banner | `@defect` (2 scenarios) |
| 7 | Low | Extra decimals in a price are rounded silently (`120.0009` → `120.001`) | reported only |
| 8 | Low | A "200 OK" answer carrying an error code shows "Position has been created." | reported only |
| 9 | Medium | A pending order's price isn't checked against the market; the server's raw "Metatrader Invalid Price" is shown | `@defect` (4 scenarios) |
| 10 | Medium | A Stop Limit Price on the wrong side of the Price isn't checked; the server says only "Invalid price" | `@defect` (2 scenarios) |
| 11 | Low | An expiry time already past today can be picked and placed; only the server rejects it | `@defect` (1 scenario) |
| 12 | Medium | Switching one-click trading on or off fails silently when the request fails | `@defect` (2 scenarios) |
| 13 | Medium | A failed history / notifications load shows "You have no … history." / "No new notifications." | `@defect` (3 scenarios) |
| 14 | Low | Bulk failures always show "Order action failed", hiding the server's reason | reported only |
| 15 | Low | Bulk toasts say "All … have been closed / deleted" when the 30 cap left some behind | `@defect` (1 scenario) |
| 16 | Low | "Profitable / Loss Positions" with none to act on still opens the dialog and sends an empty request | reported only |
| 17 | Low | SL/TP `0` is "none" in the order panel but an error ("Value must be greater than 0") in Edit Position | reported only |
| 18 | Low | Volume above the maximum / off-step is changed silently in the order panel (100.1 → 100, 0.15 → 0.1) but rejected with a message in the close dialog | reported only |
| 19 | Low (API) | `PUT /api/trade/trade/v1` (close) answers 500 "Internal error" unless the session listed positions first | reported only |
| 20 | Medium | A "Position Closed" notification can show a close price that isn't the fill price (111.490 vs 111.488) | reported only (intermittent) |
| 21 | Low | Edit Order, opened just after the page loads, overwrites what is being typed (price, Stop Loss) | reported only (timing) |
| 22 | Low | The expiry date box starts at today, which the calendar won't let you pick, and placing with it is accepted | reported only |

1. **SL/TP of 0 means "none".** UKOIL, Buy with SL `0.000` or `0.00000001` (or Sell with TP the same).
   No error shows, the confirmation says "Stop Loss 0.000", the request sends `"stopLoss": 0`, and
   the position shows `--`. Expected: a validation error, as for 0 on the other side
   ("Stop Loss must be greater than Buy Price."). The user believes they're protected and isn't.
2. **Typed price drifts with focus in Points.** Type a TP price, press Tab (focus moves to its Points
   box), wait. The price moves with the market: typed `133.441`, sent `133.469` after a 28-point
   move. Pasting a price in one go does the same. Expected: a typed price stays as typed.
   It isn't tested because it only shows when the market moves.
3. **0.000 + Tab bypasses validation.** UKOIL Sell, SL `0.000`, Tab, Place. The error is on screen,
   but Place clears the box and opens the confirmation without a Stop Loss. Confirming sends no SL.
   Leaving the field with a click elsewhere blocks Place as it should. Related: with focus in
   Points, Place recalculates an invalid price (Buy SL `150` became `149.989`).
4. **USDSGD margin.** USDSGD, Buy 0.01 lot (1,000 USD). Est. Margin Required: 1,277,800.00 USD in the
   panel and the confirmation, more than the account's ~$1M equity. At 1:100 it should be 10.00.
   The server agrees with the wrong figure: both orders tried (Fill or Kill and Immediate or Cancel)
   got HTTP 400 `{"code": "10019", "message": "Not enough money"}`, banner "Insufficient balance".
   This looks like a server-side symbol setup problem.
5. **USDSGD currency.** Trade Volume shows 1,277.80 (SGD) for a 1,000 USD trade; Potential Loss and
   Gain are in SGD too.
6. **Gateway errors.** When the order request gets a 502/503 page instead of the API's JSON, the
   banner reads "/api/trade/trade/v1/market POST (503 - Service Unavailable)". A JSON 500 shows
   "Something went wrong. Please contact customer support.", which the scenario expects here too.
7. **Silent rounding.** The price box rounds to the symbol's point size on blur with no message.
   Only a problem when it changes what the user meant, as in #1.
8. **Success on an error body.** Faked HTTP 200 with `{"code": "TRADE_9999", ...}` shows
   "Position has been created." The real server reports errors with an HTTP status (only seen as
   400 so far), so this probably can't happen.

9. **Pending price vs market.** UKOIL at ~112, Buy Limit at 120 (or Sell Limit 100, Buy Stop 100,
   Sell Stop 120): no error in the form, the confirmation opens, Confirm gets HTTP 400 `MT4_1009`
   and the banner "Metatrader Invalid Price" (an MT4 term on an MT5 account). Expected: a message
   under the Price before Place, as for SL/TP. The same holds in Edit Order.
10. **Stop Limit Price.** Buy Stop Limit 120 with Stop Limit Price 121 (must be below): no error,
    server `10015`, banner "Invalid price", without saying which price.
11. **Past expiry time.** Specified Date and Time, today, hour 00: the time list doesn't disable
    past hours and the form doesn't object. The server rejects it and the banner says "Invalid
    Expiration Date. Please try again." (past *dates* are disabled in the calendar).
12. **One-click switch failures.** If `PATCH /api/user/setting/v1/preference` fails (500 or
    network), the switch stays where it was with no message. The user clicked "Agree and
    continue" and nothing tells them it didn't work. Turning it off never shows a toast either,
    though the app has "One-Click Trading deactivated." in its texts.
13. **Load failures look like empty data.** A 500 or network error on the history or notification
    lists shows the empty state ("You have no orders & deals history.", "No new notifications."),
    so a trader is told they have no trades.
14. **Bulk failure banner.** A single close/delete shows the server's message on a 4xx; a bulk one
    always says "Order action failed".
15. **Bulk cap toast.** With 31 positions, Bulk Close → All closes 30 and says "All positions have
    been closed." while one is still open. The app has "{n} positions have been closed." in its texts.
16. **Empty Profitable / Loss.** Delete categories with no orders are greyed out, but "Profitable
    Positions" with nothing in profit opens the dialog and sends `{"orderList": []}`.
17. **SL/TP 0, two rules.** The order panel takes 0 as "no SL/TP" (bug #1); Edit Position rejects
    it with "Value must be greater than 0".
18. **Silent volume changes.** Typing 100.1 lots becomes 100, and 0.15 becomes 0.1, with no message
    (order panel and One-Click tab). The close dialog rejects the same values with messages.
19. **API close.** Not seen by users (the web app lists positions first), but API clients get a
    bare 500 "Internal error". See `docs/api-notes.md`.
20. **Notification close price.** Position 2353416 (UKOIL Buy 0.2) closed in two halves. The first
    close (order 2353417) filled at 111.488 (Orders & Deals deal 1449565, P/L -3.30). Its "Position
    Closed" notification says "@ 111.49", and its details show Close Price 111.490, with the same
    P/L -3.30, which only adds up at 111.488. The second close matched. The notification seems to
    carry the requested price, not the fill, so it only shows when the fill slips. Positions History
    (average 111.485) and Orders & Deals agree with the fills. Not a strict `@defect` scenario
    because it's intermittent: the record checks take prices from the deals and compare the
    notifications on volume and P/L only.
21. **Edit Order resets while typing.** Pending order placed, page loaded, Edit opened right away
    (within ~2 s), price / SL / TP typed: in 2 of 3 tries the price and Stop Loss went back to the
    order's values while typing (once the Take Profit became "0.000"). The user may confirm values
    they didn't type. Users rarely edit that fast after a load; tests type the values again if the
    dialog put them back.
22. **Expiry date default.** For Specified Date (and Time) the date box starts at today, but the
    calendar has today greyed out (only tomorrow on can be picked). Placing with the untouched box
    is accepted (the request sends the current time), so the default is a value the calendar
    wouldn't allow.

## Open questions
- **Notifications cover positions only.** Placing, changing, deleting or expiring a pending order,
  and changing SL/TP, create no notification. Is that intended?
- **Expected texts for #12, #13, #15** (an error message for failed loads, a count in the cap
  toast) are assumptions until the product owner confirms them.
- **Fill policy differs by symbol, not by kind.** The requirement said forex offers only Fill or
  Kill. That holds for EURUSD and EURCHF, but USDSGD and NZDCHF also offer Immediate or Cancel.
  Is that intended? The tests use EURUSD and check what it offers.
- **Expected texts in `@defect` scenarios are assumptions:** the 502/503 banner (the app's own 500
  message) and USDSGD's 10.00 margin and 1,000.00 Trade Volume. Confirm with the product owner.
- **SL/TP entered as points follow the market** until the order is placed. It looks deliberate
  (the distance stays fixed), but the user isn't told.

## Not covered yet
- Bugs #2, #3, #7 and #8 (see the table).
- Trade Details for a forex symbol (EURUSD formulas were checked by hand, not by a test).
- Volume above the maximum (UKOIL 100 lots), and off-step volumes (e.g. 0.15 with a 0.1 step).
- EURUSD's "Min. Stop Distance" of 50 points: SL/TP closer than that to the price.
- Negative or decimal values typed into a Points box.
- "Swap to Units": placing an order by units instead of lots.
- Bulk close "Profitable Positions": needs the market to move past the spread (decided 2026-10-23).
- A pending order that fills: needs the market to reach the price.
- Orders the server marks `closable: false`: none could be created.
- Pending price distance boundaries ("Min. Stop Distance", EURUSD 50 points): they move with the
  live price.

## Test suite: limits and improvements
- **Market hours.** The published hours of UKOIL, EURUSD and USDSGD (`src/datas/market_hours.py`)
  pick which tags run, not the site's live market status (changed 2026-10-24). Before that,
  scenarios skipped themselves when the site said closed. So if the site had wrongly shown UKOIL
  closed during trading hours, about 156 scenarios would have skipped and the run would have looked
  fine. Now they fail. Limits:
  - **Holidays** aren't in the hours, so on a holiday the open-market scenarios fail with
    "Symbol market is closed."
  - **Server time** is UTC+3 (seen 2026-10-23/24) and is hard-coded. If it moves when daylight
    saving ends (Europe 2026-10-25, US 2026-11-01), every boundary is off by an hour. Check the
    Server Time display after 2026-11-01.
  - **UKOIL's weekday breaks** (00:00-03:05, Thursday 12:45 to Friday 03:05) leave only the
    `@any_market` scenarios to run, as does any time within 30 minutes of an opening or closing. A
    run longer than 30 minutes (the full suite takes 25-30) can still cross one.
  - **Plain `pytest`** runs everything, so at the weekend the open-market scenarios fail. Use
    `pytest -m "$(python -m src.datas.market_hours)"`.
- **Session limit.** The account keeps about 10 logins. Scenarios reuse one saved browser login
  per worker (`SavedLogins` in `tests/conftest.py`) and log in again only if it was pushed out;
  the login feature still logs in for real. `TradingApi` logs in again on a 401. What the UI does
  when its own session is pushed out mid-scenario hasn't been checked.
- **Live prices.** Trade Details lag the shown price by a few points, so checks allow 10 points.
  SL/TP sit 20-30% from the price so they never trigger mid-test.
- **Hard-coded symbol data.** `CONTRACT_SIZE` (UKOIL only) and the 1:100 leverage are constants in
  `order_panel_steps.py`. Reading them from the Specification tab and Assets page would make the
  Trade Details steps work for any symbol.
- **One shared demo account.** Every scenario that touches the account is `@trading` and runs one
  at a time on one worker, so a full run takes about 25-30 minutes. Bulk scenarios also skip if
  the account holds orders they didn't create. Anyone trading on the account by hand during a run
  can still get their positions closed by the start-of-run cleanup.
- **Timing.** Tables show a change about 1.5 s after the site answers, so checks that nothing
  changed ("… should still …") wait 2 s first. The expired-order scenario waits up to 2 minutes.
- **Slow from GitHub.** GitHub's runners are in the US (San Jose on 2026-10-24), where each request
  to the site takes 0.2-0.7 s against 0.03 s from Singapore. After login the trade page showed its
  first symbol 3.6-4.9 s after opening (under 1 s from Singapore), so with `CI` set checks wait
  15 s instead of 5. The fixed 1-2 s waits before "nothing changed" checks aren't scaled, so on
  GitHub a late change could slip past them.
- **Profitable bulk close** isn't covered: it needs the market to move past the spread first. A
  Buy and a Sell on UKOIL split into one winner and one loser within ~20 s on 2026-10-23, so a
  scenario that waits for that (and skips if the market is quiet) would be possible.
