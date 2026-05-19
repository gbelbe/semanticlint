from __future__ import annotations

from rdflib import RDF, Graph
from rdflib.namespace import OWL, SKOS
from rdflib.term import URIRef

from semanticlint.checks.base import CheckConfig, Severity
from semanticlint.checks.rdf.uris import (
    BaseURIConsistencyCheck,
    InconsistentSeparatorCheck,
    MalformedURICheck,
    NonHttpURICheck,
)


def _run(check_cls, graph):
    return check_cls().run(graph, CheckConfig())


# ── RDF003 ────────────────────────────────────────────────────────────────────


def test_rdf003_no_violation_clean_http_uri():
    g = Graph()
    g.add((URIRef("http://example.org/C1"), RDF.type, SKOS.Concept))
    assert _run(MalformedURICheck, g) == []


def test_rdf003_violation_uri_with_space():
    g = Graph()
    g.add((URIRef("http://example.org/my concept"), RDF.type, SKOS.Concept))
    violations = _run(MalformedURICheck, g)
    assert any(v.check_id == "RDF003" for v in violations)


def test_rdf003_violation_uri_with_control_char():
    g = Graph()
    g.add((URIRef("http://example.org/a\x01b"), RDF.type, SKOS.Concept))
    violations = _run(MalformedURICheck, g)
    assert any(v.check_id == "RDF003" for v in violations)


def test_rdf003_violation_uri_with_angle_bracket():
    g = Graph()
    g.add((URIRef("http://example.org/<foo>"), RDF.type, SKOS.Concept))
    violations = _run(MalformedURICheck, g)
    assert any(v.check_id == "RDF003" for v in violations)


def test_rdf003_subject_is_the_offending_uri():
    g = Graph()
    bad = URIRef("http://example.org/my concept")
    g.add((bad, RDF.type, SKOS.Concept))
    violations = _run(MalformedURICheck, g)
    assert any(v.subject == bad for v in violations)


def test_rdf003_severity_is_error():
    g = Graph()
    g.add((URIRef("http://example.org/my concept"), RDF.type, SKOS.Concept))
    violations = _run(MalformedURICheck, g)
    assert violations[0].severity == Severity.ERROR


def test_rdf003_no_violation_empty_graph():
    assert _run(MalformedURICheck, Graph()) == []


def test_rdf003_object_uriref_also_checked():
    g = Graph()
    bad = URIRef("http://example.org/my concept")
    g.add((URIRef("http://example.org/C1"), RDF.type, bad))
    violations = _run(MalformedURICheck, g)
    assert any(v.check_id == "RDF003" for v in violations)


# ── RDF004 ────────────────────────────────────────────────────────────────────


def test_rdf004_no_violation_http_concept():
    g = Graph()
    g.add((URIRef("http://example.org/C1"), RDF.type, SKOS.Concept))
    assert _run(NonHttpURICheck, g) == []


def test_rdf004_no_violation_https_concept():
    g = Graph()
    g.add((URIRef("https://example.org/C1"), RDF.type, SKOS.Concept))
    assert _run(NonHttpURICheck, g) == []


def test_rdf004_violation_urn_concept():
    g = Graph()
    urn = URIRef("urn:example:C1")
    g.add((urn, RDF.type, SKOS.Concept))
    violations = _run(NonHttpURICheck, g)
    assert any(v.check_id == "RDF004" for v in violations)


def test_rdf004_violation_file_concept():
    g = Graph()
    file_uri = URIRef("file:///example/C1")
    g.add((file_uri, RDF.type, SKOS.Concept))
    violations = _run(NonHttpURICheck, g)
    assert any(v.check_id == "RDF004" for v in violations)


def test_rdf004_owl_external_entity_not_flagged():
    g = Graph()
    g.add((OWL.Class, RDF.type, OWL.Class))
    assert _run(NonHttpURICheck, g) == []


def test_rdf004_severity_is_warning():
    g = Graph()
    g.add((URIRef("urn:example:C1"), RDF.type, SKOS.Concept))
    violations = _run(NonHttpURICheck, g)
    assert violations[0].severity == Severity.WARNING


