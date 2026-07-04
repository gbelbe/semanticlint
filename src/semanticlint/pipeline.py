"""The check pipeline for a single parsed graph.

Runs, in order: the **SHACL pass** (per-node cardinality / value constraints, via
pySHACL) and the remaining **registered Python checks** (graph-traversal and lexical
rules that SHACL does not express well). Results are filtered by the config's
``select`` / ``ignore``. Kept out of the CLI so it is directly unit-testable and
reusable by embedders.
"""

from __future__ import annotations

from rdflib import Graph

from semanticlint.checks.base import CheckConfig, Violation
from semanticlint.checks.registry import CheckRegistry
from semanticlint.detect import detect_vocab_type
from semanticlint.shacl.runner import run_shapes


def check_included(check_id: str, config: CheckConfig) -> bool:
    """Apply the config's ``select`` / ``ignore`` (exact id or prefix)."""
    if any(check_id == entry or check_id.startswith(entry) for entry in config.ignore):
        return False
    if config.select:
        return any(check_id == entry or check_id.startswith(entry) for entry in config.select)
    return True


def check_graph(graph: Graph, config: CheckConfig) -> list[Violation]:
    """Every violation for *graph*: SHACL-backed shapes + registered Python checks,
    gated to the detected vocabulary type and filtered by select/ignore."""
    vtype = detect_vocab_type(graph)
    violations = run_shapes(graph, config, vtype)
    for check_cls in CheckRegistry.for_vocab(vtype):
        violations.extend(check_cls().run(graph, config))
    return [v for v in violations if check_included(v.check_id, config)]
