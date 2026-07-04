Feature: Local project SHACL rules (auto-discovery)
  As a vocabulary owner
  I want business rules in a *.shapes.ttl file next to my ontology
  So that they are discovered, enforced and gate CI with no extra wiring

  Scenario: A local rule is discovered and enforced
    Given a project with a local Person-employment shape
    And the ontology has a Person working for two Departments
    When I check the project
    Then there is a violation with id "PersonEmploymentShape"
    And the violation severity is "error"

  Scenario: A conforming ontology passes the local rule
    Given a project with a local Person-employment shape
    And the ontology has a Person working for one Department
    When I check the project
    Then there are no violations

  Scenario: A local-rule violation breaks CI
    Given a project with a local Person-employment shape
    And the ontology has a Person working for two Departments
    When I run semanticlint check on the project
    Then the exit code is 1

  Scenario: A conforming project exits cleanly and shapes files are not linted as data
    Given a project with a local Person-employment shape
    And the ontology has a Person working for one Department
    When I run semanticlint check on the project
    Then the exit code is 0
