@market_closed @trading
Feature: Trading while the market is closed
  As a trader
  I want to be stopped from placing orders while a symbol's market is closed
  So that I know why my order can't go through

  # "mocked as closed" happens in the browser: the page is told the symbol's market status is
  # closed, whatever the real state, so these scenarios run at any time (@any_market).
  # The last scenario needs UKOIL's market to be really closed (at the weekend, say), so it's
  # @closed_market: it runs only outside the published hours (src/datas/market_hours.py).

  Background:
    Given one-click trading is off

  @smoke @any_market
  Scenario: A market order can't be placed while the market is closed
    Given the "UKOIL" market is mocked as closed
    And I am logged in as the "normal" user
    And I open "UKOIL"
    When I fill in a "Buy" market order for "0.1" lots with "Fill or Kill"
    Then the order panel should say the market is closed
    And the Place button should be disabled

  @any_market
  Scenario Outline: A <type> order can't be placed while the market is closed
    Given the "UKOIL" market is mocked as closed
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

  @any_market
  Scenario: One-click Buy and Sell aren't offered while the market is closed
    Given one-click trading is on
    And the "UKOIL" market is mocked as closed
    And I am logged in as the "normal" user
    And I open "UKOIL"
    Then the order panel should say the market is closed
    And I should not be able to buy or sell with one click

  # The page still shows the market open, as if it closed after the page loaded, so Place works and
  # the order reaches the server.
  @closed_market
  Scenario: An order sent after the market has closed is turned down
    Given the "UKOIL" market is closed, but mocked as open on my page
    And I am logged in as the "normal" user
    And I open "UKOIL"
    When I fill in a "Buy" market order for "0.1" lots with "Fill or Kill"
    And I place the order
    And I try to confirm the order
    Then I should see the message "Symbol market is closed."
