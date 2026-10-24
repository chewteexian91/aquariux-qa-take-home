@one_click @trading
Feature: Market orders with one-click trading
  As a trader
  I want to buy and sell with a single click
  So that my order goes in at once, without a confirmation step

  # One-click trading is saved on the server for the whole account. Scenarios that switch it on
  # switch it back off afterwards.
  # Failed requests are faked in the browser: they never reach the server. A "400 answer" carries
  # the message "Rejected for this test." in the API's error format.
  # @defect scenarios check what the site should do. They are expected to fail until it's fixed.
  # Steps to reproduce each defect by hand: docs/defects.md.

  Background:
    Given one-click trading is off

  # --- Switching it on and off ---

  Scenario: Turn on one-click trading
    Given I am logged in as the "normal" user
    When I turn on one-click trading
    And I agree to the one-click trading terms
    Then I should see the message "One-Click Trading activated."
    And one-click trading should be on

  Scenario: Declining the terms leaves one-click trading off
    Given I am logged in as the "normal" user
    When I turn on one-click trading
    And I decline the one-click trading terms
    Then one-click trading should be off

  Scenario: Turn off one-click trading
    Given one-click trading is on
    And I am logged in as the "normal" user
    And "UKOIL" is open for trading
    When I turn off one-click trading
    Then one-click trading should be off
    When I fill in a "Buy" market order for "0.1" lots with "Fill or Kill"
    And I place the order
    Then the order confirmation should show my order

  # --- Placing orders ---

  Scenario Outline: <side> <symbol> from the One-Click tab, with no confirmation
    Given one-click trading is on
    And I am logged in as the "normal" user
    And "<symbol>" is open for trading
    When I open the One-Click tab
    And I place a "<side>" order for "<volume>" lots with one click
    Then no order confirmation should have opened
    And I should see the message "Position has been created."
    And my position should be listed in Open Positions as ordered

    @smoke
    Examples:
      | symbol | side | volume |
      | UKOIL  | Buy  | 0.1    |

    Examples:
      | symbol | side | volume |
      | UKOIL  | Sell | 0.1    |
      | EURUSD | Buy  | 0.01   |
      | EURUSD | Sell | 0.01   |

  # While one-click trading is on, the order panel opens on the One-Click tab.
  Scenario: The Trade tab places orders without a confirmation while one-click trading is on
    Given one-click trading is on
    And I am logged in as the "normal" user
    And "UKOIL" is open for trading
    When I open the Trade tab
    And I fill in a "Buy" market order for "0.1" lots with "Fill or Kill"
    And I set the Stop Loss price "30%" from the market
    And I set the Take Profit price "20%" from the market
    And I place the order with one-click trading on
    Then no order confirmation should have opened
    And I should see the message "Position has been created."
    And my position should be listed in Open Positions as ordered

  # --- Volume ---

  Scenario Outline: A one-click volume of "<volume>" is rejected and nothing is sent
    Given one-click trading is on
    And I am logged in as the "normal" user
    And "UKOIL" is open for trading
    When I open the One-Click tab
    And I enter "<volume>" lots on the One-Click tab
    And I try to buy with one click
    Then I should see the "Volume" error "<error>"
    And no order should have been sent

    Examples:
      | volume | error                        |
      | 0      | Please enter a valid volume. |
      | 0.0001 | Minimum volume is 0.1.       |
      |        | Please enter a valid volume. |

  # UKOIL's maximum is 100 lots. Anything above is changed to 100 without a message (docs/findings.md #18).
  Scenario Outline: A one-click volume of <volume> lots, at or above the maximum, reads <shown>
    Given one-click trading is on
    And I am logged in as the "normal" user
    And "UKOIL" is open for trading
    When I open the One-Click tab
    And I enter "<volume>" lots on the One-Click tab
    Then the volume should read "<shown>"
    And I should not see a "Volume" error

    Examples:
      | volume | shown |
      | 100    | 100   |
      | 100.1  | 100   |

  # --- Failed requests ---

  Scenario Outline: A one-click order that fails with a <failure> shows "<banner>"
    Given one-click trading is on
    And I am logged in as the "normal" user
    And "UKOIL" is open for trading
    And the "place market order" request will fail with a "<failure>"
    When I open the One-Click tab
    And I enter "0.1" lots on the One-Click tab
    And I try to buy with one click
    Then I should see the message "<banner>"

    Examples:
      | failure       | banner                                                 |
      | 400 answer    | Rejected for this test.                                |
      | 500 answer    | Something went wrong. Please contact customer support. |
      | network error | Network error. Please try again later.                 |
      | timeout       | Network error. Please try again later.                 |

  # Defect #12: if saving the setting fails, the switch stays as it was and nothing tells the user. The right wording isn't known, so any error message passes.
  @defect
  Scenario: Turning on one-click trading tells me when it fails
    Given I am logged in as the "normal" user
    And the "one-click setting" request will fail with a "500 answer"
    When I turn on one-click trading
    And I agree to the one-click trading terms
    Then I should see an error message
    And one-click trading should be off

  @defect
  Scenario: Turning off one-click trading tells me when it fails
    Given one-click trading is on
    And I am logged in as the "normal" user
    And the "one-click setting" request will fail with a "500 answer"
    When I turn off one-click trading
    Then I should see an error message
    And one-click trading should be on
