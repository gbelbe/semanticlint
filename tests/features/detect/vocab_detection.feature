Feature: Vocabulary type detection
  As a vocabulary publisher
  I want the linter to detect the type of my vocabulary automatically
  So that the appropriate checks are applied without manual configuration

  Scenario: File using skos:Concept is detected as SKOS
    Given an RDF graph containing a skos:Concept
    When I detect the vocabulary type
    Then the detected type includes "SKOS"

  Scenario: File using skos:ConceptScheme is detected as SKOS
    Given an RDF graph containing a skos:ConceptScheme
    When I detect the vocabulary type
    Then the detected type includes "SKOS"

  Scenario: File using owl:Class is detected as OWL
    Given an RDF graph containing an owl:Class
    When I detect the vocabulary type
    Then the detected type includes "OWL"

  Scenario: File using owl:Ontology is detected as OWL
    Given an RDF graph containing an owl:Ontology declaration
    When I detect the vocabulary type
    Then the detected type includes "OWL"

  Scenario: File using only rdfs:Class is detected as RDFS
    Given an RDF graph containing only an rdfs:Class
    When I detect the vocabulary type
    Then the detected type includes "RDFS"
    And the detected type does not include "OWL"

  Scenario: File mixing skos:Concept and owl:Class is detected as both SKOS and OWL
    Given an RDF graph containing both a skos:Concept and an owl:Class
    When I detect the vocabulary type
    Then the detected type includes "SKOS"
    And the detected type includes "OWL"

  Scenario: Minimal RDF file with no known vocabulary is detected as plain RDF
    Given an RDF graph with only plain RDF triples
    When I detect the vocabulary type
    Then the detected type is exactly "RDF"

  Scenario: Empty graph is detected as plain RDF
    Given an empty RDF graph
    When I detect the vocabulary type
    Then the detected type is exactly "RDF"
