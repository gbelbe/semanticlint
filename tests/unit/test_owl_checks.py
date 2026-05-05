from __future__ import annotations

from rdflib import RDF, Graph, Namespace
from rdflib.namespace import OWL, RDFS

from semanticlint.checks.base import CheckConfig, Severity
from semanticlint.checks.owl.properties import (
    PropertyDomainCheck,
    PropertyRangeCheck,
    UntypedIndividualCheck,
)

EX = Namespace("http://example.org/")


def _run(check_cls, graph):
    return check_cls().run(graph, CheckConfig())


# ── OWL001 ────────────────────────────────────────────────────────────────────


def test_owl001_no_violation_property_has_domain():
    g = Graph()
    g.add((EX.p, RDF.type, OWL.ObjectProperty))
    g.add((EX.p, RDFS.domain, EX.Source))
    assert _run(PropertyDomainCheck, g) == []


def test_owl001_violation_object_property_no_domain():
    g = Graph()
    g.add((EX.p, RDF.type, OWL.ObjectProperty))
    violations = _run(PropertyDomainCheck, g)
    assert any(v.check_id == "OWL001" for v in violations)


def test_owl001_violation_datatype_property_no_domain():
    g = Graph()
    g.add((EX.p, RDF.type, OWL.DatatypeProperty))
    violations = _run(PropertyDomainCheck, g)
    assert any(v.check_id == "OWL001" for v in violations)


def test_owl001_violation_subject_is_property_uri():
    g = Graph()
    g.add((EX.p, RDF.type, OWL.ObjectProperty))
    violations = _run(PropertyDomainCheck, g)
    assert violations[0].subject == EX.p


def test_owl001_severity_is_warning():
    g = Graph()
    g.add((EX.p, RDF.type, OWL.ObjectProperty))
    violations = _run(PropertyDomainCheck, g)
    assert violations[0].severity == Severity.WARNING


def test_owl001_no_violation_empty_graph():
    assert _run(PropertyDomainCheck, Graph()) == []


# ── OWL002 ────────────────────────────────────────────────────────────────────


def test_owl002_no_violation_property_has_range():
    g = Graph()
    g.add((EX.p, RDF.type, OWL.ObjectProperty))
    g.add((EX.p, RDFS.range, EX.Target))
    assert _run(PropertyRangeCheck, g) == []


def test_owl002_violation_object_property_no_range():
    g = Graph()
    g.add((EX.p, RDF.type, OWL.ObjectProperty))
    violations = _run(PropertyRangeCheck, g)
    assert any(v.check_id == "OWL002" for v in violations)


def test_owl002_violation_datatype_property_no_range():
    g = Graph()
    g.add((EX.p, RDF.type, OWL.DatatypeProperty))
    violations = _run(PropertyRangeCheck, g)
    assert any(v.check_id == "OWL002" for v in violations)


def test_owl002_violation_subject_is_property_uri():
    g = Graph()
    g.add((EX.p, RDF.type, OWL.ObjectProperty))
    violations = _run(PropertyRangeCheck, g)
    assert violations[0].subject == EX.p


def test_owl002_no_violation_empty_graph():
    assert _run(PropertyRangeCheck, Graph()) == []


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
