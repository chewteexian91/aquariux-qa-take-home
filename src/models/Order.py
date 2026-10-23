from dataclasses import dataclass


@dataclass
class Order:
    """An order a test created, so later steps can find it and compare against it."""

    symbol: str
    side: str  # "Buy" or "Sell"
    volume: str  # lots, as written in the feature file
    order_id: str | None = None  # the Order No.; None until the order is placed
    fill_policy: str | None = None  # "Fill or Kill" / "Immediate or Cancel", as the site shows it
    stop_loss: str | None = None  # price, as the site shows it (e.g. "77.123"); None when not set
    take_profit: str | None = None
    # Set when the Stop Loss / Take Profit was entered as a distance in points. The site then moves
    # the price with the market until the order is placed, so the price is only known from there on.
    stop_loss_points: str | None = None
    take_profit_points: str | None = None
