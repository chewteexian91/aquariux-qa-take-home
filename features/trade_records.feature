@trade_records @trading
Feature: Order details and status across trading records
  As a trader
  I want every record of a trade to agree
  So that I can trust what the platform tells me about my money

  # One trade is followed through every place it shows up: Open Positions, Pending Orders, the
  # notifications, Positions History and Orders & Deals. Expected values are what the server
  # recorded (its own notifications), so every record is checked against the same numbers.
  # A position keeps its Order No. in every record; each close is a new order with its own number.

  Background:
    Given one-click trading is off

  @smoke
  Scenario: A position closed in two halves shows the same details everywhere
    Given I had a "Buy" position of "0.2" lots on "UKOIL" that I closed in two halves
    And I am logged in as the "normal" user
    When I open the notifications
    Then I should see a "Position Created" notification for my position
    And I should see a "Position Closed" notification for each close of my position
    When I open Positions History
    Then Positions History should list my position
    When I open Orders & Deals
    Then Orders & Deals should list my opening order as filled
    And Orders & Deals should list each close of my position as a filled order with its own Order No.

  Scenario: A partly closed position keeps its Order No. in every record
    Given I have a "Buy" position of "0.2" lots on "UKOIL" that I partly closed by "0.1" lots
    And I am logged in as the "normal" user
    Then my position should be listed with "0.1" lots
    When I open the notifications
    Then I should see a "Position Closed" notification for each close of my position
    When I open Positions History
    Then Positions History should list my position
    When I open Orders & Deals
    Then Orders & Deals should list each close of my position as a filled order with its own Order No.

  Scenario: A deleted pending order shows as cancelled
    Given I have a "Buy" "Limit" order of "0.1" lots on "UKOIL"
    And I am logged in as the "normal" user
    When I delete my order
    Then my order should no longer be pending
    When I open Orders & Deals
    Then Orders & Deals should list my order as "CANCELED"

  # The order expires at the start of the minute after next, so this waits up to two minutes.
  Scenario: An expired pending order leaves Pending Orders and shows as expired
    Given I have a "Buy" "Limit" order of "0.1" lots on "UKOIL" that expires within two minutes
    And I am logged in as the "normal" user
    When I wait for my order to expire
    Then my order should no longer be pending
    When I open Orders & Deals
    Then Orders & Deals should list my order as "EXPIRED"
    And its remarks should say when it expired
