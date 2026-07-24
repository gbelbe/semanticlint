from __future__ import annotations

from pytest_bdd import given, scenarios, when
from rdflib import RDF, Graph
from rdflib.namespace import OWL, SKOS
from rdflib.term import URIRef

from semanticlint.checks.base import CheckConfig
from semanticlint.checks.rdf.uris import (
    BaseURIConsistencyCheck,
    DuplicateEntityURICheck,
    InconsistentSeparatorCheck,
    MalformedURICheck,
    NonHttpURICheck,
)

scenarios("../features/rdf/uri_format.feature")

_URI_CHECKS = [
    MalformedURICheck,
    NonHttpURICheck,
    InconsistentSeparatorCheck,
    BaseURIConsistencyCheck,
    DuplicateEntityURICheck,
]


# ── Givens ────────────────────────────────────────────────────────────────────


@given("a SKOS concept with a clean HTTP URI", target_fixture="graph")
def clean_http_concept() -> Graph:
    g = Graph()
    g.add((URIRef("http://example.org/C1"), RDF.type, SKOS.Concept))
    return g


@given("a SKOS concept whose URI contains a space", target_fixture="graph")
def concept_uri_with_space() -> Graph:
    g = Graph()
    g.add((URIRef("http://example.org/my concept"), RDF.type, SKOS.Concept))
    return g


@given("a SKOS concept whose URI contains a control character", target_fixture="graph")
def concept_uri_with_control_char() -> Graph:
    g = Graph()
    g.add((URIRef("http://example.org/a\x01b"), RDF.type, SKOS.Concept))
    return g


@given("a SKOS concept whose URI has more than one hash fragment", target_fixture="graph")
def concept_uri_with_two_hashes() -> Graph:
    g = Graph()
    g.add(
        (
            URIRef("https://ontology.adeo.com/kb#https://docs.google.com/presentation/d/1#slide"),
            RDF.type,
            SKOS.Concept,
        )
    )
    return g


@given("a SKOS concept with an HTTP URI", target_fixture="graph")
def concept_http_uri() -> Graph:
    g = Graph()
    g.add((URIRef("http://example.org/C1"), RDF.type, SKOS.Concept))
    return g


@given("a SKOS concept with a URN URI", target_fixture="graph")
def concept_urn_uri() -> Graph:
    g = Graph()
    g.add((URIRef("urn:example:C1"), RDF.type, SKOS.Concept))
    return g


@given("a SKOS concept with a file: URI", target_fixture="graph")
def concept_file_uri() -> Graph:
    g = Graph()
    g.add((URIRef("file:///example/C1"), RDF.type, SKOS.Concept))
    return g


@given("only an OWL class from the OWL namespace is typed in the graph", target_fixture="graph")
def owl_external_class() -> Graph:
    g = Graph()
    g.add((OWL.Class, RDF.type, OWL.Class))
    return g


@given("two SKOS concepts both using hash-based URIs", target_fixture="graph")
def two_hash_concepts() -> Graph:
    g = Graph()
    g.add((URIRef("http://example.org/vocab#C1"), RDF.type, SKOS.Concept))
    g.add((URIRef("http://example.org/vocab#C2"), RDF.type, SKOS.Concept))
    return g


@given("two SKOS concepts both using slash-based URIs", target_fixture="graph")
def two_slash_concepts() -> Graph:
    g = Graph()
    g.add((URIRef("http://example.org/vocab/C1"), RDF.type, SKOS.Concept))
    g.add((URIRef("http://example.org/vocab/C2"), RDF.type, SKOS.Concept))
    return g


@given(
    "two SKOS concepts where one uses a hash URI and one uses a slash URI",
    target_fixture="graph",
)
def mixed_separator_concepts() -> Graph:
    g = Graph()
    g.add((URIRef("http://example.org/vocab/C1"), RDF.type, SKOS.Concept))
    g.add((URIRef("http://example.org/vocab/C2"), RDF.type, SKOS.Concept))
    g.add((URIRef("http://example.org/vocab#C3"), RDF.type, SKOS.Concept))
    return g


@given("a concept scheme and concepts all under its base URI", target_fixture="graph")
def scheme_with_matching_concepts() -> Graph:
    g = Graph()
    g.add((URIRef("http://example.org/tax"), RDF.type, SKOS.ConceptScheme))
    g.add((URIRef("http://example.org/tax/C1"), RDF.type, SKOS.Concept))
    g.add((URIRef("http://example.org/tax#C2"), RDF.type, SKOS.Concept))
    return g


@given(
    "a concept scheme and a concept whose URI is outside the scheme base",
    target_fixture="graph",
)
def scheme_with_outsider_concept() -> Graph:
    g = Graph()
    g.add((URIRef("http://example.org/tax"), RDF.type, SKOS.ConceptScheme))
    g.add((URIRef("http://other.org/C1"), RDF.type, SKOS.Concept))
    return g


@given("a SKOS concept with no ConceptScheme declared", target_fixture="graph")
def concept_no_scheme() -> Graph:
    g = Graph()
    g.add((URIRef("http://example.org/C1"), RDF.type, SKOS.Concept))
    return g


@given(
    "a concept scheme and a class from the OWL namespace typed in the graph",
    target_fixture="graph",
)
def scheme_with_external_class() -> Graph:
    g = Graph()
    g.add((URIRef("http://example.org/tax"), RDF.type, SKOS.ConceptScheme))
    g.add((OWL.Class, RDF.type, OWL.Class))
    return g


# ── RDF007 Givens (duplicate entity URI) ──────────────────────────────────────

_X = URIRef("http://example.org/X")


def _typed_graph(*types) -> Graph:
    g = Graph()
    for t in types:
        g.add((_X, RDF.type, t))
    return g


@given("a URI declared only as a SKOS concept", target_fixture="graph")
def uri_single_concept() -> Graph:
    return _typed_graph(SKOS.Concept)


@given("a URI declared as both a SKOS concept and an OWL class", target_fixture="graph")
def uri_concept_class_pun() -> Graph:
    return _typed_graph(SKOS.Concept, OWL.Class)


@given("a URI declared as both an OWL class and an OWL named individual", target_fixture="graph")
def uri_class_individual_pun() -> Graph:
    return _typed_graph(OWL.Class, OWL.NamedIndividual)


@given("a URI declared as both a SKOS concept and an OWL object property", target_fixture="graph")
def uri_concept_property() -> Graph:
    return _typed_graph(SKOS.Concept, OWL.ObjectProperty)


@given("a URI declared as a concept, a class and an individual", target_fixture="graph")
def uri_three_types() -> Graph:
    return _typed_graph(SKOS.Concept, OWL.Class, OWL.NamedIndividual)


# ── When ──────────────────────────────────────────────────────────────────────


@when("I run the URI format checks", target_fixture="violations")
def run_uri_checks(graph: Graph) -> list:
    config = CheckConfig()
    violations = []
    for cls in _URI_CHECKS:
        violations.extend(cls().run(graph, config))
    return violations
