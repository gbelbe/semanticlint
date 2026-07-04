from __future__ import annotations

from pytest_bdd import given, scenarios, when
from rdflib import RDF, Graph, Literal, Namespace
from rdflib.namespace import SKOS

from semanticlint.checks.base import CheckConfig, VocabType
from semanticlint.checks.skos.labels import DuplicatePrefLabelCheck, LabelDisjointnessCheck
from semanticlint.shacl.runner import run_shapes

scenarios("../features/skos/label_integrity.feature")

EX = Namespace("http://example.org/")


def _run_skos_label_checks(graph: Graph) -> list:
    """The SKOS label domain checks: SKO002 via SHACL shape + SKO001/SKO003 (Python)."""
    config = CheckConfig()
    violations = run_shapes(graph, config, VocabType.SKOS)
    violations.extend(DuplicatePrefLabelCheck().run(graph, config))
    violations.extend(LabelDisjointnessCheck().run(graph, config))
    return violations


# ── Givens ────────────────────────────────────────────────────────────────────


@given("a SKOS concept with one prefLabel in English", target_fixture="graph")
def concept_one_label() -> Graph:
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.prefLabel, Literal("Concept One", lang="en")))
    return g


@given("a SKOS concept with two prefLabels in English", target_fixture="graph")
def concept_two_labels_same_lang() -> Graph:
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.prefLabel, Literal("Concept One", lang="en")))
    g.add((EX.C1, SKOS.prefLabel, Literal("Concept 1", lang="en")))
    return g


@given("a SKOS concept with one prefLabel in English and one in French", target_fixture="graph")
def concept_two_labels_diff_lang() -> Graph:
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.prefLabel, Literal("Concept One", lang="en")))
    g.add((EX.C1, SKOS.prefLabel, Literal("Concept Un", lang="fr")))
    return g


@given("a SKOS concept with no prefLabel", target_fixture="graph")
def concept_no_label() -> Graph:
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    return g


@given("a SKOS concept with only an altLabel", target_fixture="graph")
def concept_only_alt_label() -> Graph:
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.altLabel, Literal("Alternate", lang="en")))
    return g


@given(
    "a SKOS concept with the same literal as both prefLabel and altLabel", target_fixture="graph"
)
def concept_pref_alt_overlap() -> Graph:
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.prefLabel, Literal("Foo", lang="en")))
    g.add((EX.C1, SKOS.altLabel, Literal("Foo", lang="en")))
    return g


@given(
    "two SKOS concepts where each has the same literal but in different label properties",
    target_fixture="graph",
)
def two_concepts_shared_literal_diff_concepts() -> Graph:
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.prefLabel, Literal("Foo", lang="en")))
    g.add((EX.C2, RDF.type, SKOS.Concept))
    g.add((EX.C2, SKOS.altLabel, Literal("Foo", lang="en")))
    # C2 still needs a prefLabel to not trigger SKO002
    g.add((EX.C2, SKOS.prefLabel, Literal("Bar", lang="en")))
    return g


# ── When ──────────────────────────────────────────────────────────────────────


@when("I run the SKOS label checks", target_fixture="violations")
def run_label_checks(graph: Graph) -> list:
    return _run_skos_label_checks(graph)
