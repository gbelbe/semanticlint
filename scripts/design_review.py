#!/usr/bin/env python3
"""Advisory design prompts for the rules no gate can decide.

The gates check what can be measured: complexity, size, heuristics, tests. Some of Clean
Code's rules are about intent (does a function do one thing? does a query change state?) and
cannot be decided from a diff. They can, however, be *smelled*: a boolean parameter usually
means two behaviours, "and" in a name usually means two jobs, a `get_` that assigns to
`self` mixes a command with a query. This script flags those in the functions a change
touched, as prompts for the reviewer. They are not findings, they never fail anything, and
a human decides.

Python only. Deterministic and offline: no model, no credentials.

Usage:
    python scripts/design_review.py --base origin/main
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import NamedTuple

sys.path.insert(
    0, str(Path(__file__).resolve().parent)
)  # siblings by bare name, also when imported as scripts.<name>
from astfuncs import walk_functions  # noqa: E402
from gate_config import DESIGN_REVIEW, ConfigError, find_root, load_settings  # noqa: E402
from gitdiff import added_lines, base_ref_parser, git, touched_python_files  # noqa: E402

QUERY_PREFIXES = ("get_", "is_", "has_", "find_", "count_", "compute_", "calculate_")
MUTATORS = frozenset(
    {"append", "extend", "update", "pop", "remove", "clear", "insert", "add", "discard", "sort"}
)
RECEIVER = "self"
TEST_FILE_PREFIX = "test_"  # fixtures make test functions look parameter-heavy; not a design signal
DEFAULT_LIMIT = 15


class Limits(NamedTuple):
    """What counts as too many parameters or too long: Clean Code's bar, not the gate's limit."""

    max_parameters: int = 2  # the gate's hard limit is 5
    max_lines: int = 20  # the gate's limit is 50 statements


class Note(NamedTuple):
    path: str
    line: int
    name: str
    message: str


def _parameters(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.arg]:
    args = node.args
    named = [*args.posonlyargs, *args.args, *args.kwonlyargs]
    return [a for a in named if a.arg not in (RECEIVER, "cls")]


def _flag_arguments(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    args = node.args
    positional = [*args.posonlyargs, *args.args]
    defaults = dict(zip(reversed(positional), reversed(args.defaults), strict=False))
    defaults.update({a: d for a, d in zip(args.kwonlyargs, args.kw_defaults, strict=True) if d})
    flags = []
    for arg in _parameters(node):
        boolean_default = isinstance(default := defaults.get(arg), ast.Constant) and isinstance(
            default.value, bool
        )
        boolean_annotation = isinstance(arg.annotation, ast.Name) and arg.annotation.id == "bool"
        if boolean_default or boolean_annotation:
            flags.append(arg.arg)
    return flags


def _changes_state(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """True when the body assigns to an attribute of self or calls a mutator on a parameter."""
    names = {a.arg for a in _parameters(node)} | {RECEIVER}
    for inner in ast.walk(node):
        targets = [inner.target] if isinstance(inner, ast.AugAssign) else []
        targets += inner.targets if isinstance(inner, ast.Assign) else []
        if any(isinstance(t, ast.Attribute) for t in targets):
            return True
        if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute):
            owner = inner.func.value
            owner_is_known = isinstance(owner, ast.Name) and owner.id in names
            if inner.func.attr in MUTATORS and owner_is_known:
                return True
    return False


def _prompts(node: ast.FunctionDef | ast.AsyncFunctionDef, limits: Limits) -> list[str]:
    prompts = [
        f"flag argument `{flag}`: does it make this do two different things? "
        "(Clean Code: split it into two functions)"
        for flag in _flag_arguments(node)
    ]
    count = len(_parameters(node))
    if count > limits.max_parameters:
        prompts.append(
            f"{count} parameters: the design bar is {limits.max_parameters} or fewer "
            "(the gate allows 5); is a parameter object hiding here?"
        )
    if "_and_" in node.name:
        prompts.append("the name says 'and': a function should do one thing")
    if node.name.startswith(QUERY_PREFIXES) and _changes_state(node):
        prompts.append(
            "reads like a query but changes state: command-query separation says do one, not both"
        )
    length = (node.end_lineno or node.lineno) - node.lineno + 1
    if length > limits.max_lines:
        prompts.append(
            f"{length} lines: the design bar is about {limits.max_lines}; what could come out?"
        )
    return prompts


def review_source(
    source: str,
    added: set[int],
    path: str = "",
    limits: Limits = Limits(),  # noqa: B008
) -> list[Note]:
    """Prompts for every function in *source* that contains a line in *added*."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    notes = []
    for name, node in walk_functions(tree, []):
        touched = any(node.lineno <= line <= (node.end_lineno or node.lineno) for line in added)
        if touched:
            notes += [Note(path, node.lineno, name, text) for text in _prompts(node, limits)]
    return sorted(notes, key=lambda n: (n.path, n.line))


def review_diff(root: Path, base: str, head: str = "HEAD") -> list[Note]:
    """Prompts for the functions touched between the merge-base of *base* and *head*."""
    section = load_settings(find_root(root))[DESIGN_REVIEW]
    limits = Limits(section["max-parameters"], section["max-lines"])
    merge_base = git(["merge-base", base, head], cwd=root).strip()
    notes: list[Note] = []
    for old_rel, new_rel in touched_python_files(root, merge_base, head):
        if Path(new_rel).name.startswith(TEST_FILE_PREFIX) or Path(new_rel).name == "conftest.py":
            continue
        added = added_lines(merge_base, head, root, tuple(dict.fromkeys((old_rel, new_rel))))
        source = git(["show", f"{head}:{new_rel}"], cwd=root, check=False)
        notes += review_source(source, added, new_rel, limits)
    return notes


def render_review(notes: list[Note], limit: int = DEFAULT_LIMIT) -> str:
    """The PR-comment section: a table of prompts, capped, or "" when there are none."""
    if not notes:
        return ""
    rows = [f"| `{n.path}:{n.line}` | `{n.name}` | {n.message} |" for n in notes[:limit]]
    lines = [
        "**Design review (advisory)**",
        "",
        "Prompts for the reviewer on the functions this change touched: rules a gate cannot "
        "decide from a diff, flagged by smell. They are not findings, and nothing here blocks "
        "the PR.",
        "",
        "| Where | Function | Prompt |",
        "|---|---|---|",
        *rows,
    ]
    if len(notes) > limit:
        lines += ["", f"…and {len(notes) - limit} more."]
    return "\n".join(lines)


def main() -> int:
    parser = base_ref_parser(__doc__)
    parser.add_argument("--path", default=".", help="repo root (default: current directory)")
    args = parser.parse_args()
    try:
        notes = review_diff(Path(args.path).resolve(), args.base)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(render_review(notes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
