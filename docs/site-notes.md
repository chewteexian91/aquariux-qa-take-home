# Site notes

## Reading the live DOM
When the user hasn't pasted HTML for part of the page, write a throwaway Playwright script in the
scratchpad (not in the repo). Run it from the project root with the root on `sys.path`, log in with
`get_user("normal")`, then print the HTML and `data-testid`s you need and take screenshots. To find new
elements fast, compare the list of `[data-testid]` values before and after an action.

## Login (`/web/login`)
- Test ids: `login-user-id`, `login-password`, `login-submit`.
- A wrong password shows "Invalid credentials, please try again." (no test id).

## Trade page (`/web/trade`)
- `symbol-overview-id` (above the chart) shows the open symbol. Wait for it to have text before
  searching: symbol data isn't loaded until then.
- The demo account opens on UKOIL. A test of "select X" should start on a different symbol, or it
  passes without anything changing.

### Symbol search (`SymbolSearch`)
- Input `symbol-input-search`. Dropdown `symbol-dropdown-result` (always in the DOM, hidden when closed).
  Result rows `symbol-input-search-items-symbol`.
- The kind tabs All / Forex / Commodities and the "No search result" message have no test ids.
  The selected tab has the class `selected`.
- After typing, the list is empty for about 0.6s while it loads, before rows or "No search result"
  appear. Don't check that something is missing until the search has loaded.
- Search ignores letter case and matches part of a symbol.
- Selecting a row closes the dropdown and leaves the symbol in the input.

### Order panel (`OrderPanel`)
- Every `trade-*` test id matches exactly one element, for both forex and commodities, **until an
  edit dialog opens**. The Edit Position / Edit Order dialogs reuse `trade-input-stoploss-*` and
  `trade-input-takeprofit-*`, so scope those to the dialog (`edit-confirmation-modal`).
- Differs by symbol: UKOIL point 0.001, min 0.1 lot (100 units). USDSGD point 0.00001, min 1000 units.
- Order Type options (no test ids, match by text inside `trade-dropdown-order-type`): Market,
  Limit, Stop, Stop Limit, the same for UKOIL and EURUSD. The `trade-dropdown-order-type-*` ids in
  the app's code aren't rendered on web. The open dropdown also contains the selected value's
  text, so don't click the option that's already selected.
- Pending types (details under "Pending order form") add `trade-dropdown-expiry` and a Price input
  with no test id (`input[name="price"]`). Stop Limit adds `input[name="priceTrigger"]` (the "Stop
  Limit Price"). Fill Policy then shows only "Return". For Market it shows "Fill or Kill".
- "Place … Order" (`trade-button-order`) opens an Order Confirmation dialog: `trade-confirmation-symbol`,
  `-order-type` (BUY, BUY LIMIT…), `-label` / `-value` pairs, `-button-confirm`, `-button-close` (Cancel).
  No dialog while one-click trading is on. Each `-value` is the next sibling of its `-label`. Rows the
  order doesn't have (no Stop Loss, say) are left out.
- **Selecting a symbol reloads the panel.** "One point equals" shows `0` for about 0.15s, and anything
  typed into the panel before the real value appears is dropped. `SymbolSearch.select` waits for it.
- Fill Policy options (Market) have no test ids: the second child of `trade-dropdown-fill-policy`,
  elements with `tabindex="0"`. They differ **by symbol, not by kind**: UKOIL, XTIUSD, USDSGD and NZDCHF
  offer Fill or Kill and Immediate or Cancel. EURUSD and EURCHF offer only Fill or Kill.
- Validation messages have no test ids. Each is the element right after the input's wrapper.
  - Volume: "Please enter a valid volume." (0), "Minimum volume is 0.1." (UKOIL, below min)
  - Buy: "Stop Loss must be less than Sell Price." / "Take Profit must be greater than Sell Price."
  - Sell: "Stop Loss must be greater than Buy Price." / "Take Profit must be less than Buy Price."
  - Place stays enabled while one shows. Clicking it opens nothing, unless focus has been in the
    Points box (see the bugs below).
- Typed prices are rounded to the point size without a message (`120.0009` → `120.001`).
- **Market closed** (checked 2026-10-24, a Saturday): the Place button (`trade-button-order`) is
  disabled and reads "MARKET CLOSED". On the One-Click tab the same button takes the place of the
  one-click BUY / SELL. The page text is "Market Closed"; CSS shows it in capitals, so match it
  ignoring case. For about 0.1s after a symbol is selected it reads "Stay Tuned" (loading).
  BUY / SELL, Volume and the other fields stay enabled, and the prices stay at the last close.
  The chart header doesn't show it.
  The panel takes this from the symbol's details (`GET /api/market/v1/symbol/detail`, `status`
  "TRADING" or "CLOSED"), read once when the symbol opens. Faking that answer in the browser makes
  the panel show the market closed (or open) at any time (checked 2026-10-24 both ways, on UKOIL
  and XTIUSD). `Given the "<symbol>" market is mocked as closed` does that.
  An order that reaches the server while the market is closed gets the toast "Symbol market is closed."
  `Given "<symbol>" is open for trading` fails when the panel shows "Market Closed": those
  scenarios run only during the published hours (`src/datas/market_hours.py`).

