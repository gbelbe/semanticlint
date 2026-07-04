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
from rdflib import RDF, Graph, Namespace, URIRef
from rdflib.namespace import SH
from rdflib.term import Node

from semanticlint.checks.base import CheckConfig, Severity, Violation, VocabType
from semanticlint.detect import detect_vocab_type
from semanticlint.shacl.builder import build_config_shapes

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
    """The NodeShape a result's ``sh:sourceShape`` belongs to.

    A property-constraint result points at the (blank) property shape; its parent
    NodeShape is returned. A node-level constraint points at the NodeShape itself.
    """
    if source is None:
        return None
    parent = shapes.value(predicate=SH.property, object=source)
    return parent if parent is not None else source


def _local_name(node: Node) -> str:
    text = str(node)
    for sep in ("#", "/"):
        if sep in text:
            return text.rsplit(sep, 1)[-1]
    return text


def _check_id(shapes: Graph, shape: Node) -> str:
    """The check id for *shape*: its ``slint:checkId`` (built-in / opt-in), else the
    shape's URI local name (local business shapes need no annotation), else ``SHACL``."""
    declared = shapes.value(shape, SLINT.checkId)
    if declared is not None:
        return str(declared)
    return _local_name(shape) if isinstance(shape, URIRef) else "SHACL"


def _shape_applies(shapes: Graph, shape: Node, vtype: VocabType) -> bool:
    """Whether *shape* fires for the graph's vocabulary. Built-in shapes declare
    ``slint:appliesTo`` and are gated by it; a shape with no declaration (a local
    business rule) always applies — its SHACL targets already gate relevance."""
    declared = list(shapes.objects(shape, SLINT.appliesTo))
    if not declared:
        return True
    flags = VocabType(0)
    for obj in declared:
        flags |= _VOCAB.get(str(obj), VocabType(0))
    return bool(flags & vtype)


def run_shapes(
    graph: Graph,
    config: CheckConfig,
    vtype: VocabType | None = None,
    extra_shapes: Graph | None = None,
) -> list[Violation]:
    """Validate *graph* against the built-in shapes plus any *extra_shapes* (discovered
    local business rules), returning Violations.

    Built-in shapes are vocab-gated by ``slint:appliesTo``; local shapes apply always
    (targets gate them) and take their id from ``slint:checkId`` or their shape name.
    ``config`` supplies config-driven shapes (e.g. QUA003 languages); select/ignore are
    applied by the caller / pipeline.
    """
    if vtype is None:
        vtype = detect_vocab_type(graph)
    shapes = Graph()
    shapes += _shapes()  # built-in static shapes (cached; copied, not mutated)
    shapes += build_config_shapes(config)  # config-driven shapes (e.g. QUA003 languages)
    if extra_shapes is not None:
        shapes += extra_shapes  # discovered local *.shapes.ttl business rules
    _, results, _ = validate(graph, shacl_graph=shapes, inference="none")

    nested = set(results.objects(None, SH.detail))  # sub-results of sh:node etc. — skip
    violations: list[Violation] = []
    for result in results.subjects(RDF.type, SH.ValidationResult):
        if result in nested:
            continue
        shape = _annotated_shape(shapes, results.value(result, SH.sourceShape))
        if shape is None or not _shape_applies(shapes, shape, vtype):
            continue
        sev_node = results.value(result, SH.resultSeverity)
        severity = _SEVERITY.get(sev_node, Severity.WARNING) if sev_node else Severity.WARNING
        violations.append(
            Violation(
                _check_id(shapes, shape),
                _message(results, result),
                severity,
                subject=_focus(results, result),  # type: ignore[arg-type]
            )
        )
    return violations


def _focus(results: Graph, result: Node) -> Node | None:
    return results.value(result, SH.focusNode)


def _message(results: Graph, result: Node) -> str:
    """The result message, with the offending value appended when the result carries one
    (``sh:value``) — e.g. RDS002's undeclared class URI, matching the legacy wording."""
    message = str(results.value(result, SH.resultMessage) or "")
    offending = results.value(result, SH.value)
    return f"{message} <{offending}>" if offending is not None else message
