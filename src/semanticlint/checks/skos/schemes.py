from __future__ import annotations

from rdflib import Graph
from rdflib.namespace import SKOS

from semanticlint.checks.base import Check, CheckConfig, Severity, Violation, VocabType
from semanticlint.checks.registry import CheckRegistry


@CheckRegistry.register
class TopConceptInSchemeCheck(Check):
    id = "SKO020"
    description = "If C skos:topConceptOf S then C must also assert skos:inScheme S (W3C SKOS S46)"
    severity = Severity.ERROR
    applies_to = VocabType.SKOS

    def run(self, graph: Graph, config: CheckConfig) -> list[Violation]:
        violations = []
        for concept, _, scheme in graph.triples((None, SKOS.topConceptOf, None)):
            if (concept, SKOS.inScheme, scheme) not in graph:
                violations.append(
                    Violation(
                        self.id,
                        f"Concept is skos:topConceptOf <{scheme}> but not skos:inScheme <{scheme}>",
                        self.severity,
                        subject=concept,  # type: ignore[arg-type]
                    )
                )
        return violations


@CheckRegistry.register
class TopConceptAlignmentCheck(Check):
    id = "SKO021"
    description = (
        "skos:hasTopConcept and skos:topConceptOf must be mutually asserted (W3C SKOS S36/S37)"
    )
    severity = Severity.WARNING
    applies_to = VocabType.SKOS

    def run(self, graph: Graph, config: CheckConfig) -> list[Violation]:
        violations = []
        for scheme, _, concept in graph.triples((None, SKOS.hasTopConcept, None)):
            if (concept, SKOS.topConceptOf, scheme) not in graph:
                violations.append(
                    Violation(
                        self.id,
                        f"Scheme has skos:hasTopConcept <{concept}> but that concept"
                        " does not assert skos:topConceptOf",
                        self.severity,
                        subject=scheme,  # type: ignore[arg-type]
                    )
                )
        for concept, _, scheme in graph.triples((None, SKOS.topConceptOf, None)):
            if (scheme, SKOS.hasTopConcept, concept) not in graph:
                violations.append(
                    Violation(
                        self.id,
                        f"Concept asserts skos:topConceptOf <{scheme}> but that scheme"
                        " does not assert skos:hasTopConcept",
                        self.severity,
                        subject=concept,  # type: ignore[arg-type]
                    )
                )
        return violations
