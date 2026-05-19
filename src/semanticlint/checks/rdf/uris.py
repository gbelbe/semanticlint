from __future__ import annotations

import re

from rdflib import RDF, Graph
from rdflib.namespace import OWL, RDFS
from rdflib.namespace import SKOS as SKOS_NS
from rdflib.term import URIRef

from semanticlint.checks.base import Check, CheckConfig, Severity, Violation, VocabType
from semanticlint.checks.registry import CheckRegistry

_MALFORMED_CHARS = re.compile(r"[ <>\x00-\x1f\x7f]")

_EXTERNAL_PREFIXES = (
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "http://www.w3.org/2000/01/rdf-schema#",
    "http://www.w3.org/2002/07/owl#",
    "http://www.w3.org/2004/02/skos/core#",
    "http://www.w3.org/2001/XMLSchema#",
    "http://purl.org/dc/elements/1.1/",
    "http://purl.org/dc/terms/",
    "http://xmlns.com/foaf/0.1/",
    "http://schema.org/",
    "https://schema.org/",
    "http://www.w3.org/ns/prov#",
    "http://rdfs.org/ns/void#",
    "http://purl.org/vocab/vann/",
)

# These declare the vocabulary itself — their URIs are the namespace anchors.
_ANCHOR_TYPES = (OWL.Ontology, SKOS_NS.ConceptScheme)

# These are entities *within* the vocabulary.
_LEAF_ENTITY_TYPES = (
    SKOS_NS.Concept,
    OWL.Class,
    OWL.NamedIndividual,
    OWL.ObjectProperty,
    OWL.DatatypeProperty,
    RDFS.Class,
)


def _is_external(uri: str) -> bool:
    return any(uri.startswith(p) for p in _EXTERNAL_PREFIXES)


def _typed_subjects(graph: Graph, *types: URIRef) -> list[URIRef]:
    entities: set[URIRef] = set()
    for etype in types:
        for s in graph.subjects(RDF.type, etype):
            if isinstance(s, URIRef):
                entities.add(s)
    return list(entities)


def _normalize_base(uri: str) -> str:
    return uri.rstrip("#/")


def _matches_base(entity_uri: str, base: str) -> bool:
    nb = _normalize_base(base)
    return entity_uri == nb or entity_uri.startswith(nb + "#") or entity_uri.startswith(nb + "/")


@CheckRegistry.register
class MalformedURICheck(Check):
    id = "RDF003"
    description = "URI contains illegal characters (spaces, angle brackets, control characters)"
    severity = Severity.ERROR
    applies_to = VocabType.RDF

    def run(self, graph: Graph, config: CheckConfig) -> list[Violation]:
        violations = []
        seen: set[URIRef] = set()
        for s, _, o in graph:
            for node in (s, o):
                if not isinstance(node, URIRef) or node in seen:
                    continue
                seen.add(node)
                uri = str(node)
                if _MALFORMED_CHARS.search(uri):
                    violations.append(
                        Violation(
                            self.id,
                            f"URI contains illegal characters: <{uri}>",
                            self.severity,
                            subject=node,
                        )
                    )
        return violations


@CheckRegistry.register
class NonHttpURICheck(Check):
    id = "RDF004"
    description = "Vocabulary-defined entities should use HTTP or HTTPS URIs"
    severity = Severity.WARNING
    applies_to = VocabType.RDF

    def run(self, graph: Graph, config: CheckConfig) -> list[Violation]:
        violations = []
        for entity in _typed_subjects(graph, *_ANCHOR_TYPES, *_LEAF_ENTITY_TYPES):
            uri = str(entity)
            if _is_external(uri):
                continue
            if not (uri.startswith("http://") or uri.startswith("https://")):
                violations.append(
                    Violation(
                        self.id,
                        f"Vocabulary entity uses a non-HTTP/HTTPS URI scheme: <{uri}>",
                        self.severity,
                        subject=entity,
                    )
                )
        return violations


@CheckRegistry.register
class InconsistentSeparatorCheck(Check):
    id = "RDF005"
    description = (
        "Vocabulary entities should use a consistent URI separator (# or /)"
        " within the same namespace"
    )
    severity = Severity.WARNING
    applies_to = VocabType.RDF

    def run(self, graph: Graph, config: CheckConfig) -> list[Violation]:
        entities = [
            e for e in _typed_subjects(graph, *_LEAF_ENTITY_TYPES) if not _is_external(str(e))
        ]
        if len(entities) < 2:
            return []

        hash_uris = [e for e in entities if "#" in str(e)]
        slash_uris = [e for e in entities if "#" not in str(e) and "/" in str(e)]

        if not hash_uris or not slash_uris:
            return []

        # Flag the minority; hash loses ties so the more common slash pattern is preferred.
        if len(hash_uris) <= len(slash_uris):
            minority, majority_sep = hash_uris, "/"
        else:
            minority, majority_sep = slash_uris, "#"

        minority_sep = "#" if majority_sep == "/" else "/"
        return [
            Violation(
                self.id,
                f"URI uses '{minority_sep}' separator but the majority of vocabulary"
                f" entities use '{majority_sep}'",
                self.severity,
                subject=uri,
            )
            for uri in minority
        ]


@CheckRegistry.register
class BaseURIConsistencyCheck(Check):
    id = "RDF006"
    description = (
        "Vocabulary entities should share the base URI of the declared ontology or concept scheme"
    )
    severity = Severity.WARNING
    applies_to = VocabType.RDF

    def run(self, graph: Graph, config: CheckConfig) -> list[Violation]:
        anchors = _typed_subjects(graph, *_ANCHOR_TYPES)
        if not anchors:
            return []
        bases = [str(a) for a in anchors]
        anchor_set = set(anchors)

        violations = []
        for entity in _typed_subjects(graph, *_LEAF_ENTITY_TYPES):
            if entity in anchor_set:
                continue
            uri = str(entity)
            if _is_external(uri):
                continue
            if not any(_matches_base(uri, base) for base in bases):
                violations.append(
                    Violation(
                        self.id,
                        f"Entity URI does not share the base of any declared"
                        f" ontology or concept scheme: <{uri}>",
                        self.severity,
                        subject=entity,
                    )
                )
        return violations
