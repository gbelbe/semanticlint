from __future__ import annotations

from rdflib import RDF, Graph, Literal, Namespace
from rdflib.namespace import OWL, RDFS, SKOS

from semanticlint.checks.base import CheckConfig, Severity
from semanticlint.checks.quality.metrics import (
    ClassLabelCoverageCheck,
    DefinitionCoverageCheck,
    LabelCoverageCheck,
    LanguageCoverageCheck,
    PropertyLabelCoverageCheck,
)

EX = Namespace("http://example.org/")


def _run(cls, graph, **quality_kwargs):
    config = CheckConfig(quality=quality_kwargs)
    return cls().run(graph, config)


# ── QUA001 — Label coverage ───────────────────────────────────────────────────


def test_label_coverage_full():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.prefLabel, Literal("One", lang="en")))
    assert _run(LabelCoverageCheck, g) == []


def test_label_coverage_below_threshold():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.prefLabel, Literal("One", lang="en")))
    g.add((EX.C2, RDF.type, SKOS.Concept))  # no prefLabel
    violations = _run(LabelCoverageCheck, g)
    assert any(v.check_id == "QUA001" for v in violations)


def test_label_coverage_threshold_zero():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))  # no prefLabel
    assert _run(LabelCoverageCheck, g, min_label_coverage=0.0) == []


def test_label_coverage_empty_graph():
    assert _run(LabelCoverageCheck, Graph()) == []


def test_label_coverage_severity():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    violations = _run(LabelCoverageCheck, g)
    assert violations[0].severity == Severity.WARNING


def test_label_coverage_no_subject():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    violations = _run(LabelCoverageCheck, g)
    assert violations[0].subject is None


# ── QUA002 — Definition coverage ─────────────────────────────────────────────


def test_definition_coverage_full():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.definition, Literal("Definition.", lang="en")))
    assert _run(DefinitionCoverageCheck, g, min_definition_coverage=1.0) == []


def test_definition_coverage_below_threshold():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))  # no definition
    g.add((EX.C2, RDF.type, SKOS.Concept))
    violations = _run(DefinitionCoverageCheck, g)
    assert any(v.check_id == "QUA002" for v in violations)


def test_definition_coverage_empty_graph():
    assert _run(DefinitionCoverageCheck, Graph()) == []


def test_definition_coverage_severity():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    violations = _run(DefinitionCoverageCheck, g)
    assert violations[0].severity == Severity.INFO


# ── QUA003 — Language coverage ────────────────────────────────────────────────


def test_language_coverage_all_en():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.prefLabel, Literal("One", lang="en")))
    assert _run(LanguageCoverageCheck, g) == []


def test_language_coverage_missing_en():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.prefLabel, Literal("Un", lang="fr")))  # no English
    violations = _run(LanguageCoverageCheck, g)
    assert any(v.check_id == "QUA003" for v in violations)


def test_language_coverage_missing_fr():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.prefLabel, Literal("One", lang="en")))
    violations = _run(LanguageCoverageCheck, g, languages=["fr"])
    assert any(v.check_id == "QUA003" for v in violations)


def test_language_coverage_subject_is_concept():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    violations = _run(LanguageCoverageCheck, g)
    assert violations[0].subject == EX.C1


def test_language_coverage_empty_graph():
    assert _run(LanguageCoverageCheck, Graph()) == []


def test_language_coverage_multiple_langs_both_present():
    g = Graph()
    g.add((EX.C1, RDF.type, SKOS.Concept))
    g.add((EX.C1, SKOS.prefLabel, Literal("One", lang="en")))
    g.add((EX.C1, SKOS.prefLabel, Literal("Un", lang="fr")))
    assert _run(LanguageCoverageCheck, g, languages=["en", "fr"]) == []


# ── QUA004 — Class label coverage ────────────────────────────────────────────


def test_class_label_coverage_full():
    g = Graph()
    g.add((EX.ClassA, RDF.type, OWL.Class))
    g.add((EX.ClassA, RDFS.label, Literal("Class A", lang="en")))
    assert _run(ClassLabelCoverageCheck, g) == []


def test_class_label_coverage_below_threshold():
    g = Graph()
    g.add((EX.ClassA, RDF.type, OWL.Class))
    g.add((EX.ClassA, RDFS.label, Literal("Class A", lang="en")))
    g.add((EX.ClassB, RDF.type, OWL.Class))  # no rdfs:label
    violations = _run(ClassLabelCoverageCheck, g)
    assert any(v.check_id == "QUA004" for v in violations)


def test_class_label_coverage_empty_graph():
    assert _run(ClassLabelCoverageCheck, Graph()) == []


def test_class_label_coverage_severity():
    g = Graph()
    g.add((EX.ClassA, RDF.type, OWL.Class))
    violations = _run(ClassLabelCoverageCheck, g)
    assert violations[0].severity == Severity.WARNING


# ── QUA005 — Property label coverage ─────────────────────────────────────────


def test_property_label_coverage_full():
    g = Graph()
    g.add((EX.propA, RDF.type, OWL.ObjectProperty))
    g.add((EX.propA, RDFS.label, Literal("Prop A", lang="en")))
    assert _run(PropertyLabelCoverageCheck, g) == []


def test_property_label_coverage_below_threshold():
    g = Graph()
    g.add((EX.propA, RDF.type, OWL.ObjectProperty))
    g.add((EX.propA, RDFS.label, Literal("Prop A", lang="en")))
    g.add((EX.propB, RDF.type, OWL.DatatypeProperty))  # no rdfs:label
    violations = _run(PropertyLabelCoverageCheck, g)
    assert any(v.check_id == "QUA005" for v in violations)


def test_property_label_coverage_empty_graph():
    assert _run(PropertyLabelCoverageCheck, Graph()) == []


def test_property_label_coverage_severity():
    g = Graph()
    g.add((EX.propA, RDF.type, OWL.ObjectProperty))
    violations = _run(PropertyLabelCoverageCheck, g)
    assert violations[0].severity == Severity.WARNING
