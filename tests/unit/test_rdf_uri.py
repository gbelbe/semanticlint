from __future__ import annotations

import pytest
from rdflib import RDF, Graph
from rdflib.namespace import OWL, RDFS, SKOS
from rdflib.term import URIRef

from semanticlint.checks.base import CheckConfig, Severity
from semanticlint.checks.rdf.uris import (
    BaseURIConsistencyCheck,
    DuplicateEntityURICheck,
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


def test_rdf003_no_violation_single_hash_fragment():
    g = Graph()
    g.add((URIRef("http://example.org/vocab#C1"), RDF.type, SKOS.Concept))
    assert _run(MalformedURICheck, g) == []


def test_rdf003_violation_two_hash_fragments():
    g = Graph()
    g.add((URIRef("http://example.org/vocab#a#b"), RDF.type, SKOS.Concept))
    violations = _run(MalformedURICheck, g)
    assert any(v.check_id == "RDF003" for v in violations)


def test_rdf003_violation_url_pasted_into_fragment():
    # Real-world case: a whole Google-Slides URL crammed into the fragment —
    # two '#' separators, structurally invalid per RFC 3986.
    g = Graph()
    bad = URIRef(
        "https://ontology.adeo.com/kai-internal-knowledge#"
        "https://docs.google.com/presentation/d/1oKfiFcyb/edit#slide=id.g3e8"
    )
    g.add((bad, RDF.type, SKOS.Concept))
    violations = _run(MalformedURICheck, g)
    assert any(v.check_id == "RDF003" and v.subject == bad for v in violations)


# ── RDF003: full RFC 3986 grammar validation ──────────────────────────────────

# Well-formed URIs/IRIs of every shape must pass untouched (no false positives).
_WELL_FORMED_URIS = [
    "http://example.org/C1",
    "https://ex.org/vocab#Concept",
    "http://www.w3.org/2002/07/owl#Class",
    "http://purl.org/dc/terms/",
    "urn:uuid:6e8bc430-9c3a-11d9-9669-0800200c9a66",
    "file:///example/C1",
    "http://ex.org/x?a=1&b=2#frag",
    "http://ex.org/p%C3%A9rignon",  # valid percent-encoding
    "http://例え.jp/資源#概念",  # internationalised IRI (RFC 3987 ucschar)
    "mailto:user@example.com",
    "tag:example.com,2024:thing",
    "http://[2001:db8::1]:8080/x",  # IPv6 host literal + port
]

# Structurally invalid identifiers the RFC grammar rejects.
_MALFORMED_URIS = [
    "http://example.org/my concept",  # space
    "http://example.org/a\x01b",  # control character
    "http://example.org/<foo>",  # angle brackets
    "http://ex.org/a{b}",  # braces
    "http://ex.org/a|b",  # pipe
    "http://ex.org/a`b",  # backtick
    'http://ex.org/a"b',  # double quote
    "http://ex.org/%zz",  # non-hex percent-encoding
    "http://ex.org/%1",  # truncated percent-encoding
    "http://ex.org/vocab#a#b",  # two fragment separators
    "not a uri at all",  # no scheme
]


@pytest.mark.parametrize("uri", _WELL_FORMED_URIS)
def test_rdf003_well_formed_uri_never_flagged(uri):
    g = Graph()
    g.add((URIRef(uri), RDF.type, SKOS.Concept))
    assert _run(MalformedURICheck, g) == [], uri


@pytest.mark.parametrize("uri", _MALFORMED_URIS)
def test_rdf003_malformed_uri_is_flagged(uri):
    g = Graph()
    bad = URIRef(uri)
    g.add((bad, RDF.type, SKOS.Concept))
    violations = _run(MalformedURICheck, g)
    assert any(v.check_id == "RDF003" and v.subject == bad for v in violations), uri


def test_rdf003_reports_invalid_percent_encoding_reason():
    g = Graph()
    g.add((URIRef("http://ex.org/%zz"), RDF.type, SKOS.Concept))
    violations = _run(MalformedURICheck, g)
    assert any("percent-encoding" in v.message for v in violations)


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


# ── RDF007: duplicate entity URI ──────────────────────────────────────────────

_NI = OWL.NamedIndividual


def _typed(*types):
    g = Graph()
    for t in types:
        g.add((URIRef("http://example.org/X"), RDF.type, t))
    return g


def test_rdf007_no_violation_single_type():
    assert _run(DuplicateEntityURICheck, _typed(SKOS.Concept)) == []


def test_rdf007_no_violation_concept_class_pun():
    assert _run(DuplicateEntityURICheck, _typed(SKOS.Concept, OWL.Class)) == []


def test_rdf007_no_violation_class_individual_pun():
    assert _run(DuplicateEntityURICheck, _typed(OWL.Class, _NI)) == []


def test_rdf007_no_violation_property_subtype_pun():
    # An Object+Annotation property is one 'property' bucket, not cross-entity duplication.
    assert _run(DuplicateEntityURICheck, _typed(OWL.ObjectProperty, OWL.AnnotationProperty)) == []


def test_rdf007_violation_concept_and_property():
    violations = _run(DuplicateEntityURICheck, _typed(SKOS.Concept, OWL.ObjectProperty))
    assert any(v.check_id == "RDF007" for v in violations)


def test_rdf007_violation_individual_and_property():
    violations = _run(DuplicateEntityURICheck, _typed(_NI, OWL.DatatypeProperty))
    assert any(v.check_id == "RDF007" for v in violations)


def test_rdf007_violation_concept_and_individual():
    violations = _run(DuplicateEntityURICheck, _typed(SKOS.Concept, _NI))
    assert any(v.check_id == "RDF007" for v in violations)


def test_rdf007_violation_three_entity_types():
    violations = _run(DuplicateEntityURICheck, _typed(SKOS.Concept, OWL.Class, _NI))
    assert any(v.check_id == "RDF007" for v in violations)


def test_rdf007_violation_is_an_error_pointing_at_the_uri():
    violations = _run(DuplicateEntityURICheck, _typed(SKOS.Concept, OWL.ObjectProperty))
    v = next(v for v in violations if v.check_id == "RDF007")
    assert v.severity == Severity.ERROR
    assert v.subject == URIRef("http://example.org/X")


def test_rdf007_no_violation_for_rdfs_class_and_owl_class():
    # Both collapse to the 'class' bucket → one entity, no duplication.
    assert _run(DuplicateEntityURICheck, _typed(RDFS.Class, OWL.Class)) == []
