"""Helpers for checks against live prices, shared by the order panel and confirmation steps.

Not a step file: it holds no steps, so it isn't registered in `pytest_plugins`.
"""
import re
import time
from decimal import Decimal, InvalidOperation

from src.pages.trade_page import TradePage

BUY, SELL = "Buy", "Sell"
STOP_LOSS, TAKE_PROFIT = "Stop Loss", "Take Profit"

# Values the site works out from the live price use a price a few points behind the one shown
# (and not always the same one), so they may be off by this many points. Using the other side's
# price (UKOIL's spread is 40 points) still fails.
PRICE_LAG_POINTS = 10
# How long a live-price check keeps re-reading the panel before it fails.
LIVE_CHECK_SECONDS = 5


def number(text: str) -> Decimal | None:
    """A number as the site shows it ("1,009.00", "+/- 0.10", "-336.00"), or None if there is none."""
    try:
        return Decimal(re.sub(r"[^\d.\-]", "", text.replace("+/-", "")))
    except InvalidOperation:
        return None


def entry_price(snap: dict, side: str) -> Decimal:
    """A Buy opens at the Buy price, a Sell at the Sell price."""
    return number(snap["buy"] if side == BUY else snap["sell"])


def close_price(snap: dict, side: str) -> Decimal:
    """A Buy closes (and its Stop Loss / Take Profit trigger) at the Sell price, a Sell at the Buy price."""
    return number(snap["sell"] if side == BUY else snap["buy"])


def point(snap: dict) -> Decimal:
    """From "One point equals: 0.001"."""
    return number(snap["point"].split(":")[-1])


def goes_above(side: str, field: str) -> bool:
    """Whether the field belongs above the price: a Buy's Take Profit, or a Sell's Stop Loss."""
    return (field == TAKE_PROFIT) == (side == BUY)


def price_from_points(snap: dict, side: str, field: str, points: str) -> Decimal:
    """Where the site puts a Stop Loss / Take Profit entered as points: that far from the close price."""
    direction = 1 if goes_above(side, field) else -1
    return close_price(snap, side) + direction * Decimal(points) * point(snap)


def live_check(trade_page: TradePage, mismatch):
    """Re-read the panel until `mismatch(snapshot)` returns None, or fail with its last message.

    Used instead of `expect` for values worked out from the live price: the expected value has
    to be recomputed from the same snapshot every time the price ticks.
    """
    deadline = time.monotonic() + LIVE_CHECK_SECONDS
    while True:
        problem = mismatch(trade_page.order_panel.snapshot())
        if problem is None:
            return
        if time.monotonic() > deadline:
            raise AssertionError(problem)
        trade_page.page.wait_for_timeout(200)
