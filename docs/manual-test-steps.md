# Manual test steps: trading

How to do each item in the functional scope by hand on the demo account, and what you should see.
Written from the live site on 2026-10-23 (UKOIL at about 110.000). Things marked *not checked* were
not tried.

## Before you start
- Log in at `/web/login` with the demo account (`normal` in `src/test_data/user.json`). The trade page
  opens on UKOIL.
- Markets must be open. UKOIL is closed at weekends. While a symbol's market is closed, the Place
  button reads "Market Closed" and can't be clicked, and the One-Click tab has no BUY / SELL.
- Use the minimum volume unless a step needs more. UKOIL: min 0.1 lot (= 100 units), one point = 0.001.
  The Volume field shows the minimum for the open symbol.
- Everyone shares this account. Write down the **Order No.** of everything you create, and only touch
  those rows. Bulk actions hit everyone's orders (see section 5).
- After each action a message (toast) shows at the top of the page for a few seconds.

## Where things are
| Area | What's there |
|---|---|
| Order panel (right) | BUY / SELL, Order Type, Volume, Fill Policy, Stop Loss, Take Profit, Expiry (pending only), "Place Buy/Sell Order" |
| Bottom tables | Tabs: Open Positions, Pending Orders, Positions History, Orders & Deals. Plus Bulk Close / Bulk Delete, "Hide Other Symbols", a date range and Filter |
| Bell icon (top right) | Notifications panel, with tabs Positions / System / Information |
| Gear icon (top right) | Settings, including the **One Click Trading** switch |
| Assets (left sidebar) | Account info (balance, realised P/L, deposit…) and the same tables |

