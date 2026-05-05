Feature: SKOS hierarchy integrity
  As a vocabulary publisher
  I want hierarchy rules to be enforced
  So that my taxonomy has a clean, cycle-free structure

  Scenario: Linear hierarchy produces no violations
    Given a SKOS hierarchy with concepts A broader B broader C
    When I run the SKOS hierarchy checks
    Then there are no violations

  Scenario: Concept with a self-reference in skos:broader produces SKO010
    Given a SKOS concept that is its own skos:broader
    When I run the SKOS hierarchy checks
    Then there is a violation with id "SKO010"

  Scenario: Two-node cycle in skos:broader produces SKO010
    Given two SKOS concepts each declaring the other as skos:broader
    When I run the SKOS hierarchy checks
    Then there is a violation with id "SKO010"

  Scenario: Three-node cycle in skos:broader produces SKO010
    Given three SKOS concepts forming a broader cycle A broader B broader C broader A
    When I run the SKOS hierarchy checks
    Then there is a violation with id "SKO010"

  Scenario: Concept with skos:broader is not an orphan
    Given a SKOS concept with a skos:broader link
    When I run the SKOS hierarchy checks
    Then there is no violation with id "SKO011"

  Scenario: Concept declared as top concept is not an orphan
    Given a SKOS concept declared as skos:topConceptOf a scheme
    When I run the SKOS hierarchy checks
    Then there is no violation with id "SKO011"

  Scenario: Concept with no broader and no top concept declaration produces SKO011
    Given a SKOS concept with no skos:broader and no top concept declaration
    When I run the SKOS hierarchy checks
    Then there is a violation with id "SKO011"
