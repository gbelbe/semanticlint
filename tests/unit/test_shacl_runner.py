from __future__ import annotations

from rdflib import RDF, Graph, Literal, Namespace
from rdflib.namespace import OWL, RDFS, SKOS

from semanticlint.checks.base import CheckConfig, Severity, VocabType
from semanticlint.shacl.runner import run_shapes

EX = Namespace("http://example.org/")


def _owl(*triples) -> Graph:
    g = Graph()
    g.add((EX.O, RDF.type, OWL.Ontology))
    for t in triples:
        g.add(t)
    return g


# ── result mapping ────────────────────────────────────────────────────────────


def test_runner_maps_result_to_check_id_and_subject():
    g = _owl((EX.p, RDF.type, OWL.ObjectProperty), (EX.p, RDFS.range, EX.T))
    violations = run_shapes(g, CheckConfig())
    owl001 = [v for v in violations if v.check_id == "OWL001"]
    assert owl001 and owl001[0].subject == EX.p


def test_runner_maps_shacl_severity_to_semanticlint_severity():
    g = _owl((EX.C, RDF.type, OWL.Class))  # unlabelled class → RDS001
    violations = run_shapes(g, CheckConfig())
    rds = [v for v in violations if v.check_id == "RDS001"]
    assert rds and rds[0].severity == Severity.WARNING


def test_runner_message_matches_legacy():
    g = _owl((EX.p, RDF.type, OWL.ObjectProperty), (EX.p, RDFS.domain, EX.S))  # missing range
    violations = run_shapes(g, CheckConfig())
    owl002 = [v for v in violations if v.check_id == "OWL002"]
    assert owl002 and owl002[0].message == "Property has no rdfs:range"


# ── vocab gating (parity with for_vocab) ──────────────────────────────────────


def test_owl_shape_gated_out_when_vocab_not_owl():
    # A property with no owl:Ontology/Class → detected as RDF only, so the OWL
    # shape is gated out, mirroring the legacy applies_to=OWL behaviour.
    g = Graph()
    g.add((EX.p, RDF.type, OWL.ObjectProperty))
    assert run_shapes(g, CheckConfig()) == []


def test_owl_shape_fires_when_vocab_forced_owl():
    g = Graph()
    g.add((EX.p, RDF.type, OWL.ObjectProperty))
    violations = run_shapes(g, CheckConfig(), VocabType.OWL)
    assert any(v.check_id == "OWL001" for v in violations)


# ── clean graphs ──────────────────────────────────────────────────────────────


def test_clean_owl_graph_yields_no_violations():
    g = _owl(
        (EX.p, RDF.type, OWL.ObjectProperty),
        (EX.p, RDFS.domain, EX.S),
        (EX.p, RDFS.range, EX.T),
    )
    assert run_shapes(g, CheckConfig()) == []


def test_clean_skos_graph_yields_no_violations():
    g = Graph()
    g.add((EX.Scheme, RDF.type, SKOS.ConceptScheme))
    g.add((EX.c1, RDF.type, SKOS.Concept))
    g.add((EX.c1, SKOS.prefLabel, Literal("Concept One", lang="en")))
    assert run_shapes(g, CheckConfig()) == []


def test_empty_graph_yields_no_violations():
    assert run_shapes(Graph(), CheckConfig()) == []