### Order panel bugs (2026-10-23)
- **A Stop Loss / Take Profit of 0 means "none"**, and 0 is "below the price". So a Buy's SL or a
  Sell's TP of `0.000` (or `0.00000001`, rounded to `0.000`) shows no error. The confirmation says
  "0.000", the request sends `0`, and the position opens with `--`.
- **Sell with SL `0.000`, then Tab:** the error shows, but Place clears the box and opens the
  confirmation without a Stop Loss. Leaving the field with a plain blur, Place is blocked as it
  should be. With focus in Points, Place also recalculates an invalid price from the points
  (Buy SL `150` became `149.989`, Buy TP `0.000` became `0.003`).
- **Typed prices drift once the Points box gets focus.** Tab from a typed Stop Loss / Take Profit price
  moves into its Points box. From then on the site moves the price with the market (typed `133.441`,
  sent `133.469` after the price rose 28 points). A price pasted in one go (Playwright `fill`)
  drifts too. Tests type key by key (`press_sequentially`) and leave with `blur()`, which keeps the
  typed price.
- A Stop Loss / Take Profit **entered as points** follows the market until the order is placed. It
  stays exactly that many points from the close price (a Buy closes at the Sell price). That looks
  deliberate.
- **USDSGD**: Est. Margin Required shows 1,277,800.00 USD for 0.01 lot (1,000 USD; should be 10.00
  at 1:100), and the server rejects every USDSGD order (HTTP 400 `{"code": "10019", "message":
  "Not enough money"}`, banner "Insufficient balance"). Trade Volume, Potential Loss and Gain
  are in SGD under "Trade Details (USD)".

### Pending order form (checked 2026-10-23)
- Expiry options (no test ids, in this order): Good Till Canceled, Good Till Day, Specified Date and
  Time, Specified Date. Same for every pending type and symbol tried.
