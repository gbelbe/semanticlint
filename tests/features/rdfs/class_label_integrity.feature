Feature: RDFS and OWL class integrity
  As a vocabulary publisher
  I want class declaration rules to be enforced
  So that my ontology is well-labelled and internally consistent

  Scenario: owl:Class with rdfs:label passes RDS001
    Given an owl:Class with an rdfs:label
    When I run the RDFS checks
    Then there are no violations

  Scenario: owl:Class without rdfs:label produces RDS001
    Given an owl:Class with no rdfs:label
    When I run the RDFS checks
    Then there is a violation with id "RDS001"

  Scenario: rdfs:Class without rdfs:label produces RDS001
    Given an rdfs:Class with no rdfs:label
    When I run the RDFS checks
    Then there is a violation with id "RDS001"

  Scenario: rdfs:subClassOf referencing a declared class passes RDS002
    Given a class with rdfs:subClassOf pointing to a declared class
    When I run the RDFS checks
    Then there is no violation with id "RDS002"

  Scenario: rdfs:subClassOf referencing an undeclared class produces RDS002
    Given a class with rdfs:subClassOf pointing to an undeclared class
    When I run the RDFS checks
    Then there is a violation with id "RDS002"
