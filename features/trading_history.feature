@trading_history @trading
Feature: Trading history and notifications
  As a trader
  I want to see my closed positions, my orders and deals, and notifications of my trades
  So that I can review what happened to my money

  # Positions and orders are opened, closed and deleted through the API before logging in.
  # Notifications are only sent for positions (created / closed), not for pending orders.
  # History lists show 30 rows per page, newest first, for the last 30 days by default.
  # Failed requests are faked in the browser: they never reach the server.
  # @defect scenarios check what the site should do. They are expected to fail until it's fixed.
  # Steps to reproduce each defect by hand: docs/defects.md.

  Background:
    Given one-click trading is off

  # --- Notifications ---

  @smoke
  Scenario: A new position is notified
    Given I have a "Buy" position of "0.2" lots on "UKOIL" with a Stop Loss and Take Profit
    And I am logged in as the "normal" user
    When I open the notifications
    Then I should see a "Position Created" notification for my position

  Scenario: A closed position is notified, with its details
    Given I had a "Buy" position of "0.2" lots on "UKOIL" that I closed
    And I am logged in as the "normal" user
    When I open the notifications
    Then I should see a "Position Closed" notification for each close of my position
    When I open the latest "Position Closed" notification for my position
    Then its details should match my position and that close

  # --- History ---

  Scenario: Positions History lists a closed position
    Given I had a "Buy" position of "0.2" lots on "UKOIL" that I closed
    And I am logged in as the "normal" user
    When I open Positions History
    Then Positions History should list my position

  Scenario: Orders & Deals lists the orders that opened and closed a position
    Given I had a "Buy" position of "0.2" lots on "UKOIL" that I closed
    And I am logged in as the "normal" user
    When I open Orders & Deals
    Then Orders & Deals should list my opening order as filled
    And Orders & Deals should list each close of my position as a filled order with its own Order No.
    When I expand my opening order
    Then its deal should be "In" for "0.2" lots

  Scenario: Orders & Deals lists a deleted pending order as cancelled
    Given I had a "Buy" "Limit" order of "0.1" lots on "UKOIL" that I deleted
    And I am logged in as the "normal" user
    When I open Orders & Deals
    Then Orders & Deals should list my order as "CANCELED"

  Scenario: The last 7 days include today's orders
    Given I had a "Buy" position of "0.2" lots on "UKOIL" that I closed
    And I am logged in as the "normal" user
    When I open Orders & Deals
    And I choose the date range "Last 7 days"
    Then Orders & Deals should list my opening order as filled

  # The demo account has no orders before this year.
  Scenario: Last year has no orders
    Given I had a "Buy" position of "0.2" lots on "UKOIL" that I closed
    And I am logged in as the "normal" user
    When I open Orders & Deals
    Then Orders & Deals should list my opening order as filled
    When I choose the date range "Last year"
    Then Orders & Deals should not list my opening order
    And Orders & Deals should say there is no history

  # --- Failed loads ---
  # Defect #13: when a list fails to load, the site shows its "nothing here" message instead of an
  # error, so a trader is told they have no history. The right wording isn't
  # known, so any error message passes.

  @defect
  Scenario: A failed Orders & Deals load is reported as an error
    Given I am logged in as the "normal" user
    And the "orders and deals" request will fail with a "500 answer"
    When I open Orders & Deals
    Then I should see an error message
    And Orders & Deals should not say there is no history

  @defect
  Scenario: A failed Positions History load is reported as an error
    Given I am logged in as the "normal" user
    And the "positions history" request will fail with a "network error"
    When I open Positions History
    Then I should see an error message
    And Positions History should not say there is no history

  @defect
  Scenario: A failed notifications load is reported as an error
    Given I am logged in as the "normal" user
    And the "notifications" request will fail with a "500 answer"
    When I open the notifications
    Then I should see an error message
    And the notifications should not say there are none
