# Trading API notes

The REST calls the AQX Trader web app makes, recorded on 2026-10-23 by driving every trading flow in
the UI with Playwright. This is the site's **internal, undocumented** API: it can change without
notice. Tokens and passwords are redacted here. Never commit a real token.

## Can tests use it to set up data without the UI?
**Yes.** A probe script did the following through the API alone:
- Logged in (0.8s).
- Opened a market order (0.4s), then closed it (0.4s).
- Placed a pending order (0.45s), then deleted it (0.45s).

Through the UI, each of these takes several seconds (search the symbol, fill the form, confirm, wait
for the table). Also:
- The UI shows API-created positions like any other.
- The create response returns the new **Order No.** (`clOrdId`), so tests don't have to work it out
  from the table.
- An API login does not log out the UI session.

Suggested split:
- Use the API for `Given` setup (open a position, place a pending order) and for cleanup.
- Use the UI only for the behaviour each scenario tests.
- #1, #2 and #3 (placing orders) must still go through the UI, because placing *is* the behaviour.

## Basics
- Base URL `https://aqxtrader.aquariux.com`. JSON in and out.
- Every response is wrapped: `{"code": "200", "result": ...}`. Errors have another code and a
  `message`, e.g. `{"code": "PW_1003", "message": "Copy trading missing authentication"}`.
- `lotSize` is in lots (UKOIL 0.1 = 100 units). Prices are plain numbers.
- Order numbers are strings in most responses, but numbers in the bulk responses.

## Auth
```
POST /api/auth/v2/metatrader5/demo/login
{"userId": "<account id>", "password": "<password>", "source": "WEB", "language": "en"}

-> {"code": "200", "result": {"token": "<JWT>", "user": {"metatraderId": "<account id>", "isDemo": true,
    "metatraderGroup": "AQR\\demo\\demo-signup", "tenantId": "aqxtrader", ...}}}
```
- Send the token on every call as `authorization: Bearer <token>`.
- The web app also sends `browserType`, `deviceType` and `marketingPageUrl` on login. The API login
  worked without them.
- The web app calls `PATCH /api/auth/v1/session` (no body, `result: true`) every few seconds as a
  keep-alive. Short API sessions worked without it.

## Values seen
| Field | Value | Meaning |
|---|---|---|
| `orderType` | 0 | Buy (market / buy position) |
| | 1 | Sell (market / sell position) |
| | 2 | Buy Limit |
| | 3 | Sell Limit |
| | 4 | Buy Stop |
| | 5 | Sell Stop |
| | 8 | Buy Stop Limit |
| | 9 | Sell Stop Limit |
| | 10, 11, 12 | Close By, Buy / Sell Market To Limit (in the app's code; not offered on web) |
| `fillPolicy` | 0 | Fill or Kill (market orders) |
| | 1 | Immediate or Cancel (market orders, where the symbol offers it) |
| | 2 | Return (pending orders) |
| `tradeExpiry` | `GTC` | Good Till Canceled |
| | `GTD` | Good Till Day (stored `expiration`: today 00:00 server time) |
| | `SPECIFIED_DAY` | Specified Date; `expiration` = that day 00:00 server time (UTC+3), epoch ms |
| | `SPECIFIED_TIMESTAMP` | Specified Date and Time; `expiration` = epoch ms, cut to the minute |
| `indicate` | `PRICE` | SL/TP are given as prices |
| `comment` | `wt\|o:...` / `wt\|c:...` / `wt\|oc:...` | set by the server: web trade open / close / partly closed |
| deal history `state` | 9 / 11 / 13 | CANCELED (deleted) / FILLED / EXPIRED (remarks "Expired [...]") |

Values from the app's code (checked 2026-10-23): `orderType` above, `fillPolicy` 3-5 (GTC, GTD,
DAY) exist but weren't seen.

