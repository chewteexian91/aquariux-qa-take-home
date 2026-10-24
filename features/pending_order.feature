@pending_order @trading
Feature: Pending orders
  As a trader
  I want to place, change and delete Limit, Stop and Stop Limit orders with an expiry
  So that I can trade at a price I choose, for as long as I choose

  # Supported: Limit, Stop and Stop Limit orders, each with the expiry Good Till Canceled, Good Till
  # Day, Specified Date or Specified Date and Time (dates on the server's clock, UTC+3).
  # Prices are set relative to the market ("-20%" = 20% below the side's market price), far enough
  # that the orders never fill while a test runs. Orders to change or delete are placed through the
  # API first; placing itself is checked through the UI.
  # Failed requests are mocked in the browser: they never reach the server. A "400 answer" carries
  # the message "Rejected for this test." in the API's error format.
  # @defect scenarios check what the site should do. They are expected to fail until it's fixed.
  # Steps to reproduce each defect by hand: docs/defects.md.

  Background:
    Given one-click trading is off

  # --- Placing ---

  Scenario Outline: Place a <side> <type> order
    Given I am logged in as the "normal" user
    And "UKOIL" is open for trading
    When I fill in a "<side>" "<type>" order for "0.1" lots priced "<price>" from the market
    And I place the order
    Then the order confirmation should show my order
    When I confirm the order
    Then I should see the message "Order has been created."
    And my order should be listed in Pending Orders as ordered

    @smoke
    Examples:
      | side | type  | price |
      | Buy  | Limit | -20%  |

    Examples:
      | side | type  | price |
      | Sell | Limit | +20%  |
      | Buy  | Stop  | +20%  |
      | Sell | Stop  | -20%  |

  # A Buy Stop Limit's Stop Limit Price sits below its Price, a Sell's above.
  Scenario Outline: Place a <side> Stop Limit order
    Given I am logged in as the "normal" user
    And "UKOIL" is open for trading
    When I fill in a "<side>" "Stop Limit" order for "0.1" lots priced "<price>" from the market
    And I set the Stop Limit Price "<stop_limit_price>" from the market
    And I place the order
    Then the order confirmation should show my order
    When I confirm the order
    Then I should see the message "Order has been created."
    And my order should be listed in Pending Orders as ordered

    Examples:
      | side | price | stop_limit_price |
      | Buy  | +20%  | +19%             |
      | Sell | -20%  | -19%             |

  Scenario: Place an order that is good till the end of the day
    Given I am logged in as the "normal" user
    And "UKOIL" is open for trading
    When I fill in a "Buy" "Limit" order for "0.1" lots priced "-20%" from the market
    And I choose the expiry "Good Till Day"
    And I place the order
    Then the order confirmation should show my order
    When I confirm the order
    Then I should see the message "Order has been created."
    And my order should be listed in Pending Orders as ordered

  Scenario Outline: Place an order with the expiry "<expiry>"
    Given I am logged in as the "normal" user
    And "UKOIL" is open for trading
    When I fill in a "Buy" "Limit" order for "0.1" lots priced "-20%" from the market
    And I choose the expiry "<expiry>"
    And I pick an expiry date 3 days ahead
    And I place the order
    Then the order confirmation should show my order
    When I confirm the order
    Then I should see the message "Order has been created."
    And my order should be listed in Pending Orders as ordered

    Examples:
      | expiry                  |
      | Specified Date          |
      | Specified Date and Time |

  Scenario: Place an order with a Stop Loss and Take Profit
    Given I am logged in as the "normal" user
    And "UKOIL" is open for trading
    When I fill in a "Buy" "Limit" order for "0.1" lots priced "-20%" from the market
    And I set the Stop Loss price "30%" from the market
    And I set the Take Profit price "20%" from the market
    And I place the order
    Then the order confirmation should show my order
    When I confirm the order
    Then I should see the message "Order has been created."
    And my order should be listed in Pending Orders as ordered

  Scenario Outline: <symbol> offers the pending order types and expiry options
    Given I am logged in as the "normal" user
    And "<symbol>" is open for trading
    When I open the order type list
    Then the order types offered should be "Market, Limit, Stop, Stop Limit"
    When I choose a "Limit" order
    And I open the expiry list
    Then the expiry options offered should be "Good Till Canceled, Good Till Day, Specified Date and Time, Specified Date"

    Examples:
      | symbol |
      | UKOIL  |
      | EURUSD |

  # --- Checks in the form ---

  Scenario Outline: A <side> Limit order rejects a <field> on the wrong side of its price
    Given I am logged in as the "normal" user
    And "UKOIL" is open for trading
    When I fill in a "<side>" "Limit" order for "0.1" lots priced "<price>" from the market
    And I set the "<field>" price "5%" on the wrong side of my order's price
    Then I should see the "<field>" error "<error>"
    And I should not be able to place the order

    Examples:
      | side | price | field       | error                                   |
      | Buy  | -20%  | Stop Loss   | Stop Loss must be less than price.      |
      | Buy  | -20%  | Take Profit | Take Profit must be greater than price. |
      | Sell | +20%  | Stop Loss   | Stop Loss must be greater than price.   |
      | Sell | +20%  | Take Profit | Take Profit must be less than price.    |

  Scenario: A pending order needs a price
    Given I am logged in as the "normal" user
    And "UKOIL" is open for trading
    When I fill in a "Buy" "Limit" order for "0.1" lots priced "-20%" from the market
    And I clear the price
    Then I should see the "Price" error "Please enter a valid price."
    And I should not be able to place the order

  Scenario Outline: A pending order rejects a volume of <volume>
    Given I am logged in as the "normal" user
    And "UKOIL" is open for trading
    When I fill in a "Buy" "Limit" order for "0.1" lots priced "-20%" from the market
    And I enter a volume of "<volume>"
    Then I should see the "Volume" error "<error>"
    And I should not be able to place the order

    Examples:
      | volume | error                        |
      | 0      | Please enter a valid volume. |
      | 0.0001 | Minimum volume is 0.1.       |

  # The date box starts at today, but today can't be picked: Good Till Day covers it.
  Scenario: Only days from tomorrow can be picked as the expiry date
    Given I am logged in as the "normal" user
    And "UKOIL" is open for trading
    When I fill in a "Buy" "Limit" order for "0.1" lots priced "-20%" from the market
    And I choose the expiry "Specified Date"
    And I open the expiry calendar
    Then only days from tomorrow should be selectable as the expiry date

  # Defect #9: the form doesn't check a pending order's price against the market. The order reaches
  # the confirmation and the server turns it down with "Metatrader Invalid Price".
  @defect
  Scenario Outline: A <side> <type> order priced on the wrong side of the market is stopped in the form
    Given I am logged in as the "normal" user
    And "UKOIL" is open for trading
    When I fill in a "<side>" "<type>" order for "0.1" lots priced "<price>" from the market
    Then I should see a "Price" error
    And I should not be able to place the order

    Examples:
      | side | type  | price |
      | Buy  | Limit | +20%  |
      | Sell | Limit | -20%  |
      | Buy  | Stop  | -20%  |
      | Sell | Stop  | +20%  |

  # Defect #10: a Stop Limit Price on the wrong side of the Price isn't checked in the form; the
  # server answers "Invalid price" after Confirm.
  @defect
  Scenario Outline: A <side> Stop Limit order with the Stop Limit Price on the wrong side is stopped in the form
    Given I am logged in as the "normal" user
    And "UKOIL" is open for trading
    When I fill in a "<side>" "Stop Limit" order for "0.1" lots priced "<price>" from the market
    And I set the Stop Limit Price "<stop_limit_price>" from the market
    Then I should see a "Stop Limit Price" error
    And I should not be able to place the order

    Examples:
      | side | price | stop_limit_price |
      | Buy  | +20%  | +21%             |
      | Sell | -20%  | -21%             |

  # Defect #11: past hours aren't blocked in the time picker, and the form doesn't object to an expiry
  # time that has passed. Only the server rejects it, after Confirm.
  @defect
  Scenario: An expiry time that has already passed today is stopped in the form
    Given I am logged in as the "normal" user
    And "UKOIL" is open for trading
    When I fill in a "Buy" "Limit" order for "0.1" lots priced "-20%" from the market
    And I choose the expiry "Specified Date and Time"
    And I set the expiry hour to one that has already passed today
    Then I should not be able to place the order

  # --- Changing and deleting ---

  Scenario: Change a pending order's price, Stop Loss, Take Profit and expiry
    Given I have a "Buy" "Limit" order of "0.1" lots on "UKOIL"
    And I am logged in as the "normal" user
    When I open Pending Orders
    And I change my order's price, Stop Loss, Take Profit and expiry
    Then the order confirmation should show my changed order
    When I confirm the change
    Then I should see the message "Order has been updated."
    And my order should be listed in Pending Orders as ordered

  Scenario Outline: Changing a Buy Limit order rejects a <field> on the wrong side of its price
    Given I have a "Buy" "Limit" order of "0.1" lots on "UKOIL"
    And I am logged in as the "normal" user
    When I open Pending Orders
    And I set my order's "<field>" price "5%" on the wrong side of its price
    Then I should see the edit "<field>" error "<error>"
    And I should not be able to update

    Examples:
      | field       | error                                   |
      | Stop Loss   | Stop Loss must be less than price.      |
      | Take Profit | Take Profit must be greater than price. |

  Scenario: Cancelling a change keeps the order as it was
    Given I have a "Buy" "Limit" order of "0.1" lots on "UKOIL"
    And I am logged in as the "normal" user
    When I open Pending Orders
    And I start changing my order's price to "79.000"
    And I cancel the edit
    Then my order should still show price "80.000"

  Scenario: Delete a pending order
    Given I have a "Buy" "Limit" order of "0.1" lots on "UKOIL"
    And I am logged in as the "normal" user
    When I delete my order
    Then I should see the message "Order has been deleted."
    And my order should no longer be pending

  Scenario: Cancelling a deletion keeps the order
    Given I have a "Buy" "Limit" order of "0.1" lots on "UKOIL"
    And I am logged in as the "normal" user
    When I start deleting my order
    And I cancel the deletion
    Then my order should still be pending

  # --- Failed requests ---

  Scenario Outline: Placing a pending order that fails with a <failure> shows "<banner>"
    Given I am logged in as the "normal" user
    And "UKOIL" is open for trading
    And the "place pending order" request is mocked to fail with a "<failure>"
    When I fill in a "Buy" "Limit" order for "0.1" lots priced "-20%" from the market
    And I place the order
    And I try to confirm the order
    Then I should see the message "<banner>"
    And no pending order should have been created

    Examples:
      | failure       | banner                                                 |
      | 400 answer    | Rejected for this test.                                |
      | 500 answer    | Something went wrong. Please contact customer support. |
      | network error | Network error. Please try again later.                 |

  Scenario Outline: Changing a pending order that fails with a <failure> keeps it as it was
    Given I have a "Buy" "Limit" order of "0.1" lots on "UKOIL"
    And I am logged in as the "normal" user
    And the "modify pending order" request is mocked to fail with a "<failure>"
    When I open Pending Orders
    And I change my order's price to "79.000"
    And I confirm the change
    Then I should see the message "<banner>"
    And my order should still show price "80.000"

    Examples:
      | failure       | banner                                                 |
      | 400 answer    | Rejected for this test.                                |
      | 500 answer    | Something went wrong. Please contact customer support. |
      | network error | Network error. Please try again later.                 |

  Scenario Outline: Deleting a pending order that fails with a <failure> keeps it
    Given I have a "Buy" "Limit" order of "0.1" lots on "UKOIL"
    And I am logged in as the "normal" user
    And the "delete pending order" request is mocked to fail with a "<failure>"
    When I start deleting my order
    And I confirm the deletion
    Then I should see the message "<banner>"
    And my order should still be pending

    Examples:
      | failure       | banner                                                 |
      | 400 answer    | Rejected for this test.                                |
      | 500 answer    | Something went wrong. Please contact customer support. |
      | network error | Network error. Please try again later.                 |
