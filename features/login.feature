@login
Feature: Login
  As a demo account holder
  I want to log in to AQX Trader
  So that I can access the trading platform

  Background:
    Given I am on the login page

  @smoke
  Scenario: Successful login with valid credentials
    When I log in as the "normal" user
    Then I should be on the trade page
    And I should see my account information

  Scenario: Login fails with an invalid password
    When I log in as the "normal" user with password "WrongPass123!"
    Then I should see the invalid credentials error
    And I should remain on the login page

  Scenario Outline: Log in button is disabled until both fields are filled
    When I enter account ID "<account_id>" and password "<password>"
    Then the log in button should be disabled

    Examples:
      | account_id | password |
      |            |          |
      | 123456     |          |
      |            | secret   |
