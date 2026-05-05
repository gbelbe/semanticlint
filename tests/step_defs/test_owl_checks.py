from __future__ import annotations

from pytest_bdd import given, scenarios, when
from rdflib import RDF, Graph, Namespace
from rdflib.namespace import OWL, RDFS

from semanticlint.checks.base import CheckConfig
from semanticlint.checks.owl.properties import (
    PropertyDomainCheck,
    PropertyRangeCheck,
    UntypedIndividualCheck,
)

scenarios("../features/owl/property_integrity.feature")

EX = Namespace("http://example.org/")

_OWL_CHECKS = [PropertyDomainCheck, PropertyRangeCheck, UntypedIndividualCheck]


# ── Givens ────────────────────────────────────────────────────────────────────


@given("an owl:ObjectProperty with both rdfs:domain and rdfs:range", target_fixture="graph")
def property_with_domain_and_range() -> Graph:
    g = Graph()
    g.add((EX.myProp, RDF.type, OWL.ObjectProperty))
    g.add((EX.myProp, RDFS.domain, EX.Source))
    g.add((EX.myProp, RDFS.range, EX.Target))
    return g


@given("an owl:ObjectProperty with no rdfs:domain", target_fixture="graph")
def property_no_domain() -> Graph:
    g = Graph()
    g.add((EX.myProp, RDF.type, OWL.ObjectProperty))
    g.add((EX.myProp, RDFS.range, EX.Target))
    return g


@given("an owl:ObjectProperty with no rdfs:range", target_fixture="graph")
def property_no_range() -> Graph:
    g = Graph()
    g.add((EX.myProp, RDF.type, OWL.ObjectProperty))
    g.add((EX.myProp, RDFS.domain, EX.Source))
    return g


@given("an owl:DatatypeProperty with no rdfs:domain", target_fixture="graph")
def datatype_property_no_domain() -> Graph:
    g = Graph()
    g.add((EX.myProp, RDF.type, OWL.DatatypeProperty))
    g.add((EX.myProp, RDFS.range, EX.Target))
    return g


@given("an owl:NamedIndividual typed to a domain class", target_fixture="graph")
def individual_with_type() -> Graph:
    g = Graph()
    g.add((EX.MyClass, RDF.type, OWL.Class))
    g.add((EX.i1, RDF.type, OWL.NamedIndividual))
    g.add((EX.i1, RDF.type, EX.MyClass))
    return g


@given("an owl:NamedIndividual with no additional type", target_fixture="graph")
def individual_no_type() -> Graph:
    g = Graph()
    g.add((EX.i1, RDF.type, OWL.NamedIndividual))
    return g


# ── When ──────────────────────────────────────────────────────────────────────


@when("I run the OWL checks", target_fixture="violations")
def run_owl_checks(graph: Graph) -> list:
    config = CheckConfig()
    violations = []
    for cls in _OWL_CHECKS:
        violations.extend(cls().run(graph, config))
    return violations
