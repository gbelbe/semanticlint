from __future__ import annotations

from rdflib import RDF, Graph, Namespace
from rdflib.namespace import SKOS

from semanticlint.checks.base import CheckConfig, Severity
from semanticlint.checks.skos.schemes import TopConceptAlignmentCheck, TopConceptInSchemeCheck

EX = Namespace("http://example.org/")


def _run(check_cls, graph):
    return check_cls().run(graph, CheckConfig())


# ── SKO020 ────────────────────────────────────────────────────────────────────


def test_sko020_no_violation_has_both_top_and_in_scheme():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.Scheme, RDF.type, SKOS.ConceptScheme))
    g.add((EX.C1, SKOS.topConceptOf, EX.Scheme))
    g.add((EX.C1, SKOS.inScheme, EX.Scheme))
    assert _run(TopConceptInSchemeCheck, g) == []


def test_sko020_violation_top_concept_without_in_scheme():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.Scheme, RDF.type, SKOS.ConceptScheme))
    g.add((EX.C1, SKOS.topConceptOf, EX.Scheme))
    violations = _run(TopConceptInSchemeCheck, g)
    assert any(v.check_id == "SKO020" for v in violations)


def test_sko020_no_violation_in_scheme_only():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.Scheme, RDF.type, SKOS.ConceptScheme))
    g.add((EX.C1, SKOS.inScheme, EX.Scheme))
    assert _run(TopConceptInSchemeCheck, g) == []


def test_sko020_violation_subject_is_concept_uri():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.Scheme, RDF.type, SKOS.ConceptScheme))
    g.add((EX.C1, SKOS.topConceptOf, EX.Scheme))
    violations = _run(TopConceptInSchemeCheck, g)
    assert violations[0].subject == EX.C1


def test_sko020_no_violation_empty_graph():
    assert _run(TopConceptInSchemeCheck, Graph()) == []


def test_sko020_severity_is_error():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.Scheme, RDF.type, SKOS.ConceptScheme))
    g.add((EX.C1, SKOS.topConceptOf, EX.Scheme))
    violations = _run(TopConceptInSchemeCheck, g)
    assert violations[0].severity == Severity.ERROR


# ── SKO021 ────────────────────────────────────────────────────────────────────


def test_sko021_no_violation_both_directions_stated():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.Scheme, RDF.type, SKOS.ConceptScheme))
    g.add((EX.Scheme, SKOS.hasTopConcept, EX.C1))
    g.add((EX.C1, SKOS.topConceptOf, EX.Scheme))
    assert _run(TopConceptAlignmentCheck, g) == []


def test_sko021_violation_has_top_concept_without_reciprocal():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.Scheme, RDF.type, SKOS.ConceptScheme))
    g.add((EX.Scheme, SKOS.hasTopConcept, EX.C1))
    violations = _run(TopConceptAlignmentCheck, g)
    assert any(v.check_id == "SKO021" for v in violations)


def test_sko021_violation_top_concept_of_without_reciprocal():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.Scheme, RDF.type, SKOS.ConceptScheme))
    g.add((EX.C1, SKOS.topConceptOf, EX.Scheme))
    g.add((EX.C1, SKOS.inScheme, EX.Scheme))
    violations = _run(TopConceptAlignmentCheck, g)
    assert any(v.check_id == "SKO021" for v in violations)


def test_sko021_no_violation_empty_scheme():
    g = Graph()
    g.add((EX.Scheme, RDF.type, SKOS.ConceptScheme))
    assert _run(TopConceptAlignmentCheck, g) == []


def test_sko021_severity_is_warning():
    g = Graph()
    g.add((EX.Scheme, RDF.type, SKOS.ConceptScheme))
    g.add((EX.Scheme, SKOS.hasTopConcept, EX.C1))
    violations = _run(TopConceptAlignmentCheck, g)
    assert violations[0].severity == Severity.WARNING
