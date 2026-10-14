"""AST helpers shared by the gate scripts: enumerate functions by qualified name.

The complexity and mutation ratchets key their results on
``<relpath>::<qualified name>``; sharing the walk guarantees both name a method
the same way (``Class.method``, ``outer.inner``).

Copied into consuming repos next to the scripts that import it (see bootstrap.sh).
"""

from __future__ import annotations

import ast
from collections.abc import Iterator


def qualified(stack: list[str], name: str) -> str:
    return ".".join([*stack, name])


def walk_functions(
    node: ast.AST, stack: list[str]
) -> Iterator[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]]:
    """Every function in *node*, with the qualified name it should be reported under."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.ClassDef):
            yield from walk_functions(child, [*stack, child.name])
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield qualified(stack, child.name), child
            yield from walk_functions(child, [*stack, child.name])
        else:
            yield from walk_functions(child, stack)
