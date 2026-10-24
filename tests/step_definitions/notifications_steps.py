"""Steps for the notifications panel (bell icon) and its Order Details dialog."""
import re
from collections import Counter

from playwright.sync_api import expect
from pytest_bdd import then, when

from src.models.Order import Order
from src.pages.trade_page import TradePage

CREATED, CLOSED = "Position Created", "Position Closed"


@when("I open the notifications")
def open_notifications(trade_page: TradePage):
    trade_page.notifications.open()
    expect(trade_page.notifications.panel).to_be_visible()


@then('I should see a "Position Created" notification for my position')
def created_notification(trade_page: TradePage, order: Order):
    items = trade_page.notifications.items_for(order.order_id, CREATED)
    expect(items).to_have_count(1)
    expect(items).to_contain_text(order.side.upper())
    expect(items).to_contain_text(f"{order.volume} volume(s)")
    expect(items).to_contain_text(order.entry_price)


@then('I should see a "Position Closed" notification for each close of my position')
def closed_notifications(trade_page: TradePage, order: Order):
    items = trade_page.notifications.items_for(order.order_id, CLOSED)
    expect(items).to_have_count(len(order.closes))
    # Volume and P/L ("-4.40"; a gain may carry a "+"). Not the close price: the notification's can
    # differ from the fill's by a few points (docs/findings.md #20). Two closes may look the same.
    for (volume, profit), times in Counter((c.volume, c.profit) for c in order.closes).items():
        match = items.filter(has_text=f"{volume} volume(s)").filter(has_text=re.compile(rf"\+?{re.escape(profit)}"))
        expect(match).to_have_count(times)


@when('I open the latest "Position Closed" notification for my position')
def open_latest_close(trade_page: TradePage, order: Order):
    notifications = trade_page.notifications
    notifications.open_details(notifications.items_for(order.order_id, CLOSED).first)
    expect(notifications.details).to_be_visible()


@then("its details should match my position and that close")
def details_match(trade_page: TradePage, order: Order):
    notifications, close = trade_page.notifications, order.closes[-1]
    expect(notifications.details).to_contain_text(CLOSED)
    expect(notifications.details_value("Order No.")).to_have_text(order.order_id)
    expect(notifications.details_value("Volume")).to_have_text(close.volume)
    expect(notifications.details_value("Entry Price")).to_have_text(order.entry_price)
    # Close Price isn't compared: it can differ from the fill's by a few points (docs/findings.md #20).
    expect(notifications.details_value("Stop Loss")).to_have_text(order.stop_loss)
    expect(notifications.details_value("Take Profit")).to_have_text(order.take_profit)
    expect(notifications.details_value("Profit/Loss")).to_have_text(re.compile(rf"^\+?{re.escape(close.profit)}$"))


@then("the notifications should not say there are none")
def notifications_not_empty(trade_page: TradePage):
    expect(trade_page.notifications.empty).to_be_hidden()
