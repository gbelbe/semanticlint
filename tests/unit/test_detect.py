from __future__ import annotations

from rdflib import RDF, Graph, Namespace
from rdflib.namespace import OWL, RDFS
from rdflib.namespace import SKOS as SKOS_NS

from semanticlint.checks.base import VocabType
from semanticlint.detect import detect_vocab_type

EX = Namespace("http://example.org/")


def test_detects_skos_concept():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS_NS.Concept))
    assert detect_vocab_type(g) & VocabType.SKOS


def test_detects_skos_concept_scheme():
    g = Graph()
    g.add((EX.S1, RDF.type, SKOS_NS.ConceptScheme))
    assert detect_vocab_type(g) & VocabType.SKOS


def test_detects_owl_class():
    g = Graph()
    g.add((EX.C1, RDF.type, OWL.Class))
    assert detect_vocab_type(g) & VocabType.OWL


def test_detects_owl_ontology():
    g = Graph()
    g.add((EX.O1, RDF.type, OWL.Ontology))
    assert detect_vocab_type(g) & VocabType.OWL


def test_detects_rdfs_class():
    g = Graph()
    g.add((EX.C1, RDF.type, RDFS.Class))
    result = detect_vocab_type(g)
    assert result & VocabType.RDFS
    assert not (result & VocabType.OWL)


def test_rdfs_not_set_when_owl_present():
    g = Graph()
    g.add((EX.C1, RDF.type, OWL.Class))
    g.add((EX.C2, RDF.type, RDFS.Class))
    result = detect_vocab_type(g)
    assert result & VocabType.OWL
    assert not (result & VocabType.RDFS)


def test_detects_combined_skos_owl():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS_NS.Concept))
    g.add((EX.C2, RDF.type, OWL.Class))
    result = detect_vocab_type(g)
    assert result & VocabType.SKOS
    assert result & VocabType.OWL


def test_plain_rdf_fallback():
    g = Graph()
    g.add((EX.subject, EX.predicate, EX.object))
    assert detect_vocab_type(g) == VocabType.RDF


def test_empty_graph_is_plain_rdf():
    assert detect_vocab_type(Graph()) == VocabType.RDF


def test_rdf_always_present_for_skos():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS_NS.Concept))
    assert detect_vocab_type(g) & VocabType.RDF


def test_rdf_always_present_for_owl():
    g = Graph()
    g.add((EX.C1, RDF.type, OWL.Class))
    assert detect_vocab_type(g) & VocabType.RDF
