@bulk_actions @trading
Feature: Bulk close and bulk delete
  As a trader
  I want to close positions or delete pending orders in one go, by kind
  So that I can get out of the market or clear my orders quickly

  # Supported orders: Bulk Close takes All / Profitable / Loss positions, Bulk Delete All / Limit /
  # Stop / Stop Limit orders, at most 30 at a time, only those the server marks closable. With
  # "Hide Other Symbols" on, only the open symbol's. "Profitable Positions" isn't tested here: it
  # needs the market to move past the spread first (docs/findings.md, "Not covered yet").
  # Bulk actions hit every order on the account, not just the scenario's, so each scenario first
  # checks the account holds nothing else, and skips if it does.
  # Orders are created through the API before logging in.
  # Failed requests are mocked in the browser: they never reach the server.
  # @defect scenarios check what the site should do. They are expected to fail until it's fixed.
  # Steps to reproduce each defect by hand: docs/defects.md.

  Background:
    Given one-click trading is off
    And the account has no other open positions or pending orders

  # --- Bulk close ---

  @smoke
  Scenario: Close all positions
    Given I have a "Buy" position of "0.1" lots on "UKOIL"
    And I have a "Sell" position of "0.1" lots on "UKOIL"
    And I have a "Buy" position of "0.01" lots on "EURUSD"
    And I am logged in as the "normal" user
    When I bulk close "All Positions"
    Then the bulk dialog should say "Up to 30 positions can be closed."
    And the bulk dialog should say "Would you like to close all positions?"
    When I confirm the bulk action
    Then I should see the message "All positions have been closed."
    And all my positions should be closed

  # A Buy and a Sell on the same symbol can't both be in profit: at least one is at a loss.
  Scenario: Close the positions at a loss
    Given I have a "Buy" position of "0.1" lots on "UKOIL"
    And I have a "Sell" position of "0.1" lots on "UKOIL"
    And I am logged in as the "normal" user
    When I bulk close "Loss Positions"
    Then the bulk dialog should say "Up to 30 open losing positions can be closed."
    And the bulk dialog should say "Would you like to close all losing positions?"
    When I confirm the bulk action, noting which positions are at a loss
    Then I should see the message "All losing positions have been closed."
    And my positions that were at a loss should be closed, and any others still open

  Scenario: Cancelling a bulk close keeps the positions
    Given I have a "Buy" position of "0.1" lots on "UKOIL"
    And I have a "Sell" position of "0.1" lots on "UKOIL"
    And I am logged in as the "normal" user
    When I bulk close "All Positions"
    And I cancel the bulk action
    Then my positions should all still be open

  Scenario: With Hide Other Symbols on, bulk close only closes the open symbol's positions
    Given I have a "Buy" position of "0.1" lots on "UKOIL"
    And I have a "Buy" position of "0.01" lots on "EURUSD"
    And I am logged in as the "normal" user
    And "UKOIL" is open for trading
    When I tick Hide Other Symbols
    And I bulk close "All Positions"
    And I confirm the bulk action
    Then I should see the message "All positions have been closed."
    And only my "UKOIL" positions should be closed

  Scenario Outline: Bulk close acts on at most 30 positions (<count> open)
    Given I have <count> "Buy" positions of "0.1" lots on "UKOIL"
    And I am logged in as the "normal" user
    When I bulk close "All Positions"
    And I confirm the bulk action
    Then <closed> of my positions should be closed and <left> still open

    Examples:
      | count | closed | left |
      | 30    | 30     | 0    |
      | 31    | 30     | 1    |

  # Defect #15: with 31 positions, 30 are closed and the message still says "All positions have been
  # closed." The app has a "{n} positions have been closed." message, which the expected text below
  # assumes.
  @defect
  Scenario: When some positions are left over, the message says how many were closed
    Given I have 31 "Buy" positions of "0.1" lots on "UKOIL"
    And I am logged in as the "normal" user
    When I bulk close "All Positions"
    And I confirm the bulk action
    Then I should see the message "30 positions have been closed."

  Scenario Outline: A bulk close that fails with a <failure> closes nothing
    Given I have a "Buy" position of "0.1" lots on "UKOIL"
    And I have a "Sell" position of "0.1" lots on "UKOIL"
    And I am logged in as the "normal" user
    And the "bulk close" request is mocked to fail with a "<failure>"
    When I bulk close "All Positions"
    And I confirm the bulk action
    Then I should see the message "Order action failed"
    And my positions should all still be open

    Examples:
      | failure       |
      | 400 answer    |
      | 500 answer    |
      | network error |

  # --- Bulk delete ---

  Scenario Outline: Delete "<option>"
    Given I have one pending order of each type on "UKOIL"
    And I am logged in as the "normal" user
    When I bulk delete "<option>"
    Then the bulk dialog should say "<limit>"
    And the bulk dialog should say "<question>"
    When I confirm the bulk action
    Then I should see the message "<message>"
    And only my "<option>" should be deleted

    Examples:
      | option            | limit                                      | question                                        | message                                  |
      | All Orders        | Up to 30 pending orders can be deleted.    | Would you like to delete all pending orders?    | All pending orders have been deleted.    |
      | Limit Orders      | Up to 30 limit orders can be deleted.      | Would you like to delete all limit orders?      | All limit orders have been deleted.      |
      | Stop Orders       | Up to 30 stop orders can be deleted.       | Would you like to delete all stop orders?       | All stop orders have been deleted.       |
      | Stop Limit Orders | Up to 30 stop limit orders can be deleted. | Would you like to delete all stop limit orders? | All stop limit orders have been deleted. |

  Scenario: Cancelling a bulk delete keeps the orders
    Given I have one pending order of each type on "UKOIL"
    And I am logged in as the "normal" user
    When I bulk delete "All Orders"
    And I cancel the bulk action
    Then my pending orders should all still be pending

  Scenario: Kinds with no pending orders can't be chosen
    Given I have a "Buy" "Limit" order of "0.1" lots on "UKOIL"
    And I am logged in as the "normal" user
    When I open Pending Orders
    Then my order should still be pending
    And the "Limit Orders" option should be selectable
    And the "Stop Orders" option should not be selectable
    And the "Stop Limit Orders" option should not be selectable

  Scenario: With Hide Other Symbols on, bulk delete only deletes the open symbol's orders
    Given I have a "Buy" "Limit" order of "0.1" lots on "UKOIL"
    And I have a "Buy" "Limit" order of "0.01" lots on "EURUSD"
    And I am logged in as the "normal" user
    And "UKOIL" is open for trading
    When I tick Hide Other Symbols
    And I bulk delete "All Orders"
    And I confirm the bulk action
    Then I should see the message "All pending orders have been deleted."
    And only my "UKOIL" pending orders should be deleted

  Scenario Outline: Bulk delete acts on at most 30 orders (<count> pending)
    Given I have <count> "Buy" "Limit" orders of "0.1" lots on "UKOIL"
    And I am logged in as the "normal" user
    When I bulk delete "All Orders"
    And I confirm the bulk action
    Then <deleted> of my pending orders should be deleted and <left> still pending

    Examples:
      | count | deleted | left |
      | 30    | 30      | 0    |
      | 31    | 30      | 1    |

  Scenario Outline: A bulk delete that fails with a <failure> deletes nothing
    Given I have a "Buy" "Limit" order of "0.1" lots on "UKOIL"
    And I have a "Sell" "Stop" order of "0.1" lots on "UKOIL"
    And I am logged in as the "normal" user
    And the "bulk delete" request is mocked to fail with a "<failure>"
    When I bulk delete "All Orders"
    And I confirm the bulk action
    Then I should see the message "Order action failed"
    And my pending orders should all still be pending

    Examples:
      | failure       |
      | 400 answer    |
      | 500 answer    |
      | network error |