def test_rdf004_subject_is_offending_uri():
    g = Graph()
    urn = URIRef("urn:example:C1")
    g.add((urn, RDF.type, SKOS.Concept))
    violations = _run(NonHttpURICheck, g)
    assert violations[0].subject == urn


def test_rdf004_no_violation_empty_graph():
    assert _run(NonHttpURICheck, Graph()) == []


def test_rdf004_violation_urn_ontology():
    g = Graph()
    urn = URIRef("urn:example:myonto")
    g.add((urn, RDF.type, OWL.Ontology))
    violations = _run(NonHttpURICheck, g)
    assert any(v.check_id == "RDF004" for v in violations)


# ── RDF005 ────────────────────────────────────────────────────────────────────


def test_rdf005_no_violation_all_hash():
    g = Graph()
    g.add((URIRef("http://example.org/vocab#C1"), RDF.type, SKOS.Concept))
    g.add((URIRef("http://example.org/vocab#C2"), RDF.type, SKOS.Concept))
    assert _run(InconsistentSeparatorCheck, g) == []


def test_rdf005_no_violation_all_slash():
    g = Graph()
    g.add((URIRef("http://example.org/vocab/C1"), RDF.type, SKOS.Concept))
    g.add((URIRef("http://example.org/vocab/C2"), RDF.type, SKOS.Concept))
    assert _run(InconsistentSeparatorCheck, g) == []


def test_rdf005_no_violation_single_concept():
    g = Graph()
    g.add((URIRef("http://example.org/vocab#C1"), RDF.type, SKOS.Concept))
    assert _run(InconsistentSeparatorCheck, g) == []


def test_rdf005_violation_mixed_hash_and_slash():
    g = Graph()
    g.add((URIRef("http://example.org/vocab/C1"), RDF.type, SKOS.Concept))
    g.add((URIRef("http://example.org/vocab/C2"), RDF.type, SKOS.Concept))
    g.add((URIRef("http://example.org/vocab#C3"), RDF.type, SKOS.Concept))
    violations = _run(InconsistentSeparatorCheck, g)
    assert any(v.check_id == "RDF005" for v in violations)


def test_rdf005_violation_subject_is_the_minority_uri():
    minority = URIRef("http://example.org/vocab#C3")
    g = Graph()
    g.add((URIRef("http://example.org/vocab/C1"), RDF.type, SKOS.Concept))
    g.add((URIRef("http://example.org/vocab/C2"), RDF.type, SKOS.Concept))
    g.add((minority, RDF.type, SKOS.Concept))
    violations = [v for v in _run(InconsistentSeparatorCheck, g) if v.check_id == "RDF005"]
    assert all(v.subject == minority for v in violations)


def test_rdf005_severity_is_warning():
    g = Graph()
    g.add((URIRef("http://example.org/vocab/C1"), RDF.type, SKOS.Concept))
    g.add((URIRef("http://example.org/vocab/C2"), RDF.type, SKOS.Concept))
    g.add((URIRef("http://example.org/vocab#C3"), RDF.type, SKOS.Concept))
    violations = _run(InconsistentSeparatorCheck, g)
    assert violations[0].severity == Severity.WARNING


def test_rdf005_no_violation_empty_graph():
    assert _run(InconsistentSeparatorCheck, Graph()) == []


def test_rdf005_scheme_uri_not_included_in_separator_check():
    g = Graph()
    # Scheme URI uses slash-style; concepts use hash-style — no false positive
    g.add((URIRef("http://example.org/tax"), RDF.type, SKOS.ConceptScheme))
    g.add((URIRef("http://example.org/tax#C1"), RDF.type, SKOS.Concept))
    g.add((URIRef("http://example.org/tax#C2"), RDF.type, SKOS.Concept))
    assert _run(InconsistentSeparatorCheck, g) == []


# ── RDF006 ────────────────────────────────────────────────────────────────────

_SCHEME = URIRef("http://example.org/tax")
_ONTO = URIRef("http://example.org/onto")


