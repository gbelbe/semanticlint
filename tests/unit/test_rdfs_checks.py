from __future__ import annotations

from rdflib import RDF, Graph, Namespace
from rdflib.namespace import OWL, RDFS

from semanticlint.checks.base import CheckConfig
from semanticlint.checks.rdfs.classes import UndeclaredSuperclassCheck

# RDS001 (class needs rdfs:label) migrated to a SHACL shape — see
# tests/unit/test_shacl_runner.py and tests/features/shacl/shacl_validation.feature.

EX = Namespace("http://example.org/")


def _run(check_cls, graph):
    return check_cls().run(graph, CheckConfig())


# ── RDS002 ────────────────────────────────────────────────────────────────────


def test_rds002_no_violation_subclass_is_defined():
    g = Graph()
    g.add((EX.Child, RDF.type, OWL.Class))
    g.add((EX.Parent, RDF.type, OWL.Class))
    g.add((EX.Child, RDFS.subClassOf, EX.Parent))
    assert _run(UndeclaredSuperclassCheck, g) == []


def test_rds002_violation_references_undeclared_class():
    g = Graph()
    g.add((EX.Child, RDF.type, OWL.Class))
    g.add((EX.Child, RDFS.subClassOf, EX.Undefined))
    violations = _run(UndeclaredSuperclassCheck, g)
    assert any(v.check_id == "RDS002" for v in violations)


def test_rds002_violation_subject_is_subclass_uri():
    g = Graph()
    g.add((EX.Child, RDF.type, OWL.Class))
    g.add((EX.Child, RDFS.subClassOf, EX.Undefined))
    violations = _run(UndeclaredSuperclassCheck, g)
    assert violations[0].subject == EX.Child


def test_rds002_no_violation_empty_graph():
    assert _run(UndeclaredSuperclassCheck, Graph()) == []


def test_rds002_skips_owl_thing():
    g = Graph()
    g.add((EX.Child, RDF.type, OWL.Class))
    g.add((EX.Child, RDFS.subClassOf, OWL.Thing))
    assert _run(UndeclaredSuperclassCheck, g) == []


def test_rds002_skips_rdfs_resource():
    g = Graph()
    g.add((EX.Child, RDF.type, OWL.Class))
    g.add((EX.Child, RDFS.subClassOf, RDFS.Resource))
    assert _run(UndeclaredSuperclassCheck, g) == []
