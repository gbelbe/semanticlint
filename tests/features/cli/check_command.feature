Feature: semanticlint check command

  Scenario: Valid SKOS file exits with code 0
    Given a valid SKOS Turtle file
    When I run semanticlint check
    Then the exit code is 0

  Scenario: Invalid Turtle syntax exits with code 1
    Given a Turtle file with invalid syntax
    When I run semanticlint check
    Then the exit code is 1

  Scenario: File with warnings and fail-on error exits with code 0
    Given a SKOS Turtle file with missing prefLabels
    When I run semanticlint check with fail-on "error"
    Then the exit code is 0

  Scenario: File with warnings and fail-on warning exits with code 1
    Given a SKOS Turtle file with missing prefLabels
    When I run semanticlint check with fail-on "warning"
    Then the exit code is 1

  Scenario: Non-existent path exits with code 1
    Given a non-existent path
    When I run semanticlint check
    Then the exit code is 1
