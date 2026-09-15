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

  Scenario: Showing no warnings when min-severity is error
    Given a SKOS Turtle file with missing prefLabels
    When I run semanticlint check with min-severity "error"
    Then the exit code is 0
    And the output does not contain "WARNING"

  Scenario: Showing only errors with invalid turtle file when min-severity is error
    Given a Turtle file with invalid syntax
    When I run semanticlint check with min-severity "error"
    Then the exit code is 1
    And the output contains "ERROR"
    And the output does not contain "WARNING"

  Scenario: Shows warning when min-severity is warning
    Given a SKOS Turtle file with missing prefLabels
    When I run semanticlint check with min-severity "warning"
    Then the exit code is 0
    And the output contains "WARNING"

  Scenario: Shows infos when min-severity is info
    Given a SKOS Turtle file missing definitions and triggering info-level report
    When I run semanticlint check with min-severity "info"
    Then the exit code is 0
    And the output contains "INFO"

  Scenario: Invalid min severity exits with code 1
    Given a valid SKOS Turtle file
    When I run semanticlint check with min-severity "invalid"
    Then the exit code is 1

  Scenario: Non-existent path exits with code 1
    Given a non-existent path
    When I run semanticlint check
    Then the exit code is 1
