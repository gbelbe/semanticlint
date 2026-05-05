from __future__ import annotations

from pytest_bdd import given, scenarios, when
from rdflib import RDF, Graph, Namespace
from rdflib.namespace import SKOS

from semanticlint.checks.base import CheckConfig
from semanticlint.checks.skos.hierarchy import BroaderCycleCheck, OrphanConceptCheck

scenarios("../features/skos/hierarchy_integrity.feature")

EX = Namespace("http://example.org/")

_HIERARCHY_CHECKS = [BroaderCycleCheck, OrphanConceptCheck]


# ── Givens ────────────────────────────────────────────────────────────────────


@given("a SKOS hierarchy with concepts A broader B broader C", target_fixture="graph")
def linear_hierarchy() -> Graph:
    g = Graph()
    for concept in (EX.A, EX.B, EX.C):
        g.add((concept, RDF.type, SKOS.Concept))
    g.add((EX.A, SKOS.topConceptOf, EX.Scheme))
    g.add((EX.B, SKOS.broader, EX.A))
    g.add((EX.C, SKOS.broader, EX.B))
    return g


@given("a SKOS concept that is its own skos:broader", target_fixture="graph")
def self_reference() -> Graph:
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.broader, EX.C1))
    return g


@given("two SKOS concepts each declaring the other as skos:broader", target_fixture="graph")
def two_node_cycle() -> Graph:
    g = Graph()
    g.add((EX.A, RDF.type, SKOS.Concept))
    g.add((EX.B, RDF.type, SKOS.Concept))
    g.add((EX.A, SKOS.broader, EX.B))
    g.add((EX.B, SKOS.broader, EX.A))
    return g


@given(
    "three SKOS concepts forming a broader cycle A broader B broader C broader A",
    target_fixture="graph",
)
def three_node_cycle() -> Graph:
    g = Graph()
    for concept in (EX.A, EX.B, EX.C):
        g.add((concept, RDF.type, SKOS.Concept))
    g.add((EX.A, SKOS.broader, EX.B))
    g.add((EX.B, SKOS.broader, EX.C))
    g.add((EX.C, SKOS.broader, EX.A))
    return g


@given("a SKOS concept with a skos:broader link", target_fixture="graph")
def concept_with_broader() -> Graph:
    g = Graph()
    g.add((EX.Child, RDF.type, SKOS.Concept))
    g.add((EX.Parent, RDF.type, SKOS.Concept))
    g.add((EX.Parent, SKOS.topConceptOf, EX.Scheme))
    g.add((EX.Child, SKOS.broader, EX.Parent))
    return g


@given("a SKOS concept declared as skos:topConceptOf a scheme", target_fixture="graph")
def concept_top_concept() -> Graph:
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.topConceptOf, EX.Scheme))
    return g


@given(
    "a SKOS concept with no skos:broader and no top concept declaration",
    target_fixture="graph",
)
def orphan_concept() -> Graph:
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    return g


# ── When ──────────────────────────────────────────────────────────────────────


@when("I run the SKOS hierarchy checks", target_fixture="violations")
def run_hierarchy_checks(graph: Graph) -> list:
    config = CheckConfig()
    violations = []
    for cls in _HIERARCHY_CHECKS:
        violations.extend(cls().run(graph, config))
    return violations
