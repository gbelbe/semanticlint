from __future__ import annotations

from rdflib import RDF, Graph
from rdflib.namespace import SKOS
from rdflib.term import Literal

from semanticlint.checks.base import Check, CheckConfig, Severity, Violation, VocabType
from semanticlint.checks.registry import CheckRegistry


@CheckRegistry.register
class DuplicatePrefLabelCheck(Check):
    id = "SKO001"
    description = "At most one skos:prefLabel per language tag per concept (W3C SKOS S13)"
    severity = Severity.ERROR
    applies_to = VocabType.SKOS

    def run(self, graph: Graph, config: CheckConfig) -> list[Violation]:
        violations = []
        for concept in graph.subjects(RDF.type, SKOS.Concept):
            counts: dict[str, int] = {}
            for label in graph.objects(concept, SKOS.prefLabel):
                if not isinstance(label, Literal):
                    continue
                lang = label.language or ""
                counts[lang] = counts.get(lang, 0) + 1
            for lang, n in counts.items():
                if n > 1:
                    display = lang if lang else "no language tag"
                    violations.append(
                        Violation(
                            self.id,
                            f"Concept has {n} skos:prefLabel values for language '{display}'",
                            self.severity,
                            subject=concept,  # type: ignore[arg-type]
                        )
                    )
        return violations


@CheckRegistry.register
class MissingPrefLabelCheck(Check):
    id = "SKO002"
    description = "Every skos:Concept should have at least one skos:prefLabel"
    severity = Severity.WARNING
    applies_to = VocabType.SKOS

    def run(self, graph: Graph, config: CheckConfig) -> list[Violation]:
        violations = []
        for concept in graph.subjects(RDF.type, SKOS.Concept):
            if not any(graph.objects(concept, SKOS.prefLabel)):
                violations.append(
                    Violation(
                        self.id,
                        "Concept has no skos:prefLabel",
                        self.severity,
                        subject=concept,  # type: ignore[arg-type]
                    )
                )
        return violations


@CheckRegistry.register
class LabelDisjointnessCheck(Check):
    id = "SKO003"
    description = (
        "skos:prefLabel, skos:altLabel and skos:hiddenLabel must be pairwise disjoint"
        " on the same concept (W3C SKOS S9)"
    )
    severity = Severity.ERROR
    applies_to = VocabType.SKOS

    def run(self, graph: Graph, config: CheckConfig) -> list[Violation]:
        violations = []
        for concept in graph.subjects(RDF.type, SKOS.Concept):
            pref = set(graph.objects(concept, SKOS.prefLabel))
            alt = set(graph.objects(concept, SKOS.altLabel))
            hidden = set(graph.objects(concept, SKOS.hiddenLabel))
            pairs = [
                (pref & alt, "skos:prefLabel", "skos:altLabel"),
                (pref & hidden, "skos:prefLabel", "skos:hiddenLabel"),
                (alt & hidden, "skos:altLabel", "skos:hiddenLabel"),
            ]
            for overlap, prop_a, prop_b in pairs:
                for literal in overlap:
                    violations.append(
                        Violation(
                            self.id,
                            f"Literal {str(literal)!r} appears as both {prop_a} and {prop_b}",
                            self.severity,
                            subject=concept,  # type: ignore[arg-type]
                        )
                    )
        return violations
