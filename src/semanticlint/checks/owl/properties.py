from __future__ import annotations

from rdflib import RDF, Graph
from rdflib.namespace import OWL

from semanticlint.checks.base import Check, CheckConfig, Severity, Violation, VocabType
from semanticlint.checks.registry import CheckRegistry

# OWL001 (rdfs:domain) and OWL002 (rdfs:range) are now expressed as SHACL shapes
# (semanticlint/shacl/shapes/owl_properties.ttl) and run via pySHACL — see
# semanticlint.shacl.runner. Only the non-cardinality OWL003 remains hand-written.


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
