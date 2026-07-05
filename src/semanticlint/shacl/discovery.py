"""Discovery of local, project-owned SHACL shapes.

Business rules that are specific to one vocabulary live in a ``*.shapes.ttl`` file
committed **next to the ontology** it constrains. semanticlint finds these
automatically and unions them into validation: a sibling file for a single-file
check, the whole tree for a directory check. Shapes files are never themselves
validated as data (see :func:`is_shapes_file`).
"""

from __future__ import annotations

from pathlib import Path

from rdflib import Graph

SHAPES_SUFFIX = ".shapes.ttl"


def is_shapes_file(path: Path) -> bool:
    """Whether *path* is a local shapes file (``*.shapes.ttl``) rather than data."""
    return path.name.endswith(SHAPES_SUFFIX)


def discover_shapes_files(path: Path) -> list[Path]:
    """Local ``*.shapes.ttl`` files applicable to *path*.

    For a file: its siblings in the same directory. For a directory: every
    ``*.shapes.ttl`` in the tree. Sorted for deterministic ordering.
    """
    base = path.parent if path.is_file() else path
    if path.is_file():
        return sorted(base.glob(f"*{SHAPES_SUFFIX}"))
    return sorted(base.rglob(f"*{SHAPES_SUFFIX}"))


def load_shapes(files: list[Path]) -> Graph:
    """Parse and union *files* into one shapes graph (empty when there are none)."""
    graph = Graph()
    for path in files:
        graph.parse(path, format="turtle")
    return graph
