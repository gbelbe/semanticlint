Feature: SKOS scheme integrity
  As a vocabulary publisher
  I want scheme membership rules to be enforced
  So that concept scheme declarations are consistent

  Scenario: Concept with both topConceptOf and inScheme passes
    Given a SKOS concept with both skos:topConceptOf and skos:inScheme pointing to the same scheme
    When I run the SKOS scheme checks
    Then there are no violations

  Scenario: Concept with topConceptOf but no inScheme produces SKO020
    Given a SKOS concept with skos:topConceptOf but no skos:inScheme
    When I run the SKOS scheme checks
    Then there is a violation with id "SKO020"

  Scenario: Concept with inScheme only does not produce SKO020
    Given a SKOS concept with only skos:inScheme
    When I run the SKOS scheme checks
    Then there is no violation with id "SKO020"

  Scenario: Both hasTopConcept and topConceptOf asserted passes SKO021
    Given a scheme with skos:hasTopConcept and the concept with skos:topConceptOf pointing back
    When I run the SKOS scheme checks
    Then there is no violation with id "SKO021"

  Scenario: Scheme with hasTopConcept but no reciprocal topConceptOf produces SKO021
    Given a scheme with skos:hasTopConcept where the concept does not assert skos:topConceptOf
    When I run the SKOS scheme checks
    Then there is a violation with id "SKO021"

  Scenario: Concept with topConceptOf but no reciprocal hasTopConcept produces SKO021
    Given a concept with skos:topConceptOf where the scheme does not assert skos:hasTopConcept
    When I run the SKOS scheme checks
    Then there is a violation with id "SKO021"
