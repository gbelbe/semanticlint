from __future__ import annotations

from rdflib import RDF, Graph
from rdflib.namespace import OWL, RDFS

from semanticlint.checks.base import Check, CheckConfig, Severity, Violation, VocabType
from semanticlint.checks.registry import CheckRegistry


def _properties(graph: Graph) -> set:
    return set(graph.subjects(RDF.type, OWL.ObjectProperty)) | set(
        graph.subjects(RDF.type, OWL.DatatypeProperty)
    )


@CheckRegistry.register
class PropertyDomainCheck(Check):
    id = "OWL001"
    description = "Every owl:ObjectProperty and owl:DatatypeProperty should declare rdfs:domain"
    severity = Severity.WARNING
    applies_to = VocabType.OWL

    def run(self, graph: Graph, config: CheckConfig) -> list[Violation]:
        return [
            Violation(
                self.id,
                "Property has no rdfs:domain",
                self.severity,
                subject=prop,  # type: ignore[arg-type]
            )
            for prop in _properties(graph)
            if not any(graph.objects(prop, RDFS.domain))
        ]


@CheckRegistry.register
class PropertyRangeCheck(Check):
    id = "OWL002"
    description = "Every owl:ObjectProperty and owl:DatatypeProperty should declare rdfs:range"
    severity = Severity.WARNING
    applies_to = VocabType.OWL

    def run(self, graph: Graph, config: CheckConfig) -> list[Violation]:
        return [
            Violation(
                self.id,
                "Property has no rdfs:range",
                self.severity,
                subject=prop,  # type: ignore[arg-type]
            )
            for prop in _properties(graph)
            if not any(graph.objects(prop, RDFS.range))
        ]


@CheckRegistry.register
class UntypedIndividualCheck(Check):
    id = "OWL003"
    description = "Every owl:NamedIndividual should be typed to at least one domain class"
    severity = Severity.WARNING
    applies_to = VocabType.OWL

    def run(self, graph: Graph, config: CheckConfig) -> list[Violation]:
        violations = []
        for individual in graph.subjects(RDF.type, OWL.NamedIndividual):
            other_types = [
                t for t in graph.objects(individual, RDF.type) if t != OWL.NamedIndividual
            ]
            if not other_types:
                violations.append(
                    Violation(
                        self.id,
                        "NamedIndividual has no domain class type beyond owl:NamedIndividual",
                        self.severity,
                        subject=individual,  # type: ignore[arg-type]
                    )
                )
        return violations
