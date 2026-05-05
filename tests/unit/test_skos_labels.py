from __future__ import annotations

from rdflib import RDF, Graph, Literal, Namespace
from rdflib.namespace import SKOS

from semanticlint.checks.base import CheckConfig, Severity
from semanticlint.checks.skos.labels import (
    DuplicatePrefLabelCheck,
    LabelDisjointnessCheck,
    MissingPrefLabelCheck,
)

EX = Namespace("http://example.org/")


def _run(check_cls, graph):
    return check_cls().run(graph, CheckConfig())


# ── SKO001 ────────────────────────────────────────────────────────────────────


def test_sko001_no_violation_single_label_per_lang():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.prefLabel, Literal("One", lang="en")))
    assert _run(DuplicatePrefLabelCheck, g) == []


def test_sko001_violation_duplicate_same_lang():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.prefLabel, Literal("One", lang="en")))
    g.add((EX.C1, SKOS.prefLabel, Literal("Uno", lang="en")))
    violations = _run(DuplicatePrefLabelCheck, g)
    assert any(v.check_id == "SKO001" for v in violations)


def test_sko001_no_violation_different_langs():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.prefLabel, Literal("One", lang="en")))
    g.add((EX.C1, SKOS.prefLabel, Literal("Un", lang="fr")))
    assert _run(DuplicatePrefLabelCheck, g) == []


def test_sko001_violation_subject_is_concept_uri():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.prefLabel, Literal("One", lang="en")))
    g.add((EX.C1, SKOS.prefLabel, Literal("Uno", lang="en")))
    violations = _run(DuplicatePrefLabelCheck, g)
    assert violations[0].subject == EX.C1


def test_sko001_no_violation_empty_graph():
    assert _run(DuplicatePrefLabelCheck, Graph()) == []


def test_sko001_violation_severity_is_error():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.prefLabel, Literal("One", lang="en")))
    g.add((EX.C1, SKOS.prefLabel, Literal("Uno", lang="en")))
    violations = _run(DuplicatePrefLabelCheck, g)
    assert violations[0].severity == Severity.ERROR


# ── SKO002 ────────────────────────────────────────────────────────────────────


def test_sko002_no_violation_has_preflabel():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.prefLabel, Literal("One", lang="en")))
    assert _run(MissingPrefLabelCheck, g) == []


def test_sko002_violation_no_label_at_all():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    violations = _run(MissingPrefLabelCheck, g)
    assert any(v.check_id == "SKO002" for v in violations)


def test_sko002_violation_only_alt_label():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.altLabel, Literal("Alternate", lang="en")))
    violations = _run(MissingPrefLabelCheck, g)
    assert any(v.check_id == "SKO002" for v in violations)


def test_sko002_violation_subject_is_concept_uri():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    violations = _run(MissingPrefLabelCheck, g)
    assert violations[0].subject == EX.C1


def test_sko002_no_violation_empty_graph():
    assert _run(MissingPrefLabelCheck, Graph()) == []


def test_sko002_severity_is_warning():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    violations = _run(MissingPrefLabelCheck, g)
    assert violations[0].severity == Severity.WARNING


# ── SKO003 ────────────────────────────────────────────────────────────────────


def test_sko003_violation_same_literal_pref_and_alt_same_concept():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.prefLabel, Literal("Foo", lang="en")))
    g.add((EX.C1, SKOS.altLabel, Literal("Foo", lang="en")))
    violations = _run(LabelDisjointnessCheck, g)
    assert any(v.check_id == "SKO003" for v in violations)


def test_sko003_no_violation_different_literals():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.prefLabel, Literal("Foo", lang="en")))
    g.add((EX.C1, SKOS.altLabel, Literal("Bar", lang="en")))
    assert _run(LabelDisjointnessCheck, g) == []


def test_sko003_no_violation_same_literal_on_different_concepts():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.prefLabel, Literal("Foo", lang="en")))
    g.add((EX.C2, RDF.type, SKOS.Concept))
    g.add((EX.C2, SKOS.prefLabel, Literal("Bar", lang="en")))
    g.add((EX.C2, SKOS.altLabel, Literal("Foo", lang="en")))
    assert _run(LabelDisjointnessCheck, g) == []


def test_sko003_violation_subject_is_concept_uri():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.prefLabel, Literal("Foo", lang="en")))
    g.add((EX.C1, SKOS.altLabel, Literal("Foo", lang="en")))
    violations = _run(LabelDisjointnessCheck, g)
    assert violations[0].subject == EX.C1


def test_sko003_violation_pref_and_hidden_overlap():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.prefLabel, Literal("Foo", lang="en")))
    g.add((EX.C1, SKOS.hiddenLabel, Literal("Foo", lang="en")))
    violations = _run(LabelDisjointnessCheck, g)
    assert any(v.check_id == "SKO003" for v in violations)


def test_sko003_severity_is_error():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.prefLabel, Literal("Foo", lang="en")))
    g.add((EX.C1, SKOS.altLabel, Literal("Foo", lang="en")))
    violations = _run(LabelDisjointnessCheck, g)
    assert violations[0].severity == Severity.ERROR