def test_rdf006_no_violation_all_concepts_under_scheme_base():
    g = Graph()
    g.add((_SCHEME, RDF.type, SKOS.ConceptScheme))
    g.add((URIRef("http://example.org/tax/C1"), RDF.type, SKOS.Concept))
    g.add((URIRef("http://example.org/tax#C2"), RDF.type, SKOS.Concept))
    assert _run(BaseURIConsistencyCheck, g) == []


def test_rdf006_violation_concept_outside_scheme_base():
    g = Graph()
    g.add((_SCHEME, RDF.type, SKOS.ConceptScheme))
    outsider = URIRef("http://other.org/C1")
    g.add((outsider, RDF.type, SKOS.Concept))
    violations = _run(BaseURIConsistencyCheck, g)
    assert any(v.check_id == "RDF006" for v in violations)


def test_rdf006_no_violation_all_classes_under_ontology_base():
    g = Graph()
    g.add((_ONTO, RDF.type, OWL.Ontology))
    g.add((URIRef("http://example.org/onto#MyClass"), RDF.type, OWL.Class))
    assert _run(BaseURIConsistencyCheck, g) == []


def test_rdf006_violation_class_outside_ontology_base():
    g = Graph()
    g.add((_ONTO, RDF.type, OWL.Ontology))
    outsider = URIRef("http://different.org/MyClass")
    g.add((outsider, RDF.type, OWL.Class))
    violations = _run(BaseURIConsistencyCheck, g)
    assert any(v.check_id == "RDF006" for v in violations)


def test_rdf006_no_violation_when_no_ontology_or_scheme_declared():
    g = Graph()
    g.add((URIRef("http://example.org/C1"), RDF.type, SKOS.Concept))
    assert _run(BaseURIConsistencyCheck, g) == []


def test_rdf006_external_namespace_entity_is_exempt():
    g = Graph()
    g.add((_SCHEME, RDF.type, SKOS.ConceptScheme))
    g.add((OWL.Class, RDF.type, OWL.Class))
    assert _run(BaseURIConsistencyCheck, g) == []


def test_rdf006_scheme_uri_itself_is_not_flagged():
    g = Graph()
    g.add((_SCHEME, RDF.type, SKOS.ConceptScheme))
    assert _run(BaseURIConsistencyCheck, g) == []


def test_rdf006_severity_is_warning():
    g = Graph()
    g.add((_SCHEME, RDF.type, SKOS.ConceptScheme))
    g.add((URIRef("http://other.org/C1"), RDF.type, SKOS.Concept))
    violations = _run(BaseURIConsistencyCheck, g)
    assert violations[0].severity == Severity.WARNING


def test_rdf006_subject_is_offending_uri():
    g = Graph()
    g.add((_SCHEME, RDF.type, SKOS.ConceptScheme))
    outsider = URIRef("http://other.org/C1")
    g.add((outsider, RDF.type, SKOS.Concept))
    violations = _run(BaseURIConsistencyCheck, g)
    assert violations[0].subject == outsider


def test_rdf006_no_violation_empty_graph():
    assert _run(BaseURIConsistencyCheck, Graph()) == []


def test_rdf006_multiple_schemes_accept_entities_under_any_base():
    g = Graph()
    scheme1 = URIRef("http://example.org/tax1")
    scheme2 = URIRef("http://example.org/tax2")
    g.add((scheme1, RDF.type, SKOS.ConceptScheme))
    g.add((scheme2, RDF.type, SKOS.ConceptScheme))
    g.add((URIRef("http://example.org/tax1/C1"), RDF.type, SKOS.Concept))
    g.add((URIRef("http://example.org/tax2/C2"), RDF.type, SKOS.Concept))
    assert _run(BaseURIConsistencyCheck, g) == []


def test_rdf006_false_positive_guard_similar_prefix():
    g = Graph()
    g.add((_ONTO, RDF.type, OWL.Ontology))
    # "http://example.org/ontological/..." starts with "http://example.org/onto"
    # but must NOT match because there is no '#' or '/' between base and suffix
    outsider = URIRef("http://example.org/ontological/MyClass")
    g.add((outsider, RDF.type, OWL.Class))
    violations = _run(BaseURIConsistencyCheck, g)
    assert any(v.check_id == "RDF006" for v in violations)
