from __future__ import annotations

from rdflib import RDF, Graph, Namespace
from rdflib.namespace import OWL

from semanticlint.checks.base import CheckConfig, Severity
from semanticlint.checks.owl.properties import UntypedIndividualCheck

# OWL001 (rdfs:domain) and OWL002 (rdfs:range) migrated to SHACL shapes — see
# tests/unit/test_shacl_runner.py and tests/features/shacl/shacl_validation.feature.

EX = Namespace("http://example.org/")


def _run(check_cls, graph):
    return check_cls().run(graph, CheckConfig())


# ── OWL003 ────────────────────────────────────────────────────────────────────


def test_owl003_no_violation_individual_typed_to_class():
    g = Graph()
    g.add((EX.i1, RDF.type, OWL.NamedIndividual))
    g.add((EX.i1, RDF.type, EX.MyClass))
    assert _run(UntypedIndividualCheck, g) == []


def test_owl003_violation_individual_not_typed_to_class():
    g = Graph()
    g.add((EX.i1, RDF.type, OWL.NamedIndividual))
    violations = _run(UntypedIndividualCheck, g)
    assert any(v.check_id == "OWL003" for v in violations)


def test_owl003_violation_subject_is_individual_uri():
    g = Graph()
    g.add((EX.i1, RDF.type, OWL.NamedIndividual))
    violations = _run(UntypedIndividualCheck, g)
    assert violations[0].subject == EX.i1


def test_owl003_severity_is_warning():
    g = Graph()
    g.add((EX.i1, RDF.type, OWL.NamedIndividual))
    violations = _run(UntypedIndividualCheck, g)
    assert violations[0].severity == Severity.WARNING


def test_owl003_no_violation_empty_graph():
    assert _run(UntypedIndividualCheck, Graph()) == []


def test_owl003_no_violation_multiple_types():
    g = Graph()
    g.add((EX.i1, RDF.type, OWL.NamedIndividual))
    g.add((EX.i1, RDF.type, EX.ClassA))
    g.add((EX.i1, RDF.type, EX.ClassB))
    assert _run(UntypedIndividualCheck, g) == []