Row buttons in Open Positions and Pending Orders: **Track**, **Edit** (pencil), **Close**/**Delete**.

---

## 1. Market order with Stop Loss and Take Profit

**Buy**
1. Order Type: **Market**. Click **BUY**.
2. Volume: `0.2` (0.2 lets you try a partial close later, in section 4).
3. Stop Loss price **below** the current price, e.g. `100`. Take Profit price **above** it, e.g. `120`.
   The Points boxes fill in by themselves.
4. Click **Place Buy Order**. An **Order Confirmation** dialog shows UKOIL, BUY, Volume 0.2, Units 200,
   Stop Loss 100.000, Take Profit 120.000, Fill Policy Fill or Kill, and Est. Margin Required.
5. Click **Confirm**.

Expected:
- Toast "Position has been created."
- Open Positions goes up by one. The new row shows Order No., BUY, volume 0.2, units 200, an entry
  price, Take Profit 120.000 and Stop Loss 100.000.
- The bell shows a "Position Created" notification with the same Order No.

**Sell**: the same, but click **SELL**, with Stop Loss **above** the price and Take Profit **below** it.

SL/TP on the wrong side of the price shows an error under the field (texts in `docs/site-notes.md`).
A price of `0.000` on the "right" side (Buy SL, Sell TP) is accepted and means *no* SL/TP, which is a
defect (`docs/defects.md` #1). Type prices and click away rather than pressing Tab: with the Points box focused, the
price follows the market.

## 2. Market order with One-Click Trading

**Turn it on**
1. Gear icon → switch **One Click Trading** on.
2. A "One-Click Trading — Terms and Conditions" dialog opens. Click **Agree and continue**.
3. The switch is on, and the order panel gets a new **One Click** tab (Volume plus BUY/SELL buttons
   with live prices).

**Place orders**
1. Open the **One Click** tab. Volume: `0.1`.
2. Click **SELL** (or **BUY**).

Expected:
- The order goes through straight away, with **no confirmation dialog**.
- Toast "Position has been created." and a new row in Open Positions.
- While one-click is on, the normal **Trade** tab's "Place Buy/Sell Order" also skips the
  confirmation.

**Turn it off when done**: gear icon → switch off (no dialog). The One Click tab disappears.
This setting is saved on the account, so it changes every session and every other tester. Always
switch it off.

While it's on, Place on the Trade tab also skips the confirmation for pending orders. Turning it
off shows no message. *Not checked:* the terms say closing or deleting from the positions table is
also one-click while it's on.

## 3. Pending orders (order types and expiry)

**Order types:** Limit, Stop, Stop Limit. All of them have Price, Stop Loss, Take Profit and Expiry.
Stop Limit also has **Stop Limit Price**. Fill Policy shows **Return**.

**Expiry options:**
- Good Till Canceled
- Good Till Day
- Specified Date and Time (shows date and time boxes)
- Specified Date (shows a date box)

The date and time boxes start at the server's date and time (shown top right, UTC+3). Past days
are greyed out in the calendar; past hours are not, and a past time is only rejected after
Confirm ("Invalid Expiration Date. Please try again.").

The form checks Stop Loss / Take Profit against the order's Price, but not the Price against the
market: a Buy Limit above the market reaches the confirmation and is rejected after Confirm
("Metatrader Invalid Price").

**Prices** (set them far from the market so the order doesn't fill while you test):

| Order | Price |
|---|---|
| Buy Limit | below the market, e.g. `100` |
| Sell Limit | above the market |
| Buy Stop | above the market |
| Sell Stop | below the market, e.g. `100` |
| Buy Stop Limit | Price above the market, e.g. `120`, and Stop Limit Price `119`. This was accepted. |

**Place**
1. Order Type: **Limit**. Click **BUY**. Volume `0.1`. Price `100`. Expiry: **Good Till Canceled**.
2. Click **Place Buy Order**. The confirmation shows "BUY LIMIT", Volume, Units, Price 100.000,
   Expiry, Fill Policy Return and Est. Margin Required. Click **Confirm**.

Expected:
- Toast "Order has been created."
- Pending Orders goes up by one. The row shows Order No., BUY LIMIT, Volume `0.1 / 0` (ordered /
  filled), Fill Policy Return, Expiry, Expiry Date, Price and Current Price.
- With **Good Till Day**, the Expiry Date column shows today's date. With Good Till Canceled it shows `--`.

Repeat for Sell Stop and Buy Stop Limit, and for each expiry option.

**Modify**
1. Click the pencil on the row. An **Edit Order** dialog opens (symbol, type, Order No., Volume, Units,
   Fill Policy, plus editable Price, Stop Loss, Take Profit and Expiry).
2. Change Price to `99` and Stop Loss to `90`. Click **Confirm**, then **Confirm** again in the Order
   Confirmation.

Expected: toast "Order has been updated." The row shows Price 99.000 and Stop Loss 90.000, with the
same Order No.

**Delete**
1. Click the Delete icon on the row, then **Confirm**.

Expected: toast "Order has been deleted." The row is gone, and Orders & Deals lists the order as **CANCELED**.

**Expire**: place an order with Specified Date and Time a minute or two ahead. Within a second of
that minute it leaves Pending Orders, and Orders & Deals lists it as **EXPIRED** ("Expired [date
time]" in Remarks). No notification is sent for pending orders.

## 4. View, modify, partially close and close open positions

Start with a 0.2 lot position from section 1.

**View**: Open Positions columns are Open Date, Order No., Symbol, Type, Profit/Loss, ROI%, Volume,
Units, Margin Used, Entry Price, Current Price, Take Profit, Stop Loss, Swap and Comment. Profit/Loss and
Current Price change live.

**Modify SL/TP**
1. Click the pencil. An **Edit Position** dialog shows the symbol, side, Order No., Entry Price,
   Volume, Units, and editable Stop Loss / Take Profit.
2. Change SL to `101` and TP to `119`. Click **Update Position**, then **Confirm** in the Order
   Confirmation.

Expected: toast "Position has been updated." The row shows SL 101.000 and TP 119.000.

**Partial close**
1. Click the Close icon. A **Confirm To Close Position** dialog opens with the symbol, Order No., a
   Volume box ("/0.2" shows the full size), **Min** / **Max** buttons and Fill Policy.
   Confirm stays disabled until a volume is entered.
2. Enter `0.1`. Click **Confirm**.

Expected:
- Toast "Position has been closed."
- The row **keeps the same Order No.**, now with volume 0.1.
- Positions History gets a row for the closed 0.1 under the same Order No.
- Orders & Deals gets a new Sell order with its own Order No.

**Close**
1. Click the Close icon, then **Max**, then **Confirm**.

Expected: toast "Position has been closed." The row is gone. Positions History now has one row
for the whole position: volume 0.2, the average close price and the total P/L.

## 5. Bulk close and bulk delete

**Warning:** these act on **every** open position or pending order on the account, including other
testers' orders. Only use them when no one else is using the account.

**Bulk Close** (Open Positions tab)
1. Open two or more positions.
2. Click **Bulk Close**. The menu offers All Positions, Profitable Positions and Loss Positions.
3. Pick **All Positions**. A dialog says "Up to 30 positions can be closed. Would you like to close
   all positions?". Click **Confirm**.

Expected: toast "All positions have been closed." and Open Positions (0).

For Profitable / Loss Positions you need one winning and one losing position at the same moment:
open a Buy and a Sell on UKOIL and wait for the price to move past the 40-point spread (it took
about 20 s on 2026-10-23). Profitable closes only the one in profit ("All profitable positions have
been closed."), Loss only the one at a loss ("All losing positions have been closed.").

With more than 30 positions, one bulk action closes 30 and leaves the rest (the toast still says
"All …").

**Bulk Delete** (Pending Orders tab)
1. Place two or more pending orders.
2. Click **Bulk Delete**. The menu offers All Orders, Limit Orders, Stop Orders and Stop Limit Orders.
3. Pick one, then **Confirm**.

Expected: toast "All pending orders have been deleted." (or "All limit / stop / stop limit orders
have been deleted.") and Pending Orders (0), or only the other types left. Types with no orders
are greyed out in the menu.

**Hide Other Symbols** (checkbox above the tables): while it's ticked, the tables and both bulk
actions only cover the open symbol. It's saved on the account, so untick it afterwards.

## 6. Transactions, notifications and order history

**Toasts**, one per action:

| Action | Toast |
|---|---|
| Market order | Position has been created. |
| Modify position | Position has been updated. |
| Close / partial close | Position has been closed. |
| Pending order placed | Order has been created. |
| Pending order modified | Order has been updated. |
| Pending order deleted | Order has been deleted. |
| Bulk close | All positions have been closed. |
| Bulk delete | All pending orders have been deleted. |

**Notifications** (bell icon)
- Tabs: **Positions** / **System** / **Information**. The panel says "Notifications display for up
  to 30 days."
- Each item has a title (e.g. Position Created, Position Closed), `UKOIL | Order No. <n>`, the side,
  "0.1 volume(s) at <price>", a time ("2 minutes ago"), and the P/L for closes.
- Unread items have a dot. The System tab shows an unread count.
- Only positions get notifications: "Position Created", and one "Position Closed" per close
  (a partial close gets its own, with that part's volume and P/L). All use the position's Order No.
  Pending orders and SL/TP changes get none.
- Clicking an item opens "Order Details" (times, side, volume, units, P/L, ROI%, entry and close
  price, SL, TP).

**Positions History tab**
- One row per closed position (or closed part).
- Columns: Open Date, Symbol, Close Date, Order No. (the position's own number), Type, Profit/Loss,
  Volume, Units, Entry Price, Close Price, TP, SL, Swap, Commission, Remarks and Comment.
- Use the date range to look further back. It defaults to the last month.

**Orders & Deals tab**
- One row per order: opening orders, closing orders and pending orders.
- Columns include State (**FILLED**, or **CANCELED** for deleted pending orders), Volume
  (filled / ordered), Fill Policy and Entry Price.
- The arrow on a row expands its **deal(s)**: e.g. an "Out" deal with its own deal number, the
  volume, TP/SL and the P/L.

**Assets page** (left sidebar → Assets)
- Account information: Account ID, Leverage, Available Balance, Realised Profit/Loss, Credit,
  Deposit, Withdrawal.
- "P/L Statistics for Past 14 days", the same tables, and a download icon. *Download not checked.*

## 7. Check details and status across records

Follow one trade through every place it shows up, and check the same values everywhere:

| Record | Check |
|---|---|
| Order Confirmation dialog | symbol, side, volume, units, SL, TP (and price/expiry for pending) |
| Toast | the message for the action (table above) |
| Open Positions / Pending Orders row | Order No., symbol, type, volume, units, SL, TP, price, expiry |
| Notification | same Order No., symbol, side, volume, price. P/L on close |
| Positions History (after close) | same Order No. (the position's), entry/close price, volume closed, P/L |
| Orders & Deals | opening order FILLED; the closing order has a **new** Order No.; deal P/L matches the notification; deleted pending order is CANCELED |
| Assets | Realised Profit/Loss and Available Balance move by the closed P/L |

Things that look odd but are expected:
- Closing a position creates a new order (e.g. position 2352302 was closed by Sell order 2352303).
  Positions History and the notification use the position's number (2352302).
- A partial close keeps the position's Order No. Each closed part shows up separately in history.

## Clean up
Close your positions, delete your pending orders, and **switch One Click Trading off**.