## Endpoints
| UI action | Method and path |
|---|---|
| Place market order (with or without SL/TP, one-click too) | `POST /api/trade/trade/v1/market` |
| Modify position SL/TP | `PATCH /api/trade/trade/v1/market` |
| Close or partially close a position | `PUT /api/trade/trade/v1` |
| Bulk close positions | `PUT /api/trade/trade/v1/bulk` |
| Place pending order (Limit / Stop / Stop Limit) | `POST /api/trade/trade/v1/limit` |
| Modify pending order | `PATCH /api/trade/trade/v1/limit` |
| Delete pending order | `DELETE /api/trade/trade/v1?symbol=<s>&orderId=<id>` |
| Bulk delete pending orders | `PUT /api/trade/trade/v1/limit/bulk` |
| One-click trading on/off | `PATCH /api/user/setting/v1/preference` |
| Read one-click setting | `GET /api/user/setting/v1/preference?type=OCT_ENABLE&category=ONE_CLICK_TRADING` |
| Open Positions table | `GET /api/trade/order/v1` |
| Pending Orders table | `GET /api/trade/order/v1/pending` |
| Tab counts | `GET /api/trade/order/v1/counts` |
| Positions History tab | `GET /api/order/v3/histories?from=<ms>&to=<ms>&type=POSITION` |
| Orders & Deals tab | `GET /api/trade/order/v1/deal/histories?from=<ms>&to=<ms>` |
| Notifications panel | `GET /api/notification/v2?notificationType=ORDER` (or `SYSTEM`) |
| Unread counts (bell) | `GET /api/notification/v1/summary` |
| Account info (Assets, header) | `GET /api/statistics/v1/account`, `GET /api/user/account/v1` |
| Symbol search results | `GET /api/market/v1/symbols/search?text=<text>` |
| Symbol details (order panel, Specification tab) | `GET /api/market/v1/symbol/detail?symbol=<s>` |

### Market open or closed (seen 2026-10-24, a Saturday)
- `symbols/search` gives each match a `status` and `marketStatus`: `"CLOSED"` / `"CLOSED"` while
  closed. XTIUSD, the only symbol open that day, had `"TRADING"` / `"OPEN"` and `online: true`.
- `symbol/detail` has the same `status` (`marketStatus` is `null` there) and the trading hours:
  `tradingSessions` (`dayOfWeek` 1 = Monday, times in server time, UTC+3) and
  `tradingEpochSessions` (the same as epoch ms in a week of January 2021). Also `holiday`,
  `tradable`, `marketEOD`.
- UKOIL's sessions: Mon-Wed and Fri 03:05-24:00, Thu 00:00-12:45. So it's closed from 00:00 to
  03:05 on most days, from Thursday 12:45 to Friday 03:05, and at the weekend.
  EURUSD: Mon-Fri 00:00-24:00. USDSGD: Mon-Thu 00:00-23:59, Fri 00:00-23:58 (read 2026-10-24).
  XTIUSD trades every day, weekends included (01:00-24:00 Mon-Fri).
- The web app's order panel follows `symbol/detail`'s `status` (see `docs/site-notes.md`). The
  tests don't read it: they're picked by the published hours above, copied into
  `src/datas/market_hours.py`, so a wrong status from the site fails scenarios instead of hiding them.

Live prices and order updates also arrive over a SockJS websocket (`/websocket/...`). Setup doesn't
need it.

## Requests and responses

### Market order with SL/TP (#1)
```
POST /api/trade/trade/v1/market
{"orderType": 0, "symbol": "UKOIL", "lotSize": 0.2, "fillPolicy": 0, "indicate": "PRICE",
 "stopLoss": 100, "takeProfit": 120}

-> {"code": "200", "result": {"positionId": "0", "positionReference": "0", "clOrdId": "2352307", "traceId": "..."}}
```
`clOrdId` is the new position's Order No. Without SL/TP, leave out `stopLoss` / `takeProfit`.
A Sell is `orderType: 1`.

### One-click trading (#2)
```
PATCH /api/user/setting/v1/preference
{"type": "OCT_ENABLE", "category": "ONE_CLICK_TRADING", "value": "true"}      (or "false")
-> 200, empty body

GET /api/user/setting/v1/preference?type=OCT_ENABLE&category=ONE_CLICK_TRADING
-> {"code": "200", "result": [{"category": "ONE_CLICK_TRADING", "type": "OCT_ENABLE", "value": "false", "symbol": "ALL"}]}
```
- A one-click order is the same `POST /api/trade/trade/v1/market` call. Only the UI skips the
  confirmation.
- The setting is stored per account on the server, so it affects every session. Tests that turn it
  on must turn it off in teardown. This call is the quickest way to do that.

