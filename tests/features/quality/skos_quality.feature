Feature: SKOS quality metrics

  Scenario: All concepts have prefLabel — no label coverage violation
    Given all SKOS concepts have an English prefLabel
    When I run the quality checks
    Then there is no violation with id "QUA001"

  Scenario: Some concepts missing prefLabel triggers QUA001
    Given some SKOS concepts are missing a prefLabel
    When I run the quality checks
    Then there is a violation with id "QUA001"

  Scenario: Missing prefLabel with zero threshold — no violation
    Given some SKOS concepts are missing a prefLabel
    And the label coverage threshold is 0.0
    When I run the quality checks
    Then there is no violation with id "QUA001"

  Scenario: All concepts have definition — no QUA002
    Given all SKOS concepts have a definition
    When I run the quality checks
    Then there is no violation with id "QUA002"

  Scenario: No concepts have definition — below default threshold
    Given no SKOS concepts have a definition
    When I run the quality checks
    Then there is a violation with id "QUA002"

  Scenario: All concepts have English prefLabel — no QUA003
    Given all SKOS concepts have an English prefLabel
    When I run the quality checks
    Then there is no violation with id "QUA003"

  Scenario: Concept missing English prefLabel triggers QUA003
    Given one SKOS concept is missing an English prefLabel
    When I run the quality checks
    Then there is a violation with id "QUA003"

  Scenario: French required but labels are English only triggers QUA003
    Given all SKOS concepts have an English prefLabel
    And French is required
    When I run the quality checks
    Then there is a violation with id "QUA003"
