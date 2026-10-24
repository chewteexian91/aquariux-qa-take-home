"""The test symbols' published trading hours, and which scenarios can run at a given time.

The hours are expected values (the site's symbol details, read 2026-10-24, docs/api-notes.md).
The tests don't ask the site whether a market is open: if the site said closed during these
hours, its scenarios would quietly not run. Instead they run, and fail.

Scenarios with no market tag need the market open. `@any_market` ones run at any time.
`@closed_market` ones need it really closed. CI picks them with:

    pytest -m "$(python -m src.datas.market_hours)"
"""
from datetime import datetime, timedelta, timezone

# The hours follow the server's clock (top right of the trade page).
SERVER_TIME = timezone(timedelta(hours=3))
# About as long as a full run. The market must stay as it is for that long.
RUN_MINUTES = 30

# Weekday (0 = Monday) -> (opens, closes), server time. Days not listed are closed.
TRADING_HOURS = {
    "UKOIL": {0: ("03:05", "24:00"), 1: ("03:05", "24:00"), 2: ("03:05", "24:00"),
              3: ("00:00", "12:45"), 4: ("03:05", "24:00")},
    "EURUSD": {day: ("00:00", "24:00") for day in range(5)},
    "USDSGD": {0: ("00:00", "23:59"), 1: ("00:00", "23:59"), 2: ("00:00", "23:59"),
               3: ("00:00", "23:59"), 4: ("00:00", "23:58")},
}

# pytest -m expressions
MARKET_OPEN = "not closed_market"
MARKET_CLOSED = "any_market or closed_market"
MARKET_CHANGING = "any_market"


def is_open(symbol: str, at: datetime) -> bool:
    server_time = at.astimezone(SERVER_TIME)
    hours = TRADING_HOURS[symbol].get(server_time.weekday())
    if hours is None:
        return False
    opens, closes = hours
    return opens <= server_time.strftime("%H:%M") < closes  # "HH:MM" strings sort by time


def market_marker(now: datetime) -> str:
    """The -m expression for the scenarios that can run from `now` for a whole run.

    Open means every test symbol is open throughout, closed means every one is closed. Otherwise
    (a market opens or closes during the run, or one is open and another closed) only the
    `@any_market` scenarios run.
    """
    minutes = [now + timedelta(minutes=m) for m in range(RUN_MINUTES + 1)]
    states = {is_open(symbol, at) for symbol in TRADING_HOURS for at in minutes}
    if states == {True}:
        return MARKET_OPEN
    if states == {False}:
        return MARKET_CLOSED
    return MARKET_CHANGING


if __name__ == "__main__":
    print(market_marker(datetime.now(timezone.utc)))