### Pending orders (#3)
```
POST /api/trade/trade/v1/limit
Buy Limit, Good Till Canceled:
{"orderType": 2, "symbol": "UKOIL", "lotSize": 0.1, "price": 100, "priceTrigger": null,
 "fillPolicy": 2, "indicate": "PRICE", "tradeExpiry": "GTC"}
Sell Stop, Good Till Day:
{"orderType": 5, "symbol": "UKOIL", "lotSize": 0.1, "price": 100, "priceTrigger": null,
 "fillPolicy": 2, "indicate": "PRICE", "tradeExpiry": "GTD"}
Buy Stop Limit (UI "Price" 120, "Stop Limit Price" 119):
{"orderType": 8, "symbol": "UKOIL", "lotSize": 0.1, "price": 120, "priceTrigger": 119,
 "fillPolicy": 2, "indicate": "PRICE", "tradeExpiry": "GTC"}

-> {"code": "200", "result": {"positionId": "0", "positionReference": "0", "clOrdId": "2352310", "traceId": "..."}}
```
```
PATCH /api/trade/trade/v1/limit                                   (modify)
{"symbol": "UKOIL", "orderId": "2352320", "orderType": 2, "fillPolicy": 2, "lotSize": 0.1,
 "price": 99, "stopLoss": 90, "tradeExpiry": "GTC", "indicate": "PRICE"}
-> {"code": "200", "result": {"positionId": "2352320", "clOrdId": "2352320", ...}}

DELETE /api/trade/trade/v1?symbol=UKOIL&orderId=2352321            (delete)
-> {"code": "200", "result": {"positionId": "2352321", "clOrdId": "2352321", ...}}
```

### Open positions (#4)
```
PATCH /api/trade/trade/v1/market                                  (modify SL/TP)
{"orderId": "2352325", "symbol": "UKOIL", "indicate": "PRICE", "stopLoss": 101, "takeProfit": 119,
 "units": 0, "fillPolicy": 0}
-> {"code": "200", "result": {"positionId": "2352325", "clOrdId": "2352325", ...}}

PUT /api/trade/trade/v1                                           (partial or full close)
{"orderId": "2352307", "symbol": "UKOIL", "lotSize": 0.1, "orderType": 0, "fillPolicy": 0}
-> {"code": "200", "result": {"positionId": "2352307", "clOrdId": "2352307", ...}}
```
- `lotSize` is how much to close: less than the position's size is a partial close, all of it is a
  full close.
- `orderType` is the position's side (0 for a Buy position, 1 for a Sell).
- The answer's `clOrdId` is the **position's** number, not the new closing order's. That one only
  shows in the history.
- **Quirk:** this call answers HTTP 500 `{"code": "500", "message": "Internal error"}` unless the same
  session has called `GET /api/trade/order/v1` since the position opened (seen every time,
  2026-10-23). The web app always has, so users don't hit it. API setup must list positions first.
  The bulk close below doesn't need it and also takes a partial `lotSize`.

### Bulk close and bulk delete (#5)
```
PUT /api/trade/trade/v1/bulk
{"orderList": [{"orderId": "2352317", "symbol": "UKOIL", "lotSize": 0.1, "fillPolicy": 0},
               {"orderId": "2352316", "symbol": "UKOIL", "lotSize": 0.1, "fillPolicy": 0}]}
-> {"code": "200", "result": {"account": "<account id>", "horizonAccountType": "NET",
    "closedOrderIds": [2352317, 2352316], ...}}

PUT /api/trade/trade/v1/limit/bulk
[{"orderId": "2352322", "symbol": "UKOIL"}, {"orderId": "2352320", "symbol": "UKOIL"}]
-> {"code": "200", "result": {"deletedOrderIds": [2352322, 2352320], ...}}
```
The UI's "All / Profitable / Loss" choice is made in the browser. The request just lists the orders
to act on, so an API cleanup can close exactly the orders a test created. The UI never sends more
than 30. A bulk close of 30 positions took about 6 s.

### Pending orders: more (checked 2026-10-23)
```
Sell Limit 125 / Buy Stop 125 (UKOIL at ~112): orderType 3 / 4, accepted.
Sell Stop Limit: "price" 100 (the stop), "priceTrigger" 101 (the limit, above it) -> accepted;
  priceTrigger 99 -> 400 {"code": "10015", "message": "Invalid price"}.
Buy Stop Limit: priceTrigger must be below price (120 / 119 accepted, 120 / 121 -> 10015).
Wrong side of the market (Buy Limit 120, Sell Limit 100, Buy Stop 100, Sell Stop 120):
  -> 400 {"code": "MT4_1009", "message": "Metatrader Invalid Price"}.
Specified Date:          {..., "tradeExpiry": "SPECIFIED_DAY", "expiration": 1792962000000}
Specified Date and Time: {..., "tradeExpiry": "SPECIFIED_TIMESTAMP", "expiration": 1793115823000}
Past expiration -> 400 {"code": "10022", "message": "Invalid order expiration"}.
```

### Settings
```
PATCH /api/user/setting/v1/preference
{"category": "MARKET", "type": "HIDE_OTHER_SYMBOLS", "value": "true"}       (or "false")
-> 200, empty body
```

