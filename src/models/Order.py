from dataclasses import dataclass, field


@dataclass
class Close:
    """One close (full or partial) of a position, as the server recorded it."""

    order_id: str  # the closing order's own Order No.
    volume: str  # lots closed, e.g. "0.1"
    price: str  # close price as the site shows it, e.g. "111.957"
    profit: str  # e.g. "-4.40"


@dataclass
class Order:
    """An order a test created, so later steps can find it and compare against it."""

    symbol: str
    side: str  # "Buy" or "Sell"
    volume: str  # lots, as written in the feature file
    order_id: str | None = None  # the Order No.; None until the order is placed
    order_type: str = "Market"  # "Market", "Limit", "Stop" or "Stop Limit"
    fill_policy: str | None = None  # "Fill or Kill" / "Immediate or Cancel" / "Return", as the site shows it
    stop_loss: str | None = None  # price, as the site shows it (e.g. "77.123"); None when not set
    take_profit: str | None = None
    # Set when the Stop Loss / Take Profit was entered as a distance in points. The site then moves
    # the price with the market until the order is placed, so the price is only known from there on.
    stop_loss_points: str | None = None
    take_profit_points: str | None = None
    # Pending orders only
    price: str | None = None  # as the site shows it (e.g. "90.000")
    stop_limit_price: str | None = None
    expiry: str | None = None  # the UI's name, e.g. "Good Till Canceled"
    expiry_date: str | None = None  # as the Pending Orders table shows it, e.g. "2026-10-26"
    # Positions opened through the API
    entry_price: str | None = None  # as the site shows it, e.g. "112.101"
    closes: list[Close] = field(default_factory=list)

    @property
    def type_label(self) -> str:
        """How the tables and the confirmation name the order: BUY, SELL LIMIT, BUY STOP LIMIT…"""
        if self.order_type == "Market":
            return self.side.upper()
        return f"{self.side} {self.order_type}".upper()
