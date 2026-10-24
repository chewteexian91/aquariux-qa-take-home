"""Prices for orders created through the API, before the browser shows any live price.

Not a step file. They sit far from the market (UKOIL ~112, EURUSD ~1.12 on 2026-10-23), so nothing
fills or triggers while a test runs, and they're written the way the site shows them (UKOIL 3
decimals, EURUSD 4).
"""

# Stop Loss / Take Profit for a position, by symbol and side: (stop loss, take profit).
POSITION_SL_TP = {
    "UKOIL": {"Buy": ("60.000", "180.000"), "Sell": ("180.000", "60.000")},
}
# A second, still valid pair, for scenarios that change them.
NEW_POSITION_SL_TP = {
    "UKOIL": {"Buy": ("65.000", "175.000"), "Sell": ("175.000", "65.000")},
}

# Pending orders by symbol and (side, type): (price, stop limit price or None).
PENDING_PRICES = {
    "UKOIL": {
        ("Buy", "Limit"): ("80.000", None), ("Sell", "Limit"): ("150.000", None),
        ("Buy", "Stop"): ("150.000", None), ("Sell", "Stop"): ("80.000", None),
        # A Buy Stop Limit's Stop Limit Price sits below its Price, a Sell's above.
        ("Buy", "Stop Limit"): ("150.000", "149.000"), ("Sell", "Stop Limit"): ("80.000", "81.000"),
    },
    "EURUSD": {
        ("Buy", "Limit"): ("0.9000", None), ("Sell", "Limit"): ("1.4000", None),
        ("Buy", "Stop"): ("1.4000", None), ("Sell", "Stop"): ("0.9000", None),
        ("Buy", "Stop Limit"): ("1.4000", "1.3990"), ("Sell", "Stop Limit"): ("0.9000", "0.9010"),
    },
}
# What an edited Buy Limit on UKOIL changes to: price, stop loss, take profit (all still valid).
EDITED_BUY_LIMIT = ("79.000", "70.000", "90.000")

# Units in one lot ("Contract Size" on the symbol's Specification tab).
CONTRACT_SIZE = {"UKOIL": 1000, "EURUSD": 100_000}
# Decimals the site shows prices with.
DECIMALS = {"UKOIL": 3, "EURUSD": 4}


def price_text(symbol: str, value: float) -> str:
    return f"{value:.{DECIMALS[symbol]}f}"
