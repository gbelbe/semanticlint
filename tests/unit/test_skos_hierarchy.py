from __future__ import annotations

from rdflib import RDF, Graph, Namespace
from rdflib.namespace import SKOS

from semanticlint.checks.base import CheckConfig, Severity
from semanticlint.checks.skos.hierarchy import BroaderCycleCheck, OrphanConceptCheck

EX = Namespace("http://example.org/")


def _run(check_cls, graph):
    return check_cls().run(graph, CheckConfig())


# ── SKO010 ────────────────────────────────────────────────────────────────────


def test_sko010_no_violation_linear_hierarchy():
    g = Graph()
    for c in (EX.A, EX.B, EX.C):
        g.add((c, RDF.type, SKOS.Concept))
    g.add((EX.A, SKOS.topConceptOf, EX.Scheme))
    g.add((EX.B, SKOS.broader, EX.A))
    g.add((EX.C, SKOS.broader, EX.B))
    assert _run(BroaderCycleCheck, g) == []


def test_sko010_violation_self_reference():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.broader, EX.C1))
    violations = _run(BroaderCycleCheck, g)
    assert any(v.check_id == "SKO010" for v in violations)


def test_sko010_violation_two_node_cycle():
    g = Graph()
    g.add((EX.A, RDF.type, SKOS.Concept))
    g.add((EX.B, RDF.type, SKOS.Concept))
    g.add((EX.A, SKOS.broader, EX.B))
    g.add((EX.B, SKOS.broader, EX.A))
    violations = _run(BroaderCycleCheck, g)
    assert any(v.check_id == "SKO010" for v in violations)


def test_sko010_violation_three_node_cycle():
    g = Graph()
    for c in (EX.A, EX.B, EX.C):
        g.add((c, RDF.type, SKOS.Concept))
    g.add((EX.A, SKOS.broader, EX.B))
    g.add((EX.B, SKOS.broader, EX.C))
    g.add((EX.C, SKOS.broader, EX.A))
    violations = _run(BroaderCycleCheck, g)
    assert any(v.check_id == "SKO010" for v in violations)


def test_sko010_no_violation_empty_graph():
    assert _run(BroaderCycleCheck, Graph()) == []


def test_sko010_violation_contains_offending_node():
    g = Graph()
    g.add((EX.A, RDF.type, SKOS.Concept))
    g.add((EX.A, SKOS.broader, EX.A))
    violations = _run(BroaderCycleCheck, g)
    assert violations[0].subject == EX.A


def test_sko010_severity_is_error():
    g = Graph()
    g.add((EX.A, RDF.type, SKOS.Concept))
    g.add((EX.A, SKOS.broader, EX.A))
    violations = _run(BroaderCycleCheck, g)
    assert violations[0].severity == Severity.ERROR


# ── SKO011 ────────────────────────────────────────────────────────────────────


def test_sko011_no_violation_has_broader():
    g = Graph()
    g.add((EX.Child, RDF.type, SKOS.Concept))
    g.add((EX.Parent, RDF.type, SKOS.Concept))
    g.add((EX.Parent, SKOS.topConceptOf, EX.Scheme))
    g.add((EX.Child, SKOS.broader, EX.Parent))
    assert _run(OrphanConceptCheck, g) == []


def test_sko011_no_violation_is_top_concept_of():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.topConceptOf, EX.Scheme))
    assert _run(OrphanConceptCheck, g) == []


def test_sko011_no_violation_declared_by_scheme():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.Scheme, SKOS.hasTopConcept, EX.C1))
    assert _run(OrphanConceptCheck, g) == []


def test_sko011_violation_no_broader_no_top():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    violations = _run(OrphanConceptCheck, g)
    assert any(v.check_id == "SKO011" for v in violations)


def test_sko011_severity_is_warning():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    violations = _run(OrphanConceptCheck, g)
    assert violations[0].severity == Severity.WARNING


def test_sko011_no_violation_empty_graph():
    assert _run(OrphanConceptCheck, Graph()) == []
