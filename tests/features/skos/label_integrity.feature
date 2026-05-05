Feature: SKOS label integrity
  As a vocabulary publisher
  I want label rules to be enforced
  So that my SKOS taxonomy is unambiguous and interoperable

  Scenario: Concept with one prefLabel per language passes
    Given a SKOS concept with one prefLabel in English
    When I run the SKOS label checks
    Then there are no violations

  Scenario: Concept with two prefLabels in the same language produces SKO001
    Given a SKOS concept with two prefLabels in English
    When I run the SKOS label checks
    Then there is a violation with id "SKO001"

  Scenario: Concept with prefLabels in different languages does not produce SKO001
    Given a SKOS concept with one prefLabel in English and one in French
    When I run the SKOS label checks
    Then there are no violations

  Scenario: Concept with no prefLabel produces SKO002
    Given a SKOS concept with no prefLabel
    When I run the SKOS label checks
    Then there is a violation with id "SKO002"

  Scenario: Concept with only an altLabel but no prefLabel produces SKO002
    Given a SKOS concept with only an altLabel
    When I run the SKOS label checks
    Then there is a violation with id "SKO002"

  Scenario: Same literal as prefLabel and altLabel on one concept produces SKO003
    Given a SKOS concept with the same literal as both prefLabel and altLabel
    When I run the SKOS label checks
    Then there is a violation with id "SKO003"

  Scenario: Same literal on different concepts does not produce SKO003
    Given two SKOS concepts where each has the same literal but in different label properties
    When I run the SKOS label checks
    Then there is no violation with id "SKO003"
