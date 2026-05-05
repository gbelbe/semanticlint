from __future__ import annotations

from pytest_bdd import given, scenarios, when
from rdflib import RDF, Graph, Namespace
from rdflib.namespace import SKOS

from semanticlint.checks.base import CheckConfig
from semanticlint.checks.skos.schemes import TopConceptAlignmentCheck, TopConceptInSchemeCheck

scenarios("../features/skos/scheme_integrity.feature")

EX = Namespace("http://example.org/")

_SCHEME_CHECKS = [TopConceptInSchemeCheck, TopConceptAlignmentCheck]


# ── Givens ────────────────────────────────────────────────────────────────────


@given(
    "a SKOS concept with both skos:topConceptOf and skos:inScheme pointing to the same scheme",
    target_fixture="graph",
)
def concept_top_and_in_scheme() -> Graph:
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.Scheme, RDF.type, SKOS.ConceptScheme))
    g.add((EX.C1, SKOS.topConceptOf, EX.Scheme))
    g.add((EX.C1, SKOS.inScheme, EX.Scheme))
    g.add((EX.Scheme, SKOS.hasTopConcept, EX.C1))
    return g


@given(
    "a SKOS concept with skos:topConceptOf but no skos:inScheme",
    target_fixture="graph",
)
def concept_top_without_in_scheme() -> Graph:
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.Scheme, RDF.type, SKOS.ConceptScheme))
    g.add((EX.C1, SKOS.topConceptOf, EX.Scheme))
    # no skos:inScheme triple
    return g


@given("a SKOS concept with only skos:inScheme", target_fixture="graph")
def concept_in_scheme_only() -> Graph:
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.Scheme, RDF.type, SKOS.ConceptScheme))
    g.add((EX.C1, SKOS.inScheme, EX.Scheme))
    return g


@given(
    "a scheme with skos:hasTopConcept and the concept with skos:topConceptOf pointing back",
    target_fixture="graph",
)
def both_directions_stated() -> Graph:
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.Scheme, RDF.type, SKOS.ConceptScheme))
    g.add((EX.Scheme, SKOS.hasTopConcept, EX.C1))
    g.add((EX.C1, SKOS.topConceptOf, EX.Scheme))
    g.add((EX.C1, SKOS.inScheme, EX.Scheme))
    return g


@given(
    "a scheme with skos:hasTopConcept where the concept does not assert skos:topConceptOf",
    target_fixture="graph",
)
def has_top_without_reciprocal() -> Graph:
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.Scheme, RDF.type, SKOS.ConceptScheme))
    g.add((EX.Scheme, SKOS.hasTopConcept, EX.C1))
    # no skos:topConceptOf triple
    return g


@given(
    "a concept with skos:topConceptOf where the scheme does not assert skos:hasTopConcept",
    target_fixture="graph",
)
def top_concept_of_without_reciprocal() -> Graph:
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.Scheme, RDF.type, SKOS.ConceptScheme))
    g.add((EX.C1, SKOS.topConceptOf, EX.Scheme))
    g.add((EX.C1, SKOS.inScheme, EX.Scheme))
    # no skos:hasTopConcept triple on scheme
    return g


# ── When ──────────────────────────────────────────────────────────────────────


@when("I run the SKOS scheme checks", target_fixture="violations")
def run_scheme_checks(graph: Graph) -> list:
    config = CheckConfig()
    violations = []
    for cls in _SCHEME_CHECKS:
        violations.extend(cls().run(graph, config))
    return violations
