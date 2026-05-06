Feature: OWL quality metrics

  Scenario: All classes have rdfs:label — no QUA004
    Given all OWL classes have an rdfs:label
    When I run the quality checks
    Then there is no violation with id "QUA004"

  Scenario: Class missing rdfs:label triggers QUA004
    Given one OWL class is missing an rdfs:label
    When I run the quality checks
    Then there is a violation with id "QUA004"

  Scenario: All properties have rdfs:label — no QUA005
    Given all OWL properties have an rdfs:label
    When I run the quality checks
    Then there is no violation with id "QUA005"

  Scenario: Property missing rdfs:label triggers QUA005
    Given one OWL property is missing an rdfs:label
    When I run the quality checks
    Then there is a violation with id "QUA005"
