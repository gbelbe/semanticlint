"""Which class/function a line belongs to, so findings can be attributed to a class."""

from __future__ import annotations

import ast

CLASS = "class"
FUNCTION = "function"
Scope = tuple[int, int, str, str]  # (start_line, end_line, kind, qualified_name)


def _collect_scopes(node: ast.AST, prefix: str, scopes: list[Scope]) -> None:
    for child in ast.iter_child_nodes(node):
        if not isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            _collect_scopes(child, prefix, scopes)
            continue
        kind = CLASS if isinstance(child, ast.ClassDef) else FUNCTION
        qualname = f"{prefix}.{child.name}" if prefix else child.name
        end = getattr(child, "end_lineno", child.lineno)
        scopes.append((child.lineno, end, kind, qualname))
        _collect_scopes(child, qualname, scopes)


def build_scope_index(source: str) -> list[Scope]:
    """(start_line, end_line, kind, qualified_name) for every class/function
    in the file. Callers pick the smallest enclosing span themselves, so
    order here doesn't matter."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    scopes: list[Scope] = []
    _collect_scopes(tree, "", scopes)
    return scopes


def enclosing_class(scopes: list[Scope], line: int) -> str | None:
    best: Scope | None = None
    for start, end, kind, qualname in scopes:
        if kind != CLASS or not (start <= line <= end):
            continue
        if best is None or (end - start) < (best[1] - best[0]):
            best = (start, end, kind, qualname)
    return best[3] if best else None
