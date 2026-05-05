from __future__ import annotations

from pytest_bdd import given, scenarios, when
from rdflib import RDF, Graph, Literal, Namespace
from rdflib.namespace import OWL, RDFS

from semanticlint.checks.base import CheckConfig
from semanticlint.checks.rdfs.classes import ClassLabelCheck, UndeclaredSuperclassCheck

scenarios("../features/rdfs/class_label_integrity.feature")

EX = Namespace("http://example.org/")

_RDFS_CHECKS = [ClassLabelCheck, UndeclaredSuperclassCheck]


# ── Givens ────────────────────────────────────────────────────────────────────


@given("an owl:Class with an rdfs:label", target_fixture="graph")
def owl_class_with_label() -> Graph:
    g = Graph()
    g.add((EX.MyClass, RDF.type, OWL.Class))
    g.add((EX.MyClass, RDFS.label, Literal("My Class", lang="en")))
    return g


@given("an owl:Class with no rdfs:label", target_fixture="graph")
def owl_class_no_label() -> Graph:
    g = Graph()
    g.add((EX.MyClass, RDF.type, OWL.Class))
    return g


@given("an rdfs:Class with no rdfs:label", target_fixture="graph")
def rdfs_class_no_label() -> Graph:
    g = Graph()
    g.add((EX.MyClass, RDF.type, RDFS.Class))
    return g


@given("a class with rdfs:subClassOf pointing to a declared class", target_fixture="graph")
def subclass_of_declared() -> Graph:
    g = Graph()
    g.add((EX.Child, RDF.type, OWL.Class))
    g.add((EX.Parent, RDF.type, OWL.Class))
    g.add((EX.Child, RDFS.subClassOf, EX.Parent))
    return g


@given("a class with rdfs:subClassOf pointing to an undeclared class", target_fixture="graph")
def subclass_of_undeclared() -> Graph:
    g = Graph()
    g.add((EX.Child, RDF.type, OWL.Class))
    g.add((EX.Child, RDFS.subClassOf, EX.Undefined))
    # EX.Undefined has no rdf:type owl:Class or rdfs:Class triple
    return g


# ── When ──────────────────────────────────────────────────────────────────────


@when("I run the RDFS checks", target_fixture="violations")
def run_rdfs_checks(graph: Graph) -> list:
    config = CheckConfig()
    violations = []
    for cls in _RDFS_CHECKS:
        violations.extend(cls().run(graph, config))
    return violations
