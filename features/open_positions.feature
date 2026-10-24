@open_positions @trading
Feature: Open positions
  As a trader
  I want to see my open positions, change their Stop Loss and Take Profit, and close all or part of them
  So that I can manage a trade after opening it

  # Positions are opened through the API before logging in; the scenarios check the table and dialogs.
  # UKOIL: minimum 0.1 lot, steps of 0.1. Stop Loss / Take Profit sit far from the market.
  # Failed requests are mocked in the browser: they never reach the server. A "400 answer" carries
  # the message "Rejected for this test." in the API's error format.

  Background:
    Given one-click trading is off

  Scenario: View an open position
    Given I have a "Buy" position of "0.2" lots on "UKOIL" with a Stop Loss and Take Profit
    And I am logged in as the "normal" user
    Then my position should be listed with its details

  # --- Stop Loss and Take Profit ---

  Scenario Outline: Change a <side> position's Stop Loss and Take Profit
    Given I have a "<side>" position of "0.1" lots on "UKOIL" with a Stop Loss and Take Profit
    And I am logged in as the "normal" user
    When I change my position's Stop Loss and Take Profit
    Then the order confirmation should show the new Stop Loss and Take Profit
    When I confirm the change
    Then I should see the message "Position has been updated."
    And my position should show its new Stop Loss and Take Profit

    Examples:
      | side |
      | Buy  |
      | Sell |

  Scenario: Remove a position's Stop Loss and Take Profit
    Given I have a "Buy" position of "0.1" lots on "UKOIL" with a Stop Loss and Take Profit
    And I am logged in as the "normal" user
    When I clear my position's Stop Loss and Take Profit
    Then the order confirmation should show the new Stop Loss and Take Profit
    When I confirm the change
    Then I should see the message "Position has been updated."
    And my position should show its new Stop Loss and Take Profit

  Scenario Outline: A <side> position rejects a <field> on the wrong side of the market
    Given I have a "<side>" position of "0.1" lots on "UKOIL" with a Stop Loss and Take Profit
    And I am logged in as the "normal" user
    When I set my position's "<field>" price "30%" on the wrong side of the market
    Then I should see the edit "<field>" error "<error>"
    And I should not be able to update

    Examples:
      | side | field       | error                                        |
      | Buy  | Stop Loss   | Stop Loss must be less than Sell Price.      |
      | Buy  | Take Profit | Take Profit must be greater than Sell Price. |
      | Sell | Stop Loss   | Stop Loss must be greater than Buy Price.    |
      | Sell | Take Profit | Take Profit must be less than Buy Price.     |

  # Unlike the order panel, where 0 quietly means "none" (docs/findings.md #1, #17).
  Scenario Outline: A position rejects a <field> of 0
    Given I have a "Buy" position of "0.1" lots on "UKOIL" with a Stop Loss and Take Profit
    And I am logged in as the "normal" user
    When I set my position's "<field>" price to "0"
    Then I should see the edit "<field>" error "Value must be greater than 0"
    And I should not be able to update

    Examples:
      | field       |
      | Stop Loss   |
      | Take Profit |

  Scenario: Cancelling a change keeps the Stop Loss and Take Profit
    Given I have a "Buy" position of "0.1" lots on "UKOIL" with a Stop Loss and Take Profit
    And I am logged in as the "normal" user
    When I set my position's "Stop Loss" price to "65.000"
    And I cancel the edit
    Then my position should still show its first Stop Loss and Take Profit

  # --- Closing ---

  @smoke
  Scenario: Close part of a position
    Given I have a "Buy" position of "0.2" lots on "UKOIL"
    And I am logged in as the "normal" user
    When I close "0.1" lots of my position
    Then I should see the message "Position has been closed."
    And my position should be listed with "0.1" lots

  Scenario Outline: Close a whole <side> position
    Given I have a "<side>" position of "0.2" lots on "UKOIL"
    And I am logged in as the "normal" user
    When I close my whole position using Max
    Then I should see the message "Position has been closed."
    And my position should no longer be listed

    Examples:
      | side |
      | Buy  |
      | Sell |

  Scenario: Min and Max fill in the smallest volume and the whole position
    Given I have a "Buy" position of "0.2" lots on "UKOIL"
    And I am logged in as the "normal" user
    When I open the close dialog for my position
    And I press "Min" in the close dialog
    Then the close volume should read "0.1"
    When I press "Max" in the close dialog
    Then the close volume should read "0.2"

  Scenario Outline: Closing a volume of "<volume>" lots isn't allowed
    Given I have a "Buy" position of "0.2" lots on "UKOIL"
    And I am logged in as the "normal" user
    When I open the close dialog for my position
    And I enter a close volume of "<volume>"
    Then I should see the close volume error "<error>"
    And I should not be able to confirm the close

    Examples:
      | volume | error                        |
      | 0      | Please enter a valid volume. |
      | 0.05   | Minimum volume is 0.1.       |
      | 0.15   | Please enter a valid volume. |
      | 0.3    | Maximum volume is 0.2.       |

  Scenario: A position can only be closed once a volume is entered
    Given I have a "Buy" position of "0.2" lots on "UKOIL"
    And I am logged in as the "normal" user
    When I open the close dialog for my position
    Then I should not be able to confirm the close
    When I enter a close volume of "0.1"
    Then I should be able to confirm the close
    When I clear the close volume
    Then I should see the close volume error "Please enter a valid volume."
    And I should not be able to confirm the close

  Scenario: Cancelling a close keeps the position
    Given I have a "Buy" position of "0.2" lots on "UKOIL"
    And I am logged in as the "normal" user
    When I open the close dialog for my position
    And I enter a close volume of "0.1"
    And I cancel the close
    Then my position should still be listed with "0.2" lots

  # --- Failed requests ---

  Scenario Outline: Changing the Stop Loss and Take Profit fails with a <failure>
    Given I have a "Buy" position of "0.1" lots on "UKOIL" with a Stop Loss and Take Profit
    And I am logged in as the "normal" user
    And the "modify position" request is mocked to fail with a "<failure>"
    When I change my position's Stop Loss and Take Profit
    And I confirm the change
    Then I should see the message "<banner>"
    And my position should still show its first Stop Loss and Take Profit

    Examples:
      | failure       | banner                                                 |
      | 400 answer    | Rejected for this test.                                |
      | 500 answer    | Something went wrong. Please contact customer support. |
      | network error | Network error. Please try again later.                 |

  Scenario Outline: Closing a position fails with a <failure>
    Given I have a "Buy" position of "0.2" lots on "UKOIL"
    And I am logged in as the "normal" user
    And the "close position" request is mocked to fail with a "<failure>"
    When I close "0.1" lots of my position
    Then I should see the message "<banner>"
    And my position should still be listed with "0.2" lots

    Examples:
      | failure       | banner                                                 |
      | 400 answer    | Rejected for this test.                                |
      | 500 answer    | Something went wrong. Please contact customer support. |
      | network error | Network error. Please try again later.                 |
