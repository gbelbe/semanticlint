from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, then, when
from rdflib import RDF, Graph, Namespace
from rdflib.namespace import OWL, RDFS
from rdflib.namespace import SKOS as SKOS_NS

from semanticlint.checks.base import VocabType
from semanticlint.detect import detect_vocab_type

scenarios("../features/detect/vocab_detection.feature")

EX = Namespace("http://example.org/")


# ── Givens ────────────────────────────────────────────────────────────────────


@given("an RDF graph containing a skos:Concept", target_fixture="graph")
def graph_with_skos_concept() -> Graph:
    g = Graph()
    g.add((EX.Concept1, RDF.type, SKOS_NS.Concept))
    return g


@given("an RDF graph containing a skos:ConceptScheme", target_fixture="graph")
def graph_with_skos_scheme() -> Graph:
    g = Graph()
    g.add((EX.Scheme, RDF.type, SKOS_NS.ConceptScheme))
    return g


@given("an RDF graph containing an owl:Class", target_fixture="graph")
def graph_with_owl_class() -> Graph:
    g = Graph()
    g.add((EX.MyClass, RDF.type, OWL.Class))
    return g


@given("an RDF graph containing an owl:Ontology declaration", target_fixture="graph")
def graph_with_owl_ontology() -> Graph:
    g = Graph()
    g.add((EX.MyOntology, RDF.type, OWL.Ontology))
    return g


@given("an RDF graph containing only an rdfs:Class", target_fixture="graph")
def graph_with_rdfs_class_only() -> Graph:
    g = Graph()
    g.add((EX.MyClass, RDF.type, RDFS.Class))
    return g


@given("an RDF graph containing both a skos:Concept and an owl:Class", target_fixture="graph")
def graph_with_skos_and_owl() -> Graph:
    g = Graph()
    g.add((EX.Concept1, RDF.type, SKOS_NS.Concept))
    g.add((EX.MyClass, RDF.type, OWL.Class))
    return g


@given("an RDF graph with only plain RDF triples", target_fixture="graph")
def graph_plain_rdf() -> Graph:
    g = Graph()
    g.add((EX.subject, EX.predicate, EX.object))
    return g


@given("an empty RDF graph", target_fixture="graph")
def empty_graph() -> Graph:
    return Graph()


# ── When ──────────────────────────────────────────────────────────────────────


@when("I detect the vocabulary type", target_fixture="detected_type")
def detect_type(graph: Graph) -> VocabType:
    return detect_vocab_type(graph)


# ── Thens ─────────────────────────────────────────────────────────────────────


@then(parsers.parse('the detected type includes "{vocab_type}"'))
def detected_type_includes(detected_type: VocabType, vocab_type: str):
    expected = VocabType[vocab_type]
    assert detected_type & expected, f"Expected {vocab_type!r} in {detected_type!r}"


@then(parsers.parse('the detected type does not include "{vocab_type}"'))
def detected_type_excludes(detected_type: VocabType, vocab_type: str):
    expected = VocabType[vocab_type]
    assert not (detected_type & expected), f"Expected {vocab_type!r} NOT in {detected_type!r}"


@then(parsers.parse('the detected type is exactly "{vocab_type}"'))
def detected_type_exactly(detected_type: VocabType, vocab_type: str):
    expected = VocabType[vocab_type]
    assert detected_type == expected, f"Expected exactly {expected!r}, got {detected_type!r}"
