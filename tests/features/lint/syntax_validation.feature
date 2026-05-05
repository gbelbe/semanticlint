Feature: RDF syntax validation
  As a vocabulary publisher
  I want to detect syntax errors in my RDF files
  So that I can fix them before publication

  Scenario: Valid Turtle file produces no violations
    Given a valid Turtle file
    When I run the syntax linter on it
    Then there are no violations

  Scenario: Turtle file with a syntax error produces violation RDF001
    Given a Turtle file with a syntax error
    When I run the syntax linter on it
    Then there is a violation with id "RDF001"
    And the violation severity is "error"

  Scenario: Valid RDF/XML file produces no violations
    Given a valid RDF/XML file
    When I run the syntax linter on it
    Then there are no violations

  Scenario: Valid JSON-LD file produces no violations
    Given a valid JSON-LD file
    When I run the syntax linter on it
    Then there are no violations

  Scenario: Valid N-Triples file produces no violations
    Given a valid N-Triples file
    When I run the syntax linter on it
    Then there are no violations

  Scenario: Empty file produces violation RDF002
    Given an empty RDF file
    When I run the syntax linter on it
    Then there is a violation with id "RDF002"

  Scenario: Violation carries the source file path
    Given a Turtle file with a syntax error
    When I run the syntax linter on it
    Then the violation location references the source file
