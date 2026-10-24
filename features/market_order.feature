@market_order @trading
Feature: Market orders with Stop Loss and Take Profit
  As a trader
  I want to place Buy and Sell market orders with a Stop Loss and Take Profit
  So that my position opens at the market price with its exits already set

  # UKOIL (Commodities) offers Fill or Kill and Immediate or Cancel. EURUSD (Forex) only Fill or Kill.
  # "from the market" = on the correct side: a Buy has its Stop Loss below and Take Profit above
  # the price, a Sell the reverse. They sit 20-30% away so they never trigger while a test runs.
  # Failed order requests are mocked in the browser: they never reach the server.
  # @defect scenarios check what the site should do. They are expected to fail until it's fixed.
  # Steps to reproduce each defect by hand: docs/defects.md.

  Background:
    Given one-click trading is off
    And I am logged in as the "normal" user

  # --- Placing orders ---

  Scenario Outline: Place a <side> market order on <symbol> with Stop Loss and Take Profit (<fill_policy>)
    Given "<symbol>" is open for trading
    When I fill in a "<side>" market order for "<volume>" lots with "<fill_policy>"
    And I set the Stop Loss price "30%" from the market
    And I set the Take Profit price "20%" from the market
    And I place the order
    Then the order confirmation should show my order
    When I confirm the order
    Then I should see the message "Position has been created."
    And my position should be listed in Open Positions as ordered

    @smoke
    Examples:
      | symbol | side | volume | fill_policy         |
      | UKOIL  | Buy  | 0.1    | Fill or Kill        |

    Examples:
      | symbol | side | volume | fill_policy         |
      | UKOIL  | Sell | 0.1    | Fill or Kill        |
      | UKOIL  | Buy  | 0.1    | Immediate or Cancel |
      | UKOIL  | Sell | 0.1    | Immediate or Cancel |
      | EURUSD | Buy  | 0.01   | Fill or Kill        |
      | EURUSD | Sell | 0.01   | Fill or Kill        |

  Scenario Outline: <side> market order with Stop Loss and Take Profit entered in points
    Given "UKOIL" is open for trading
    When I fill in a "<side>" market order for "0.1" lots with "Fill or Kill"
    And I set the Stop Loss "30%" from the market in points
    And I set the Take Profit "20%" from the market in points
    Then the Stop Loss and Take Profit prices should be worked out from the points
    When I place the order
    Then the order confirmation should show my order
    When I confirm the order
    Then I should see the message "Position has been created."
    And my position should be listed in Open Positions as ordered

    Examples:
      | side |
      | Buy  |
      | Sell |

  Scenario: Market order with only a Stop Loss
    Given "UKOIL" is open for trading
    When I fill in a "Buy" market order for "0.1" lots with "Fill or Kill"
    And I set the Stop Loss price "30%" from the market
    And I place the order
    Then the order confirmation should show my order
    When I confirm the order
    Then I should see the message "Position has been created."
    And my position should be listed in Open Positions as ordered

  Scenario: Market order with only a Take Profit
    Given "UKOIL" is open for trading
    When I fill in a "Buy" market order for "0.1" lots with "Fill or Kill"
    And I set the Take Profit price "20%" from the market
    And I place the order
    Then the order confirmation should show my order
    When I confirm the order
    Then I should see the message "Position has been created."
    And my position should be listed in Open Positions as ordered

  Scenario: Market order with no Stop Loss or Take Profit
    Given "UKOIL" is open for trading
    When I fill in a "Buy" market order for "0.1" lots with "Fill or Kill"
    And I place the order
    Then the order confirmation should show my order
    When I confirm the order
    Then I should see the message "Position has been created."
    And my position should be listed in Open Positions as ordered

  Scenario Outline: <symbol> market orders offer <fill_policies>
    Given "<symbol>" is open for trading
    When I open the fill policy list
    Then the fill policies offered should be "<fill_policies>"

    Examples:
      | symbol | fill_policies                     |
      | UKOIL  | Fill or Kill, Immediate or Cancel |
      | EURUSD | Fill or Kill                      |

  # Defect #4: USDSGD orders are rejected with "Insufficient balance". The site works out a margin
  # of 1,277,800.00 USD for 0.01 lot (1,000 USD), more than the account holds. At 1:100 it is 10.00.
  @defect
  Scenario: A USDSGD market order goes through
    Given "USDSGD" is open for trading
    When I fill in a "Buy" market order for "0.01" lots with "Fill or Kill"
    And I place the order
    And I confirm the order
    Then I should see the message "Position has been created."
    And my position should be listed in Open Positions as ordered

  # --- Validation and boundaries ---

  Scenario Outline: A volume of <volume> is rejected
    Given "UKOIL" is open for trading
    When I enter a volume of "<volume>"
    Then I should see the "Volume" error "<error>"
    And I should not be able to place the order

    Examples:
      | volume | error                        |
      | 0      | Please enter a valid volume. |
      | 0.0001 | Minimum volume is 0.1.       |

  Scenario Outline: A <side> order rejects a <field> on the wrong side of the market
    Given "UKOIL" is open for trading
    When I fill in a "<side>" market order for "0.1" lots with "Fill or Kill"
    And I set the "<field>" price "30%" on the wrong side of the market
    Then I should see the "<field>" error "<error>"
    And I should not be able to place the order

    Examples:
      | side | field       | error                                        |
      | Buy  | Stop Loss   | Stop Loss must be less than Sell Price.      |
      | Buy  | Take Profit | Take Profit must be greater than Sell Price. |
      | Sell | Stop Loss   | Stop Loss must be greater than Buy Price.    |
      | Sell | Take Profit | Take Profit must be less than Buy Price.     |

  Scenario Outline: A <side> order rejects a <field> price of 0.000
    Given "UKOIL" is open for trading
    When I fill in a "<side>" market order for "0.1" lots with "Fill or Kill"
    And I set the "<field>" price to "0.000"
    Then I should see the "<field>" error "<error>"
    And I should not be able to place the order

    Examples:
      | side | field       | error                                        |
      | Sell | Stop Loss   | Stop Loss must be greater than Buy Price.    |
      | Buy  | Take Profit | Take Profit must be greater than Sell Price. |

  # Defect #1: a price of 0 means "no Stop Loss / Take Profit". The site accepts it here, shows
  # "0.000" in the confirmation and opens the position with no Stop Loss / Take Profit ("--"),
  # without telling the user.
  @defect
  Scenario Outline: A <side> order rejects a <field> price of <price>, which becomes 0.000
    Given "UKOIL" is open for trading
    When I fill in a "<side>" market order for "0.1" lots with "Fill or Kill"
    And I set the "<field>" price to "<price>"
    Then I should see a "<field>" error
    And I should not be able to place the order

    Examples:
      | side | field       | price      |
      | Sell | Take Profit | 0.00000001 |
      | Sell | Take Profit | 0.000      |
      | Buy  | Stop Loss   | 0.00000001 |
      | Buy  | Stop Loss   | 0.000      |

  # --- Trade Details ---
  # Entry price = the Buy price for a Buy, the Sell price for a Sell. The account's leverage is 1:100.

  Scenario Outline: Trade Details work out a <side> order on UKOIL
    Given "UKOIL" is open for trading
    When I fill in a "<side>" market order for "0.2" lots with "Fill or Kill"
    And I set the Stop Loss price "30%" from the market
    And I set the Take Profit price "20%" from the market
    And I open the Trade Details
    Then the Trade Volume should be the units times the entry price
    And the Est. Margin Required should be the Trade Volume at 1:100 leverage
    And the Amount Per Tick should be the units times one point
    And the Potential Loss should be what the Stop Loss would lose
    And the Potential Gain should be what the Take Profit would gain
    And the Risk:Reward should be the gain over the loss

    Examples:
      | side |
      | Buy  |
      | Sell |

  Scenario: Trade Details without Stop Loss or Take Profit show no loss, gain or ratio
    Given "UKOIL" is open for trading
    When I fill in a "Buy" market order for "0.2" lots with "Fill or Kill"
    And I open the Trade Details
    Then the Trade Details should show "Potential Loss" "0.00"
    And the Trade Details should show "Potential Gain" "0.00"
    And the Trade Details should show "Risk:Reward" ""

  # Defects #4 and #5: 0.01 lot of USDSGD is 1,000 USD (the base currency). The site shows the SGD value
  # (about 1,277.80) under "Trade Details (USD)", and a margin of 1,277,800.00.
  @defect
  Scenario Outline: USDSGD Trade Details show the <detail> in USD
    Given "USDSGD" is open for trading
    When I fill in a "Buy" market order for "0.01" lots with "Fill or Kill"
    And I open the Trade Details
    Then the Trade Details should show "<detail>" "<usd>"

    Examples:
      | detail               | usd      |
      | Trade Volume         | 1,000.00 |
      | Est. Margin Required | 10.00    |

  # --- Failed order requests ---
  # A JSON error answer uses the API's error format: {"code": "<status>", "message": "<message>"}.

  Scenario Outline: An order the server answers with <status> shows "<banner>"
    Given "UKOIL" is open for trading
    When I fill in a "Buy" market order for "0.1" lots with "Fill or Kill"
    And I place the order
    And I confirm the order, with its request mocked to answer <status> with "<message>"
    Then I should see the message "<banner>"

    Examples:
      | status | message               | banner                                                 |
      | 400    | Insufficient margin.  | Insufficient margin.                                   |
      | 403    | Trading is disabled.  | Trading is disabled.                                   |
      | 500    | Internal Server Error | Something went wrong. Please contact customer support. |

  Scenario Outline: An order request that fails with a <failure> shows "<banner>"
    Given "UKOIL" is open for trading
    When I fill in a "Buy" market order for "0.1" lots with "Fill or Kill"
    And I place the order
    And I confirm the order, with its request mocked to fail with a "<failure>"
    Then I should see the message "<banner>"

    Examples:
      | failure         | banner                                 |
      | network error   | Network error. Please try again later. |
      | blocked request | Network error. Please try again later. |
      | timeout         | Network error. Please try again later. |

  # Defect #6: a gateway's 502/503 page shows the raw request path to the user
  # ("/api/trade/trade/v1/market POST (503 - Service Unavailable)").
  @defect
  Scenario Outline: An order request that fails with a <failure> tells the user
    Given "UKOIL" is open for trading
    When I fill in a "Buy" market order for "0.1" lots with "Fill or Kill"
    And I place the order
    And I confirm the order, with its request mocked to fail with a "<failure>"
    Then I should see the message "<banner>"

    Examples:
      | failure          | banner                                                 |
      | 502 gateway page | Something went wrong. Please contact customer support. |
      | 503 gateway page | Something went wrong. Please contact customer support. |