### Records: lists, history, notifications (#6, #7)
Sample items, trimmed:
```
GET /api/trade/order/v1                       (Open Positions; one item per position)
{"orderId": "2352307", "symbol": "UKOIL", "lotSize": 0.2, "units": 200.0, "orderType": 0,
 "openPrice": 110.023, "currentPrice": 109.983, "takeProfit": 120, "stopLoss": 100, "profit": -8,
 "fillPolicy": 0, "openTime": 1792755103000, "comment": "wt|o:...", "symbolType": "COM", ...}

GET /api/trade/order/v1/pending               (Pending Orders)
{"orderId": "2352310", "symbol": "UKOIL", "lotSize": 0.1, "orderType": 2, "price": 100,
 "priceTrigger": 0, "tradeExpiry": "GTC", "expiration": 0, "fillPolicy": 2, "filledLotSize": 0.0, ...}

GET /api/trade/order/v1/counts
{"marketOrderCounts": 0, "pendingOrderCounts": 0}

GET /api/order/v3/histories?from=...&to=...&type=POSITION      (Positions History; one item per closed part)
{"orderId": "2352308", "positionId": "2352307", "dealId": "1448590", "symbol": "UKOIL",
 "lotSize": 0.1, "totalLotSize": 0.2, "openPrice": 110.023, "closePrice": 109.981,
 "profit": -4.2, "realizedProfitLoss": -4.2, "status": "CLOSED", "orderType": 0,
 "openTime": 1792755103000, "closeTime": 1792755143000, ...}

GET /api/trade/order/v1/deal/histories?from=...&to=...         (Orders & Deals; one item per order)
{"orderId": "2352309", "symbol": "UKOIL", "orderType": 1, "lotSize": 0.1, "lotSizeFilled": 0.1,
 "openPrice": 109.982, "state": 11, "fillPolicy": 0,
 "deals": [{"dealId": "1448591", "price": 109.982, "profit": -4.1, "lotSize": 0.1,
            "direction": 1, "takeProfit": 120, "stopLoss": 100, "comment": "wt|c:..."}], ...}

GET /api/notification/v2?notificationType=ORDER                (Notifications → Positions)
{"id": "be47852b-...", "notificationTemplate": "NT_ORDER_CLOSE", "orderId": "2352309", "read": false,
 "message": "Position Closed: #2352307  UKOIL: Size 0.1 / Units 100 @ 109.982, Loss of -4.1",
 "metadata": {"orderId": "2352307", "tradeId": "2352309", "symbol": "UKOIL", "lotSize": 0.1,
              "openPrice": 110.023, "closePrice": 109.982, "profit": -4.1, "stopLoss": 100.0,
              "takeProfit": 120.0, ...}, "created": 1792755149000, ...}
```
How the numbers link up, which is useful for #7:
- `positionId` / notification `metadata.orderId` is the position's Order No.
- History `orderId` / notification `metadata.tradeId` is the closing order's number.
- `dealId` is the deal shown when an Orders & Deals row is expanded.
- `from` and `to` are epoch milliseconds. The UI default is the last month.
- Positions History has one item per position. After the full close it adds up the parts
  (`lotSize` 0.2, the average `closePrice`, the total `profit`).
- Notifications: only `NT_ORDER_CREATE` ("Open Position: #…") and `NT_ORDER_CLOSE` ("Position
  Closed: #…", one per close). Nothing for pending orders or SL/TP changes.
- The fill is the deal: `deals[0].price` / `.profit` of the closing order in Orders & Deals. A
  notification's `metadata.closePrice` can differ from it by a few points (findings #20), so test
  setup takes close prices from the deals.

## Errors and sessions (seen 2026-10-23)
- A rejected order comes back as an HTTP error with the usual wrapper, e.g. HTTP 400
  `{"code": "10019", "message": "Not enough money"}` for USDSGD (shown in the UI as "Insufficient balance").
- An SL/TP of `0` means "none": positions without them come back with `stopLoss: 0, takeProfit: 0`.
- While the market is closed, new market and pending orders both get HTTP 400
  `{"code": "A_1047", "message": "Symbol market is closed."}` (seen 2026-10-24).
- The token is a JWT valid for 30 days. But the account keeps only about 10 sessions. Each new
  login (UI or API) logs out the oldest one, which then gets HTTP 401 `{"code": "401", "message":
  "Unauthorized"}`. `TradingApi` logs in again once when that happens.

## Still unknown
- What a rejected order returns when the SL is on the wrong side.
- What makes the server mark an order `closable: false` (every order seen so far was `true`).
- What the server answers to a bulk close with an empty `orderList`.

## Raw captures
The full redacted capture (every call, every step) is kept outside the repo. Each line has the step, method, URL, status, request/response headers and bodies, with tokens and
passwords replaced by `<redacted>`.
