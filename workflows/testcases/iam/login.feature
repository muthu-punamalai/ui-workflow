Feature: User Authentication
  As a registered user
  I want to be able to log in to the application
  So that I can access my dashboard and protected features

@authentication @login @smoke @positive
Scenario: Successful user login with valid credentials
  Given the user is on the login page at "https://app.usemultiplier.com"
  When the user logs in with the following credentials:
    | email                                | password     |
    | tester+miageorge@usemultiplier.com  | Password@123 |
  Then the user should be redirected to the dashboard
  And a welcome message should be displayed
  And a successful login message should be displayed
  When the user logs out
  Then the application should return to a clean state

@authentication @login @smoke @negative
Scenario: Unsuccessful user login with invalid credentials
  Given the user is on the login page at "https://app.usemultiplier.com"
  When the user logs in with the following credentials:
    | email                                | password     |
    | tester+miageorge@usemultiplier.com  | Password |
  Then the user should not be redirected to the dashboard
  And user should see error message