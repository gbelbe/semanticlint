from __future__ import annotations

from rdflib import RDF, Graph
from rdflib.namespace import SKOS
from rdflib.term import URIRef

from semanticlint.checks.base import Check, CheckConfig, Severity, Violation, VocabType
from semanticlint.checks.registry import CheckRegistry


def _find_broader_cycles(graph: Graph) -> set[URIRef]:
    """Return all concept URIs involved in a skos:broader cycle.

    Uses an iterative DFS with three-colour marking (white/gray/black) and
    explicit path tracking so that every node in a cycle is flagged.
    """
    adj: dict[URIRef, set[URIRef]] = {}
    for s, _, o in graph.triples((None, SKOS.broader, None)):
        adj.setdefault(s, set()).add(o)  # type: ignore[arg-type]

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[URIRef, int] = {}
    in_cycle: set[URIRef] = set()

    for start in list(adj):
        if color.get(start, WHITE) != WHITE:
            continue

        stack: list[tuple[URIRef, object]] = [(start, iter(adj.get(start, set())))]
        path: list[URIRef] = [start]
        path_set: set[URIRef] = {start}
        color[start] = GRAY

        while stack:
            node, children = stack[-1]
            try:
                child = next(children)  # type: ignore[call-overload]
                state = color.get(child, WHITE)
                if state == GRAY:
                    idx = path.index(child)
                    for n in path[idx:]:
                        in_cycle.add(n)
                elif state == WHITE:
                    color[child] = GRAY
                    path.append(child)
                    path_set.add(child)
                    stack.append((child, iter(adj.get(child, set()))))
            except StopIteration:
                stack.pop()
                color[node] = BLACK
                if path and path[-1] == node:
                    path.pop()
                    path_set.discard(node)

    return in_cycle


@CheckRegistry.register
class BroaderCycleCheck(Check):
    id = "SKO010"
    description = "No cycles allowed in the skos:broader hierarchy"
    severity = Severity.ERROR
    applies_to = VocabType.SKOS

    def run(self, graph: Graph, config: CheckConfig) -> list[Violation]:
        return [
            Violation(
                self.id,
                "Concept is part of a cycle in the skos:broader hierarchy",
                self.severity,
                subject=concept,  # type: ignore[arg-type]
            )
            for concept in _find_broader_cycles(graph)
        ]


@CheckRegistry.register
class OrphanConceptCheck(Check):
    id = "SKO011"
    description = (
        "Concept has no skos:broader and is not declared as a top concept"
        " via skos:topConceptOf or skos:hasTopConcept"
    )
    severity = Severity.WARNING
    applies_to = VocabType.SKOS

    def run(self, graph: Graph, config: CheckConfig) -> list[Violation]:
        violations = []
        for concept in graph.subjects(RDF.type, SKOS.Concept):
            has_broader = any(graph.objects(concept, SKOS.broader))
            is_top_concept_of = any(graph.objects(concept, SKOS.topConceptOf))
            is_declared_top = any(graph.subjects(SKOS.hasTopConcept, concept))
            if not has_broader and not is_top_concept_of and not is_declared_top:
                violations.append(
                    Violation(
                        self.id,
                        "Concept has no skos:broader and is not declared as a top concept",
                        self.severity,
                        subject=concept,  # type: ignore[arg-type]
                    )
                )
        return violations
