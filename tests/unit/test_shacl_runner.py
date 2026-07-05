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


# ── OWL003 — untyped individual (qualified value shape) ───────────────────────


def test_owl003_untyped_individual_is_flagged():
    g = _owl((EX.i, RDF.type, OWL.NamedIndividual))  # only NamedIndividual
    v = [x for x in run_shapes(g, CheckConfig()) if x.check_id == "OWL003"]
    assert v and v[0].subject == EX.i


def test_owl003_individual_with_a_real_type_passes():
    g = _owl((EX.i, RDF.type, OWL.NamedIndividual), (EX.i, RDF.type, EX.Person))
    assert not [x for x in run_shapes(g, CheckConfig()) if x.check_id == "OWL003"]


# ── RDS002 — undeclared superclass (value shape; URI in the message) ──────────


def test_rds002_undeclared_superclass_flagged_with_uri_in_message():
    g = _owl((EX.Child, RDF.type, OWL.Class), (EX.Child, RDFS.subClassOf, EX.Undeclared))
    v = [x for x in run_shapes(g, CheckConfig()) if x.check_id == "RDS002"]
    assert v and v[0].subject == EX.Child
    assert str(EX.Undeclared) in v[0].message  # the offending class URI is appended


def test_rds002_declared_and_foundational_superclasses_pass():
    g = _owl(
        (EX.A, RDF.type, OWL.Class),
        (EX.B, RDF.type, OWL.Class),
        (EX.A, RDFS.subClassOf, EX.B),  # declared parent
        (EX.A, RDFS.subClassOf, OWL.Thing),  # foundational
    )
    assert not [x for x in run_shapes(g, CheckConfig()) if x.check_id == "RDS002"]


# ── QUA003 — config-driven language coverage ──────────────────────────────────


def _concept(*prefs) -> Graph:
    g = Graph()
    g.add((EX.Scheme, RDF.type, SKOS.ConceptScheme))
    g.add((EX.c1, RDF.type, SKOS.Concept))
    for text, lang in prefs:
        g.add((EX.c1, SKOS.prefLabel, Literal(text, lang=lang)))
    return g


def test_qua003_missing_required_language_flagged():
    g = _concept(("Un", "fr"))  # only French, English required by default
    assert any(v.check_id == "QUA003" for v in run_shapes(g, CheckConfig()))


def test_qua003_all_required_languages_present_passes():
    g = _concept(("One", "en"))
    assert not [v for v in run_shapes(g, CheckConfig()) if v.check_id == "QUA003"]


def test_qua003_respects_configured_languages():
    g = _concept(("One", "en"))  # English present, but French now required
    v = run_shapes(g, CheckConfig(quality={"languages": ["fr"]}))
    assert any(x.check_id == "QUA003" for x in v)
