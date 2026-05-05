from __future__ import annotations

from rdflib import RDF, Graph, Literal, Namespace
from rdflib.namespace import OWL, RDFS

from semanticlint.checks.base import CheckConfig, Severity
from semanticlint.checks.rdfs.classes import ClassLabelCheck, UndeclaredSuperclassCheck

EX = Namespace("http://example.org/")


def _run(check_cls, graph):
    return check_cls().run(graph, CheckConfig())


# ── RDS001 ────────────────────────────────────────────────────────────────────


def test_rds001_no_violation_class_has_label():
    g = Graph()
    g.add((EX.C, RDF.type, OWL.Class))
    g.add((EX.C, RDFS.label, Literal("My Class", lang="en")))
    assert _run(ClassLabelCheck, g) == []


def test_rds001_violation_owl_class_no_label():
    g = Graph()
    g.add((EX.C, RDF.type, OWL.Class))
    violations = _run(ClassLabelCheck, g)
    assert any(v.check_id == "RDS001" for v in violations)


def test_rds001_violation_rdfs_class_no_label():
    g = Graph()
    g.add((EX.C, RDF.type, RDFS.Class))
    violations = _run(ClassLabelCheck, g)
    assert any(v.check_id == "RDS001" for v in violations)


def test_rds001_violation_subject_is_class_uri():
    g = Graph()
    g.add((EX.C, RDF.type, OWL.Class))
    violations = _run(ClassLabelCheck, g)
    assert violations[0].subject == EX.C


def test_rds001_severity_is_warning():
    g = Graph()
    g.add((EX.C, RDF.type, OWL.Class))
    violations = _run(ClassLabelCheck, g)
    assert violations[0].severity == Severity.WARNING


def test_rds001_no_violation_empty_graph():
    assert _run(ClassLabelCheck, Graph()) == []


def test_rds001_no_violation_multiple_classes_all_labelled():
    g = Graph()
    for name, label in [(EX.C1, "Class One"), (EX.C2, "Class Two")]:
        g.add((name, RDF.type, OWL.Class))
        g.add((name, RDFS.label, Literal(label, lang="en")))
    assert _run(ClassLabelCheck, g) == []


def test_rds001_violation_only_unlabelled_class_flagged():
    g = Graph()
    g.add((EX.C1, RDF.type, OWL.Class))
    g.add((EX.C1, RDFS.label, Literal("Labelled", lang="en")))
    g.add((EX.C2, RDF.type, OWL.Class))
    violations = _run(ClassLabelCheck, g)
    subjects = [v.subject for v in violations]
    assert EX.C2 in subjects
    assert EX.C1 not in subjects


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
