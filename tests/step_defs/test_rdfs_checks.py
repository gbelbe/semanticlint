from __future__ import annotations

from pytest_bdd import given, scenarios, when
from rdflib import RDF, Graph, Literal, Namespace
from rdflib.namespace import OWL, RDFS

from semanticlint.checks.base import CheckConfig, VocabType
from semanticlint.shacl.runner import run_shapes

scenarios("../features/rdfs/class_label_integrity.feature")

EX = Namespace("http://example.org/")


def _run_rdfs_checks(graph: Graph) -> list:
    """The RDFS/OWL class domain checks — RDS001 and RDS002 are both SHACL shapes now."""
    return run_shapes(graph, CheckConfig(), VocabType.RDFS | VocabType.OWL)


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
    return _run_rdfs_checks(graph)
