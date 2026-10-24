@market_closed @trading
Feature: Trading while the market is closed
  As a trader
  I want to be stopped from placing orders while a symbol's market is closed
  So that I know why my order can't go through

  # "the market is closed" is faked in the browser: the page is told the symbol's market status is
  # closed, so these scenarios run at any time. The server isn't asked.
  # The last scenario needs UKOIL's market to be really closed (at the weekend, say) and skips
  # while it's open. UKOIL's hours are in docs/api-notes.md.

  Background:
    Given one-click trading is off

  @smoke
  Scenario: A market order can't be placed while the market is closed
    Given the "UKOIL" market is closed
    And I am logged in as the "normal" user
    And I open "UKOIL"
    When I fill in a "Buy" market order for "0.1" lots with "Fill or Kill"
    Then the order panel should say the market is closed
    And the Place button should be disabled

  Scenario Outline: A <type> order can't be placed while the market is closed
    Given the "UKOIL" market is closed
    And I am logged in as the "normal" user
    And I open "UKOIL"
    When I fill in a "Buy" "<type>" order for "0.1" lots priced "<price>" from the market
    Then the order panel should say the market is closed
    And the Place button should be disabled

    Examples:
      | type       | price |
      | Limit      | -20%  |
      | Stop       | +20%  |
      | Stop Limit | +20%  |

  Scenario: One-click Buy and Sell aren't offered while the market is closed
    Given one-click trading is on
    And the "UKOIL" market is closed
    And I am logged in as the "normal" user
    And I open "UKOIL"
    Then the order panel should say the market is closed
    And I should not be able to buy or sell with one click

  # The page still shows the market open, as if it closed after the page loaded, so Place works and
  # the order reaches the server.
  Scenario: An order sent after the market has closed is turned down
    Given the "UKOIL" market has closed, but my page still shows it open
    And I am logged in as the "normal" user
    And I open "UKOIL"
    When I fill in a "Buy" market order for "0.1" lots with "Fill or Kill"
    And I place the order
    And I try to confirm the order
    Then I should see the message "Symbol market is closed."