- Specified Date adds `trade-input-expiry-date`, "and Time" adds `trade-input-expiry-time` too. Both
  start at the **server's** date and time (top right "Server Time", UTC+3), not the browser's.
  - Date: click the box's `[tabindex="0"]` to open a react-calendar. Days are
    `button.react-calendar__tile` holding `abbr[aria-label="October 26, 2026"]`. Days up to and
    including today, and the previous-month arrows, are disabled; tomorrow is the first day that
    can be picked. Yet the box starts at today, and placing with it is accepted (findings #22).
  - Time: click the box to open Hour and Minute dropdowns (00-23, 00-59, no test ids) with Clear /
    OK. Past hours are **not** disabled. The open hour list sits outside the picker's element: its
    options are the only visible "00"…"23" texts.
- Checked in the browser (messages under the field, Place opens nothing):
  - Empty Price: "Please enter a valid price."
  - SL/TP against the order's **Price** (lower-case "price"): Buy "Stop Loss must be less than
    price." / "Take Profit must be greater than price."; Sell "Stop Loss must be greater than
    price." / "Take Profit must be less than price.".
  - Volume: same messages as a market order.
- **Not checked in the browser** (the confirmation opens, the server rejects on Confirm, the banner
  shows the server's message):
  - Price on the wrong side of the market (Buy Limit / Sell Stop above it, Sell Limit / Buy Stop
    below it): HTTP 400 `MT4_1009` "Metatrader Invalid Price".
  - Stop Limit Price on the wrong side of the Price (a Buy Stop Limit needs it below, a Sell Stop
    Limit above): `10015` "Invalid price".
  - An expiry time already past today: `10022`, banner "Invalid Expiration Date. Please try again.".
- Volume above the maximum is capped to 100 and off-step volumes are cut to the step (0.15 → 0.1),
  both without a message. The One-Click tab does the same.
- Confirmation: `trade-confirmation-order-type` "BUY LIMIT" etc., rows Volume, Units, Price, Stop
  Limit Price, SL/TP, Expiry, "Expiry Date" (`2026-10-26`) or "Expiry Date & Time"
  (`2026-10-27 18:43`), Fill Policy Return, Est. Margin Required (Stop Limit: from the Stop Limit
  Price). Toast "Order has been created.".

### Trade Details
- Collapsed by default; the title "Trade Details (USD)" toggles it. The header gets the class
  `expanded` while open. Rows `trade-details-*`, each a label `div` then a value `div`. All 0.00
  until the order has a volume.
- Formulas (UKOIL and EURUSD; leverage 1:100). Entry = Buy price for a Buy, Sell price for a Sell:
  - Trade Volume = units × entry
  - Est. Margin Required = Trade Volume ÷ 100
  - Amount Per Tick = units × one point, shown "+/- 0.10"
  - Potential Loss / Gain = (SL or TP − entry) × units, the other way round for a Sell
  - Risk:Reward = "1 : " + gain ÷ |loss| to 2 dp. Without SL/TP: 0.00, 0.00 and blank.
- They're worked out from a price a few points behind the one shown, and not all rows from the
  same one. Checks allow 10 points.

### Error banners (order request failed)
The `notification-box-description` banner, gone after about 5s.

| Request | Banner |
|---|---|
| network error / blocked / timeout | "Network error. Please try again later." |
| 500 (JSON) | "Something went wrong. Please contact customer support." |
| 4xx (JSON `{code, message}`) | the `message`, except known codes (10019 → "Insufficient balance") |
| 502/503 page, not JSON | "/api/trade/trade/v1/market POST (503 - Service Unavailable)" (bug) |
| 200 with an error `code` | "Position has been created." (only if the server ever answers that way) |

### One-click trading
- Gear `app-setting-dropdown-trigger` → switch `toggle-oct` (off) / `toggle-oct-checked` (on).
- Turning it on opens a dialog with no test ids: "One-Click Trading | Terms and Conditions", buttons
  "CANCEL" and "AGREE AND CONTINUE". Cancel leaves it off. Agree: toast "One-Click Trading
  activated." and the tab below appears.
- Turning it off: no dialog and no toast.
- If the setting request fails (500 or network error), the switch stays as it was and **nothing
  tells the user**, on or off.
- While on, the order panel gets a tab `tab-one-click-trading` with `trade-input-volume` (empty,
  placeholder "Min: 0.1") and `trade-button-oct-order-buy` / `-sell`, which trade at once
  (`POST /api/trade/trade/v1/market`, toast "Position has been created."). An invalid volume
  shows the usual message under the box and sends nothing.
- While on, the order panel **opens on the One-Click tab**, which has no "One point equals" label
  (so `SymbolSearch.select` waits for the symbol name there instead). Switch to `tab-trade` to use
  the order form.
- While on, the Trade tab's Place sends market **and pending** orders without the confirmation.
- The settings menu closes by itself after the switch is clicked.
- Failed one-click orders show the same banners as market orders.
- **Saved on the server for the account** (`OCT_ENABLE`), so it changes every session. Tests must
  set it on purpose and switch it back. "Hide Other Symbols" is a server setting as well.

### Hide Other Symbols
- Checkbox above the tables: `hide-other-symbols-button` (off) / `hide-other-symbols-button-checked`
  (on), label "Hide Other Symbols".
- Saved on the server: `PATCH /api/user/setting/v1/preference`
  `{"category": "MARKET", "type": "HIDE_OTHER_SYMBOLS", "value": "true"}`.
- While on, the tables and tab counts show only the open symbol, and bulk close / bulk delete act
  only on its orders.

### Toasts
- `notification-box-description`, e.g. "Position has been created.", "Position has been updated.",
  "Position has been closed.", "Order has been created.", "Order has been updated.",
  "Order has been deleted.", "All positions have been closed.", "All pending orders have been deleted.".
- The toast does not include the Order No.

### Open Positions table
- Tab `tab-asset-order-type-open-positions` ("Open Positions (N)"). Rows `asset-open-list-item`.
  Cells `asset-open-column-*`: open-date, order-id, symbol, order-type (BUY/SELL), profit, roi,
  volume, units, margin-used, entry-price, current-price, take-profit, stop-loss, swap, comment.
  Buttons `asset-open-button-track` / `-edit` / `-close`.
- **Loading quirk:** for about 0.4s after login or reload, the tab shows "(0)" and
  "You have no open positions." even when there are positions, and this is *after* the open symbol
  has loaded. The real list comes from `GET /api/trade/order/v1` (`docs/api-notes.md`). Wait for that
  response before trusting an empty table.
- A new row shows about 1.5s after the toast.
- Prices show the symbol's decimals (`77.500`). No Stop Loss / Take Profit shows `--`.
- Close: Close button → "Confirm To Close Position" dialog (no root test id: use the ancestor of that
  text): symbol, Order No., Volume "/0.2" (the position size), MIN / MAX, Fill Policy "Fill or Kill".
  - Volume `input[name="lotSize"]` (no test id). The order panel's volume has the same name, so
    scope it to the dialog. `close-order-input-volume-static-min` / `-max` fill the minimum / the
    position size. `edit-dropdown-fill-policy`.
  - Confirm / Cancel have no test ids (role button, names "Confirm" / "Cancel"). Confirm is
    disabled while the volume is empty or shows an error: empty, 0 or off-step (0.15) → "Please
    enter a valid volume.", 0.05 → "Minimum volume is 0.1.", above the size → "Maximum volume is 0.2.".
  - Toast "Position has been closed." for a partial and a full close. **A partial close keeps the
    Order No.** (the comment becomes `wt|oc:…`). A Sell close sends `orderType: 1`.
  - After a failed request the dialog stays open and the row is unchanged.
- Edit: pencil → `edit-confirmation-modal` ("Edit Position") with `edit-symbol-value`,
  `edit-order-type-value`, `edit-order-id-value`, `edit-entry-price-value`, `edit-volume-value`,
  `edit-units-value`, SL/TP inputs, `edit-button-order` ("UPDATE POSITION"), `edit-button-cancel`.
  - Same wrong-side messages as the order panel ("Stop Loss must be less than Sell Price." …), and
    Update opens nothing while one shows.
  - While it's open, the order panel's live prices read empty: read the market before opening it.
  - SL/TP `0` → "Value must be greater than 0" (the order panel instead takes 0 as "none").
    Emptying a box removes that SL/TP: no error, and the confirmation leaves the row out.
  - Update opens the Order Confirmation (`trade-confirmation-button-confirm`). Toast "Position has
    been updated.". After a failed request the dialog stays open and the row is unchanged.
- Bulk Close: see "Bulk close and bulk delete".

### Pending Orders table
- Tab `tab-asset-order-type-pending-orders`. Rows `asset-pending-list-item`. Cells `asset-pending-column-*`:
  open-date, order-id, symbol, order-type (BUY LIMIT…), volume ("0.1 / 0"), units, fill-policy,
  expiry, expiry-date, entry-price, current-price, take-profit, stop-loss.
- Row buttons reuse **`asset-open-button-*`** ids (track / edit / close = delete), so scope them to the row.
- Expiry cells: Good Till Canceled "--", Good Till Day today's date (`2026-10-23`), Specified Date
  `2026-10-26`, Specified Date and Time `2026-10-27 18:43:00`. Price is in `entry-price`.
- Edit opens an "Edit Order" dialog with **no root test id** (unlike Edit Position): use the ancestor
  of `edit-button-order` that contains `edit-symbol-value`. Inside: Price `input[name="price"]`,
  SL/TP `trade-input-stoploss-*` / `trade-input-takeprofit-*` (the order panel has the same ids, so
  scope them), `edit-dropdown-expiry` (the same 4 options), `edit-order-id-value`… Opened within a couple of seconds of a page
  load, it can put the order's values back over what is being typed (findings #21). The button
  `edit-button-order` reads "CONFIRM" and is enabled even with nothing changed. It opens the Order
  Confirmation. Toast "Order has been updated.". Same checks as the order form (SL/TP against the
  price; the price against the market isn't checked).
- Delete opens a dialog with **no test ids**: "Confirm To Delete Order | UKOIL | BUY LIMIT | Order
  No. | 2352593 | Would you like to delete the pending order?", buttons Cancel / Confirm. Toast
  "Order has been deleted.".
- After a failed place / modify / delete the dialog stays open and the row is unchanged.
- Bulk Delete: see "Bulk close and bulk delete".
- After a reload the bottom tabs reset to Open Positions.

### Bulk close and bulk delete (checked 2026-10-23)
- `bulk-close` (Open Positions) → menu items with no test ids: "All Positions", "Profitable
  Positions", "Loss Positions". Dialog "Bulk Close":
  - All: "Up to 30 positions can be closed. Would you like to close all positions?",
    `bulk-close-modal-button-submit-all` / `-cancel-all`.
  - Profitable: "Up to 30 open profitable positions can be closed. Would you like to close all
    profitable positions?", `-submit-profit` / `-cancel-profit`.
  - Loss: "Up to 30 open losing positions can be closed. Would you like to close all losing
    positions?", `-submit-loss` / `-cancel-loss`.
- `bulk-delete` (Pending Orders) → "All Orders", "Limit Orders", "Stop Orders", "Stop Limit Orders".
  Dialog "Bulk Delete": "Up to 30 pending / limit / stop / stop limit orders can be deleted. Would
  you like to delete all … orders?". All Orders uses `bulk-close-modal-button-submit-all` /
  `-cancel-all`; the other three dialogs' buttons have no test ids (role button Confirm / Cancel).
- Which orders are sent (worked out in the browser when Confirm is clicked):
  - All: every listed order the server marks `closable: true` (every order seen so far is).
  - Profitable: live profit > 0. Loss: profit < 0. A position at exactly 0 is in neither.
  - Limit: Buy and Sell Limit. Stop: Buy and Sell Stop. Stop Limit: Buy and Sell Stop Limit.
  - With Hide Other Symbols on, only the open symbol's orders.
  - **At most 30.** The tables show 30 rows per page. With 31 open, 30 are sent and closed /
    deleted and 1 stays. Which one stays isn't predictable.
- Delete categories with no orders are greyed out (cursor not-allowed) and clicking does nothing.
  With no pending orders at all the menu doesn't open. The close options are never greyed out:
  Profitable with nothing in profit still opens the dialog and sends an empty list.
- Toasts: "All positions have been closed.", "All profitable positions have been closed.", "All
  losing positions have been closed.", "All pending orders have been deleted.", "All limit orders
  have been deleted.", "All stop orders have been deleted.", "All stop limit orders have been
  deleted.". The same text shows when the cap left one behind.
- Any failure (4xx, 5xx, network): banner "Order action failed" (not the server's message), the
  dialog stays open, nothing changes.
- A fresh position is not reliably at a loss: UKOIL moved past the 40-point spread within ~20 s.

### History tabs
- `tab-asset-order-type-history-positions-history`: rows `asset-history-position-list-item`, cells
  `asset-history-column-*` (open-date, symbol, close-date, order-id, order-type, profit, volume,
  units, entry-price, close-price, take-profit, stop-loss, swap, commission, remarks, comment).
  - One row per position, under the position's Order No. After a partial close (position still
    open) it shows the closed part: volume "0.1 / 0.2", that part's close price and P/L. After the
    full close it's one row: volume 0.2, the average close price (111.9665 shown as 111.967), the
    total P/L. Type is "BUY".
- `tab-asset-order-type-history-orders-and-deals`: the same row and cell ids plus `state` and
  `fill-policy`. One row per order: the opening order (Type "Buy", FILLED, volume "0.2 / 0.2") and
  one per close (Type "Sell", FILLED, **a new Order No.** each time).
  - `asset-history-position-list-item-expand` opens the deals: rows right after it with no test
    ids: open date, symbol, deal no., "In" / "Out", volume, units, P/L, comment.
  - `state` holds "Filled" / "Canceled" / "Expired"; CSS shows them upper case (FILLED…). Compare
    with `use_inner_text=True` to match what's shown.
  - A deleted pending order: Type "Sell Limit", state CANCELED, volume "0.1 / 0". An expired one:
    state EXPIRED, close date = the expiry time, remarks "Expired [2026-10-23 19:17]". Neither shows
    in Positions History. (API `state`: 9 cancelled, 11 filled, 13 expired.)
  - An order with Specified Date and Time leaves Pending Orders within a second of its expiry
    minute (the server keeps the expiry to the minute).
- Both tabs show 30 rows per page, newest first ("1 - 30 of 413 orders", "Page 1 of 14", prev / next).
- Date range `orders-date-picker-icon-calendar` → `orders-date-picker-dropdown`: All, Last 7 days,
  Last 30 days (the default), Last 90 days, This year, Last year, Custom, a range calendar, and
  `orders-date-picker-button-apply` / `-cancel` / `-reset`.
- Filter `orders-filter-button-icon-filter`: Sort By, Asset Type, Order Type, State
  (`orders-filter-order-state-checkbox-ALL` / `-9` Canceled / `-11` Filled / `-13` Expired),
  `orders-filter-dropdown-button-apply` / `-cancel` / `-reset-all`.
- A failed load (500 or network) shows no banner, just the empty state: "You have no orders & deals
  history." / "You have no order histories.".

### Notifications
- Bell `notification-selector` → `notification-dropdown-result`. Tabs `tab-notification-type-order`
  (Positions), `-system` (with an unread count), `-information`. "Notifications display for up to 30
  days." Empty: "No new notifications." No "mark all as read" on web.
- **Only two kinds of order notification**: "Position Created" and "Position Closed" (one per
  close, partial closes included). Pending orders (placed, changed, deleted, expired) and SL/TP
  changes get none. Each login adds a System "New Login Detected".
- Items `notification-list-result-item` with `-title` and `-meta` ("UKOIL  |  Order No. 2352829",
  the **position's** number, closes too). The rest has no test ids: side, "0.2 volume(s)", "at",
  the price, "a few seconds ago", and the P/L for closes ("-4.40"). They show up within a second or two.
- A close's price in the notification can differ from the fill by a few points (findings #20);
  the P/L matches the fill. Orders & Deals has the fill.
- Clicking an item opens `notification-order-details-modal` ("Order Details"): title, Created Time,
  Closed Time, symbol, side, Order No., Volume, Units, Profit/Loss, ROI%, Entry Price, Close Price,
  Stop Loss, Take Profit, Commission, Swap, Remarks, and a CLOSE button. The labels and values have
  no test ids on web.
- A failed load (500) shows "No new notifications.", no error.

### Sessions
- Two logins to the same account at once both stay active (checked with a trade from the first
  after the second logged in). Each session sees the other's orders straight away.
- **But only about 10 at once.** Each new login (UI or API) logs out the oldest session, which then
  gets HTTP 401. Every scenario logs in, so the test run's API session is soon the oldest.
  `TradingApi` logs in again once on a 401. The token itself is valid for 30 days. *Not checked:*
  what the UI does when its own session is pushed out.

## Test symbols
- Commodities: UKOIL (Brent Crude Oil). Point 0.001, min 0.1 lot, 1 lot = 1,000 units.
- Forex for orders: EURUSD (Euro vs US Dollar). Point 0.0001, min 0.01 lot, 1 lot = 100,000 units,
  Fill or Kill only, Min. Stop Distance 50 points (UKOIL's is 0).
- Forex for search: USDSGD (US Dollar vs Singapore Dollar). USDSGX doesn't exist. Orders on USDSGD
  are rejected on this account (see the order panel bugs).
