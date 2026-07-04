from __future__ import annotations

from rdflib import RDF, Graph
from rdflib.namespace import OWL, RDFS

from semanticlint.checks.base import Check, CheckConfig, Severity, Violation, VocabType
from semanticlint.checks.registry import CheckRegistry

# RDS001 (every class needs an rdfs:label) is now a SHACL shape
# (semanticlint/shacl/shapes/rdfs_classes.ttl), run via pySHACL — see
# semanticlint.shacl.runner. RDS002 stays hand-written (referential integrity).

# Well-known foundational superclasses that are always valid targets for
# rdfs:subClassOf even when not explicitly declared in the graph.
_FOUNDATIONAL: frozenset = frozenset({OWL.Thing, OWL.Nothing, RDFS.Resource, RDFS.Literal})


@CheckRegistry.register
class UndeclaredSuperclassCheck(Check):
    id = "RDS002"
    description = (
        "rdfs:subClassOf should only reference classes declared in the graph"
        " (foundational classes such as owl:Thing are exempt)"
    )
    severity = Severity.WARNING
    applies_to = VocabType.RDFS | VocabType.OWL

    def run(self, graph: Graph, config: CheckConfig) -> list[Violation]:
        declared = set(graph.subjects(RDF.type, OWL.Class)) | set(
            graph.subjects(RDF.type, RDFS.Class)
        )
        violations = []
        for sub, _, super_cls in graph.triples((None, RDFS.subClassOf, None)):
            if super_cls in _FOUNDATIONAL or super_cls in declared:
                continue
            violations.append(
                Violation(
                    self.id,
                    f"rdfs:subClassOf references undeclared class <{super_cls}>",
                    self.severity,
                    subject=sub,  # type: ignore[arg-type]
                )
            )
        return violations
