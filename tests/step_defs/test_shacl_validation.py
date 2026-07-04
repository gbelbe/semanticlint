from __future__ import annotations

from pytest_bdd import given, parsers, scenarios, when
from rdflib import RDF, Graph, Literal, Namespace
from rdflib.namespace import OWL, RDFS, SKOS

from semanticlint.checks.base import CheckConfig
from semanticlint.pipeline import check_graph
from semanticlint.shacl.runner import run_shapes

scenarios("../features/shacl/shacl_validation.feature")

EX = Namespace("http://example.org/")


def _owl_graph() -> Graph:
    g = Graph()
    g.add((EX.O, RDF.type, OWL.Ontology))  # makes detect_vocab_type report OWL
    return g


# ── Givens ────────────────────────────────────────────────────────────────────


@given("an OWL graph with an unlabelled class", target_fixture="graph")
def owl_unlabelled_class() -> Graph:
    g = _owl_graph()
    g.add((EX.MyClass, RDF.type, OWL.Class))
    return g


@given("an OWL graph with a property missing rdfs:domain", target_fixture="graph")
def owl_property_no_domain() -> Graph:
    g = _owl_graph()
    g.add((EX.p, RDF.type, OWL.ObjectProperty))
    g.add((EX.p, RDFS.range, EX.Target))
    return g


@given("an OWL graph with a property missing rdfs:range", target_fixture="graph")
def owl_property_no_range() -> Graph:
    g = _owl_graph()
    g.add((EX.p, RDF.type, OWL.ObjectProperty))
    g.add((EX.p, RDFS.domain, EX.Source))
    return g


@given("a SKOS graph with a concept missing skos:prefLabel", target_fixture="graph")
def skos_concept_no_label() -> Graph:
    g = Graph()
    g.add((EX.Scheme, RDF.type, SKOS.ConceptScheme))
    g.add((EX.c1, RDF.type, SKOS.Concept))
    return g


@given("an OWL graph with an individual typed only owl:NamedIndividual", target_fixture="graph")
def owl_untyped_individual() -> Graph:
    g = _owl_graph()
    g.add((EX.i, RDF.type, OWL.NamedIndividual))
    return g


@given("an OWL graph with a subclass of an undeclared class", target_fixture="graph")
def owl_undeclared_super() -> Graph:
    g = _owl_graph()
    g.add((EX.Child, RDF.type, OWL.Class))
    g.add((EX.Child, RDFS.subClassOf, EX.Undeclared))
    return g


@given("a SKOS graph with a concept labelled only in English", target_fixture="graph")
def skos_concept_en_only() -> Graph:
    g = Graph()
    g.add((EX.Scheme, RDF.type, SKOS.ConceptScheme))
    g.add((EX.c1, RDF.type, SKOS.Concept))
    g.add((EX.c1, SKOS.prefLabel, Literal("One", lang="en")))
    return g


@given("a fully specified OWL graph", target_fixture="graph")
def owl_fully_specified() -> Graph:
    g = _owl_graph()
    g.add((EX.p, RDF.type, OWL.ObjectProperty))
    g.add((EX.p, RDFS.domain, EX.Source))
    g.add((EX.p, RDFS.range, EX.Target))
    g.add((EX.Labelled, RDF.type, OWL.Class))
    g.add((EX.Labelled, RDFS.label, Literal("Labelled", lang="en")))
    return g


# ── When ──────────────────────────────────────────────────────────────────────


@when("I run the SHACL shapes", target_fixture="violations")
def run_shacl(graph: Graph) -> list:
    return run_shapes(graph, CheckConfig())


@when(parsers.parse('I run the pipeline ignoring "{check_id}"'), target_fixture="violations")
def run_pipeline_ignoring(graph: Graph, check_id: str) -> list:
    return check_graph(graph, CheckConfig(ignore=[check_id]))


@when(
    parsers.parse('I run the SHACL shapes requiring languages "{langs}"'),
    target_fixture="violations",
)
def run_shacl_languages(graph: Graph, langs: str) -> list:
    languages = [tag.strip() for tag in langs.split(",")]
    return run_shapes(graph, CheckConfig(quality={"languages": languages}))
