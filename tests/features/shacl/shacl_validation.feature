Feature: SHACL-backed shape validation
  As a vocabulary publisher
  I want per-node cardinality rules enforced through SHACL shapes run via pySHACL
  So that structural checks share the standard SHACL engine while keeping their
  semanticlint check ids, severities and vocab gating

  Scenario: A class with no rdfs:label is reported as RDS001
    Given an OWL graph with an unlabelled class
    When I run the SHACL shapes
    Then there is a violation with id "RDS001"
    And the violation severity is "warning"

  Scenario: A property with no rdfs:domain is reported as OWL001
    Given an OWL graph with a property missing rdfs:domain
    When I run the SHACL shapes
    Then there is a violation with id "OWL001"

  Scenario: A property with no rdfs:range is reported as OWL002
    Given an OWL graph with a property missing rdfs:range
    When I run the SHACL shapes
    Then there is a violation with id "OWL002"

  Scenario: A concept with no skos:prefLabel is reported as SKO002
    Given a SKOS graph with a concept missing skos:prefLabel
    When I run the SHACL shapes
    Then there is a violation with id "SKO002"

  Scenario: A fully specified OWL graph produces no SHACL violations
    Given a fully specified OWL graph
    When I run the SHACL shapes
    Then there are no violations

  Scenario: ignore suppresses a shape-backed violation
    Given an OWL graph with a property missing rdfs:domain
    When I run the pipeline ignoring "OWL001"
    Then there is no violation with id "OWL001"

  Scenario: An individual typed only owl:NamedIndividual is reported as OWL003
    Given an OWL graph with an individual typed only owl:NamedIndividual
    When I run the SHACL shapes
    Then there is a violation with id "OWL003"

  Scenario: A subclass of an undeclared class is reported as RDS002
    Given an OWL graph with a subclass of an undeclared class
    When I run the SHACL shapes
    Then there is a violation with id "RDS002"

  Scenario: A concept missing a required language is reported as QUA003
    Given a SKOS graph with a concept labelled only in English
    When I run the SHACL shapes requiring languages "en, fr"
    Then there is a violation with id "QUA003"
