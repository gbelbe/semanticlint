from __future__ import annotations

from pathlib import Path

from rdflib import Graph
from rdflib.util import guess_format

from semanticlint.checks.base import Severity, Violation


def lint_syntax(path: Path, fmt: str | None = None) -> tuple[Graph | None, list[Violation]]:
    """Parse *path* and return ``(graph, violations)``.

    ``RDF001`` — parse error (graph is ``None``).
    ``RDF002`` — file parsed but produced an empty graph (warning).
    No violations and a populated graph on success.
    """
    location = str(path)
    effective_fmt = fmt or guess_format(str(path)) or "turtle"

    g = Graph()
    try:
        g.parse(str(path), format=effective_fmt)
    except Exception as exc:
        return None, [Violation("RDF001", str(exc), Severity.ERROR, location=location)]

    if len(g) == 0:
        return g, [
            Violation(
                "RDF002",
                "File produces an empty graph — no triples were parsed.",
                Severity.WARNING,
                location=location,
            )
        ]

    return g, []
