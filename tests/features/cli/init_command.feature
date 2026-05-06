Feature: semanticlint init command

  Scenario: No workflow exists — file is created
    Given a project directory with no CI workflow
    When I run semanticlint init
    Then the exit code is 0
    And the workflow file is created

  Scenario: Workflow already exists — skipped without force
    Given a project directory with an existing CI workflow
    When I run semanticlint init
    Then the exit code is 0
    And the workflow file is not overwritten

  Scenario: Force flag overwrites existing workflow
    Given a project directory with an existing CI workflow
    When I run semanticlint init with --force
    Then the exit code is 0
    And the workflow file is created

  Scenario: Missing .github directory is created automatically
    Given a project directory with no .github directory
    When I run semanticlint init
    Then the exit code is 0
    And the workflow file is created

  Scenario: Custom fail-on level is written into the workflow
    Given a project directory with no CI workflow
    When I run semanticlint init with --fail-on warning
    Then the exit code is 0
    And the workflow file contains "fail-on: warning"
