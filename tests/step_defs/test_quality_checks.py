from __future__ import annotations

import pytest
from pytest_bdd import given, scenarios, when
from rdflib import RDF, Graph, Literal, Namespace
from rdflib.namespace import OWL, RDFS, SKOS

from semanticlint.checks.base import CheckConfig
from semanticlint.checks.quality.metrics import (
    ClassLabelCoverageCheck,
    DefinitionCoverageCheck,
    LabelCoverageCheck,
    LanguageCoverageCheck,
    PropertyLabelCoverageCheck,
)

scenarios("../features/quality/skos_quality.feature")
scenarios("../features/quality/owl_quality.feature")

EX = Namespace("http://example.org/")

_QUALITY_CHECKS = [
    LabelCoverageCheck,
    DefinitionCoverageCheck,
    LanguageCoverageCheck,
    ClassLabelCoverageCheck,
    PropertyLabelCoverageCheck,
]


@pytest.fixture()
def config() -> CheckConfig:
    return CheckConfig()


# ── Givens — SKOS ─────────────────────────────────────────────────────────────


@given("all SKOS concepts have an English prefLabel", target_fixture="graph")
def all_concepts_labeled() -> Graph:
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.prefLabel, Literal("Concept One", lang="en")))
    g.add((EX.C2, RDF.type, SKOS.Concept))
    g.add((EX.C2, SKOS.prefLabel, Literal("Concept Two", lang="en")))
    return g


@given("some SKOS concepts are missing a prefLabel", target_fixture="graph")
def some_concepts_missing_label() -> Graph:
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.prefLabel, Literal("Concept One", lang="en")))
    g.add((EX.C2, RDF.type, SKOS.Concept))  # no prefLabel
    return g


@given("all SKOS concepts have a definition", target_fixture="graph")
def all_concepts_defined() -> Graph:
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.prefLabel, Literal("Concept One", lang="en")))
    g.add((EX.C1, SKOS.definition, Literal("The first concept.", lang="en")))
    g.add((EX.C2, RDF.type, SKOS.Concept))
    g.add((EX.C2, SKOS.prefLabel, Literal("Concept Two", lang="en")))
    g.add((EX.C2, SKOS.definition, Literal("The second concept.", lang="en")))
    return g


@given("no SKOS concepts have a definition", target_fixture="graph")
def no_concepts_defined() -> Graph:
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.prefLabel, Literal("Concept One", lang="en")))
    g.add((EX.C2, RDF.type, SKOS.Concept))
    g.add((EX.C2, SKOS.prefLabel, Literal("Concept Two", lang="en")))
    return g


@given("one SKOS concept is missing an English prefLabel", target_fixture="graph")
def one_concept_missing_en_label() -> Graph:
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.prefLabel, Literal("Concept One", lang="en")))
    g.add((EX.C2, RDF.type, SKOS.Concept))
    g.add((EX.C2, SKOS.prefLabel, Literal("Concept Deux", lang="fr")))  # no English label
    return g


@given("the label coverage threshold is 0.0", target_fixture="config")
def threshold_zero() -> CheckConfig:
    return CheckConfig(quality={"min_label_coverage": 0.0})


@given("French is required", target_fixture="config")
def french_required() -> CheckConfig:
    return CheckConfig(quality={"languages": ["fr"]})


# ── Givens — OWL ──────────────────────────────────────────────────────────────


@given("all OWL classes have an rdfs:label", target_fixture="graph")
def all_classes_labeled() -> Graph:
    g = Graph()
    g.add((EX.ClassA, RDF.type, OWL.Class))
    g.add((EX.ClassA, RDFS.label, Literal("Class A", lang="en")))
    g.add((EX.ClassB, RDF.type, OWL.Class))
    g.add((EX.ClassB, RDFS.label, Literal("Class B", lang="en")))
    return g


@given("one OWL class is missing an rdfs:label", target_fixture="graph")
def one_class_missing_label() -> Graph:
    g = Graph()
    g.add((EX.ClassA, RDF.type, OWL.Class))
    g.add((EX.ClassA, RDFS.label, Literal("Class A", lang="en")))
    g.add((EX.ClassB, RDF.type, OWL.Class))  # no rdfs:label
    return g


@given("all OWL properties have an rdfs:label", target_fixture="graph")
def all_properties_labeled() -> Graph:
    g = Graph()
    g.add((EX.propA, RDF.type, OWL.ObjectProperty))
    g.add((EX.propA, RDFS.label, Literal("Property A", lang="en")))
    g.add((EX.propB, RDF.type, OWL.DatatypeProperty))
    g.add((EX.propB, RDFS.label, Literal("Property B", lang="en")))
    return g


@given("one OWL property is missing an rdfs:label", target_fixture="graph")
def one_property_missing_label() -> Graph:
    g = Graph()
    g.add((EX.propA, RDF.type, OWL.ObjectProperty))
    g.add((EX.propA, RDFS.label, Literal("Property A", lang="en")))
    g.add((EX.propB, RDF.type, OWL.DatatypeProperty))  # no rdfs:label
    return g


# ── When ──────────────────────────────────────────────────────────────────────


@when("I run the quality checks", target_fixture="violations")
def run_quality_checks(graph: Graph, config: CheckConfig) -> list:
    violations = []
    for cls in _QUALITY_CHECKS:
        violations.extend(cls().run(graph, config))
    return violations
