Feature: OWL property integrity
  As a vocabulary publisher
  I want property declaration rules to be enforced
  So that my ontology has fully specified properties and typed individuals

  Scenario: ObjectProperty with domain and range passes OWL001 and OWL002
    Given an owl:ObjectProperty with both rdfs:domain and rdfs:range
    When I run the OWL checks
    Then there are no violations

  Scenario: ObjectProperty missing rdfs:domain produces OWL001
    Given an owl:ObjectProperty with no rdfs:domain
    When I run the OWL checks
    Then there is a violation with id "OWL001"

  Scenario: ObjectProperty missing rdfs:range produces OWL002
    Given an owl:ObjectProperty with no rdfs:range
    When I run the OWL checks
    Then there is a violation with id "OWL002"

  Scenario: DatatypeProperty missing rdfs:domain produces OWL001
    Given an owl:DatatypeProperty with no rdfs:domain
    When I run the OWL checks
    Then there is a violation with id "OWL001"

  Scenario: NamedIndividual typed to a domain class passes OWL003
    Given an owl:NamedIndividual typed to a domain class
    When I run the OWL checks
    Then there is no violation with id "OWL003"

  Scenario: NamedIndividual not typed to any class produces OWL003
    Given an owl:NamedIndividual with no additional type
    When I run the OWL checks
    Then there is a violation with id "OWL003"
