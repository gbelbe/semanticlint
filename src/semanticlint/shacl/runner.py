"""Run SHACL shapes through pySHACL and map results back to semanticlint Violations.

Per-node cardinality / value constraints (a class needs an ``rdfs:label``, a property
needs an ``rdfs:domain``, …) are expressed as SHACL shapes under ``shapes/`` rather than
hand-written Python — the standard, reusable way. Each shape is annotated with
``slint:checkId`` and ``slint:appliesTo`` so a ``sh:ValidationResult`` maps back to the
right semanticlint check id and vocabulary applicability. pySHACL runs **once** over the
combined shapes graph; results are then dispatched, vocab-gated and turned into
``Violation``s — keeping the whole library behind this one adapter.
"""

from __future__ import annotations

from functools import lru_cache
from importlib import resources

from pyshacl import validate
from rdflib import RDF, Graph, Namespace
from rdflib.namespace import SH
from rdflib.term import Node

from semanticlint.checks.base import CheckConfig, Severity, Violation, VocabType
from semanticlint.detect import detect_vocab_type

SLINT = Namespace("https://semanticlint.org/ns#")

_SEVERITY: dict[Node, Severity] = {
    SH.Violation: Severity.ERROR,
    SH.Warning: Severity.WARNING,
    SH.Info: Severity.INFO,
}
_VOCAB = {
    "RDF": VocabType.RDF,
    "RDFS": VocabType.RDFS,
    "OWL": VocabType.OWL,
    "SKOS": VocabType.SKOS,
}


@lru_cache(maxsize=1)
def _shapes() -> Graph:
    """The combined built-in shapes graph (parsed once)."""
    graph = Graph()
    shapes_dir = resources.files("semanticlint.shacl") / "shapes"
    for entry in shapes_dir.iterdir():
        if entry.name.endswith(".ttl"):
            graph.parse(data=entry.read_text(encoding="utf-8"), format="turtle")
    return graph


def _annotated_shape(shapes: Graph, source: Node | None) -> Node | None:
    """The NodeShape carrying ``slint:checkId`` for a result's ``sh:sourceShape``.

    A property-constraint result points at the (blank) property shape; its parent
    NodeShape holds the annotation. A node-level constraint points at the NodeShape
    itself.
    """
    if source is None:
        return None
    if (source, SLINT.checkId, None) in shapes:
        return source
    return shapes.value(predicate=SH.property, object=source)


def _applies_to(shapes: Graph, shape: Node) -> VocabType:
    flags = VocabType(0)
    for obj in shapes.objects(shape, SLINT.appliesTo):
        flags |= _VOCAB.get(str(obj), VocabType(0))
    return flags


def run_shapes(
    graph: Graph, config: CheckConfig, vtype: VocabType | None = None
) -> list[Violation]:
    """Validate *graph* against the built-in SHACL shapes and return Violations.

    Only shapes whose ``slint:appliesTo`` overlaps the graph's detected vocabulary
    type fire — mirroring the ``for_vocab`` gating of the Python checks. ``config`` is
    accepted for parity with the check interface (select/ignore are applied by the
    caller / pipeline).
    """
    if vtype is None:
        vtype = detect_vocab_type(graph)
    shapes = _shapes()
    _, results, _ = validate(graph, shacl_graph=shapes, inference="none")

    violations: list[Violation] = []
    for result in results.subjects(RDF.type, SH.ValidationResult):
        shape = _annotated_shape(shapes, results.value(result, SH.sourceShape))
        if shape is None:
            continue
        check_id = shapes.value(shape, SLINT.checkId)
        if check_id is None or not (_applies_to(shapes, shape) & vtype):
            continue
        sev_node = results.value(result, SH.resultSeverity)
        severity = _SEVERITY.get(sev_node, Severity.WARNING) if sev_node else Severity.WARNING
        violations.append(
            Violation(
                str(check_id),
                str(results.value(result, SH.resultMessage) or ""),
                severity,
                subject=results.value(result, SH.focusNode),  # type: ignore[arg-type]
            )
        )
    return violations
