Feature: URI format integrity
  As a vocabulary publisher
  I want URI format rules to be enforced
  So that all entity identifiers are well-formed and internally consistent

  # ── RDF003: malformed URIs ─────────────────────────────────────────────────

  Scenario: All URIs are well-formed and produce no RDF003
    Given a SKOS concept with a clean HTTP URI
    When I run the URI format checks
    Then there are no violations

  Scenario: A concept URI containing a space produces RDF003
    Given a SKOS concept whose URI contains a space
    When I run the URI format checks
    Then there is a violation with id "RDF003"

  Scenario: A concept URI containing a control character produces RDF003
    Given a SKOS concept whose URI contains a control character
    When I run the URI format checks
    Then there is a violation with id "RDF003"

  # ── RDF004: non-HTTP/HTTPS scheme ──────────────────────────────────────────

  Scenario: A concept with an HTTP URI does not produce RDF004
    Given a SKOS concept with an HTTP URI
    When I run the URI format checks
    Then there is no violation with id "RDF004"

  Scenario: A concept with a URN scheme produces RDF004
    Given a SKOS concept with a URN URI
    When I run the URI format checks
    Then there is a violation with id "RDF004"

  Scenario: A concept with a file: URI produces RDF004
    Given a SKOS concept with a file: URI
    When I run the URI format checks
    Then there is a violation with id "RDF004"

  Scenario: A well-known external namespace entity is exempt from RDF004
    Given only an OWL class from the OWL namespace is typed in the graph
    When I run the URI format checks
    Then there is no violation with id "RDF004"

  # ── RDF005: inconsistent separator ─────────────────────────────────────────

  Scenario: All concepts use hash-based URIs and produce no RDF005
    Given two SKOS concepts both using hash-based URIs
    When I run the URI format checks
    Then there is no violation with id "RDF005"

  Scenario: All concepts use slash-based URIs and produce no RDF005
    Given two SKOS concepts both using slash-based URIs
    When I run the URI format checks
    Then there is no violation with id "RDF005"

  Scenario: Concepts mix hash and slash separators and produce RDF005
    Given two SKOS concepts where one uses a hash URI and one uses a slash URI
    When I run the URI format checks
    Then there is a violation with id "RDF005"

  # ── RDF006: entity outside declared base URI ───────────────────────────────

  Scenario: All concepts share the declared ConceptScheme base URI
    Given a concept scheme and concepts all under its base URI
    When I run the URI format checks
    Then there is no violation with id "RDF006"

  Scenario: A concept outside the declared ConceptScheme base produces RDF006
    Given a concept scheme and a concept whose URI is outside the scheme base
    When I run the URI format checks
    Then there is a violation with id "RDF006"

  Scenario: No ontology or scheme declared means no RDF006
    Given a SKOS concept with no ConceptScheme declared
    When I run the URI format checks
    Then there is no violation with id "RDF006"

  Scenario: A well-known external entity reused in the graph is exempt from RDF006
    Given a concept scheme and a class from the OWL namespace typed in the graph
    When I run the URI format checks
    Then there is no violation with id "RDF006"
