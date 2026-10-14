"""Duplicate-code detection (ported, not subprocessed).

Same core technique as both PMD CPD (Karp-Rabin rolling-hash string
matching over a token stream, per its own docs) and pylint's own R0801
checker (same technique, one level coarser: stripped *lines* rather than
language tokens) — verified against both before writing this, not
designed from scratch. Ported instead of subprocessing pylint because
pylint's CLI only puts ONE of a duplicate pair's two locations in
structured JSON; the other is embedded as free text inside the message,
and its internal API (`_compute_sims`) is private/unstable. This is ~60
lines once you already know the algorithm, and needs no new dependency.

Corpus-wide by nature (a duplicate only means anything relative to its
other copy, possibly in a different file) — unlike ruff/pylint/vulture,
this always runs over every file, not just ones the per-file cache says
changed. See scan.merge_corpus_findings for why that's an acceptable trade rather
than a missed optimization.

Exact-match only, like both reference tools' default mode — no
identifier/literal normalization (PMD's opt-in Type-2 fuzzy matching
needs a real per-language tokenizer to do properly; out of scope here).
Doesn't special-case docstrings the way pylint's checker does either (a
deliberate simplification) — a duplicated docstring block is still
reported, which is arguably still useful signal for this catalog entry.

Import statements ARE special-cased, on purpose, unlike PMD/pylint's own
checkers: two files both doing `import os / import sys / from pathlib
import Path` the same way isn't duplicated logic, it's every file in the
repo depending on the same libraries the same way — see
`_import_lines`/`strip_lines_for_dupes`.
"""

from __future__ import annotations

import ast
import hashlib
import io
import tokenize
from itertools import combinations
from pathlib import Path
from typing import NamedTuple

Line = tuple[int, str]  # (original_line_number, normalized_text)
Match = tuple[str, int, int, str, int, int]  # (file_a, start_a, end_a, file_b, start_b, end_b)


class Block(NamedTuple):
    """One duplicated block: where its two copies are (original line numbers) and how long."""

    file_a: str
    start_a: int
    end_a: int
    file_b: str
    start_b: int
    end_b: int
    lines: int


def _import_lines(source: str) -> set[int]:
    """Every line number spanned by an `import`/`from ... import` statement,
    anywhere in the file (not just top-level — a lazy import inside a
    function is still a library, not code this repo wrote). AST-based, not
    a line-prefix regex, so a multi-line parenthesized `from x import (a,
    b, c)` has all of its lines excluded, not just the first."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            end = getattr(node, "end_lineno", node.lineno)
            lines.update(range(node.lineno, end + 1))
    return lines


def strip_lines_for_dupes(source: str) -> list[tuple[int, str]]:
    """(original_line_number, normalized_text) for every line of code this
    repo actually wrote — comments, blank lines, and import statements all
    dropped. Comments via `tokenize`, not a regex, so a '#' inside a string
    literal is never mistaken for a comment start; imports via `ast`, so a
    library import can't masquerade as "duplicated logic" just because two
    files both `import os, sys, json` the same way."""
    lines = source.splitlines()
    comment_cols: dict[int, int] = {}
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type == tokenize.COMMENT:
                comment_cols[tok.start[0]] = tok.start[1]
    except (tokenize.TokenError, IndentationError, SyntaxError, ValueError):
        pass  # fall back to no comment-stripping for a file tokenize can't handle

    skip = _import_lines(source)

    result: list[tuple[int, str]] = []
    for i, raw in enumerate(lines, start=1):
        if i in skip:
            continue
        text = (raw[: comment_cols[i]] if i in comment_cols else raw).strip()
        if text:
            result.append((i, text))
    return result


def _window_index(
    texts_by_file: dict[str, list[str]], min_lines: int
) -> list[list[tuple[str, int]]]:
    """Every min_lines-line window per file, grouped by content hash; only the groups
    that more than one window shares (same file or different) can be duplicates."""
    by_hash: dict[str, list[tuple[str, int]]] = {}
    for rel, texts in texts_by_file.items():
        for i in range(len(texts) - min_lines + 1):
            key = hashlib.sha256("\n".join(texts[i : i + min_lines]).encode()).hexdigest()
            by_hash.setdefault(key, []).append((rel, i))
    return [occurrences for occurrences in by_hash.values() if len(occurrences) > 1]


def _match_length(texts_a: list[str], i_a: int, texts_b: list[str], i_b: int, start: int) -> int:
    """Extend a *start*-line match forward, line by line, to its true length."""
    length = start
    while (
        i_a + length < len(texts_a)
        and i_b + length < len(texts_b)
        and texts_a[i_a + length] == texts_b[i_b + length]
    ):
        length += 1
    return length


def _raw_matches(texts_by_file: dict[str, list[str]], min_lines: int) -> list[Match]:
    matches: list[Match] = []
    for occurrences in _window_index(texts_by_file, min_lines):
        for (rel_a, i_a), (rel_b, i_b) in combinations(occurrences, 2):
            length = _match_length(texts_by_file[rel_a], i_a, texts_by_file[rel_b], i_b, min_lines)
            matches.append((rel_a, i_a, i_a + length, rel_b, i_b, i_b + length))
    return matches


def _drop_subsumed(matches: list[Match]) -> list[Match]:
    """Longer matches subsume the shorter, overlapping windows that also
    matched inside them — a 20-line duplicate would otherwise produce
    ~17 separate 4-line reports. Keep only matches not already covered by
    a longer one over the same (file, file) pair and overlapping range."""
    ordered = sorted(matches, key=lambda m: -(m[2] - m[1]))
    covered: dict[tuple[str, str], list[tuple[int, int, int, int]]] = {}
    kept: list[Match] = []
    for rel_a, i_a, end_a, rel_b, i_b, end_b in ordered:
        pair_key = (rel_a, rel_b) if rel_a <= rel_b else (rel_b, rel_a)
        ranges = covered.setdefault(pair_key, [])
        if any(
            i_a >= ca0 and end_a <= ca1 and i_b >= cb0 and end_b <= cb1
            for ca0, ca1, cb0, cb1 in ranges
        ):
            continue
        ranges.append((i_a, end_a, i_b, end_b))
        kept.append((rel_a, i_a, end_a, rel_b, i_b, end_b))
    return kept


def find_blocks(filtered_by_file: dict[str, list[Line]], min_lines: int) -> list[Block]:
    """Hash every min_lines-line window per file; any hash shared by two
    windows (same file or different) is a candidate duplicate, extended
    forward line-by-line to its true length, then de-overlapped so one long
    duplicate doesn't get reported as a pile of short overlapping ones."""
    texts_by_file = {rel: [t for _, t in lines] for rel, lines in filtered_by_file.items()}
    return [
        Block(
            rel_a,
            filtered_by_file[rel_a][i_a][0],
            filtered_by_file[rel_a][end_a - 1][0],
            rel_b,
            filtered_by_file[rel_b][i_b][0],
            filtered_by_file[rel_b][end_b - 1][0],
            end_a - i_a,
        )
        for rel_a, i_a, end_a, rel_b, i_b, end_b in _drop_subsumed(
            _raw_matches(texts_by_file, min_lines)
        )
    ]


def find_duplicate_blocks(filtered_by_file: dict[str, list[Line]], min_lines: int) -> list[dict]:
    """find_blocks, as plain dicts (the shape the report and tests consume)."""
    return [b._asdict() for b in find_blocks(filtered_by_file, min_lines)]


Span = tuple[str, int, int]  # (file, first_line, last_line)


def _dupe_item(here: Span, other: Span, n_lines: int) -> dict:
    rel, line, _ = here
    other_rel, other_start, other_end = other
    return {
        "rel": rel,
        "line": line,
        "col": 0,
        "tool": "dupes",
        "rule": None,
        "duplicate_of": f"{other_rel}:{other_start}-{other_end}",
        "dup_lines": n_lines,
    }


def run_dupes(root: Path, rel_files: list[str], min_lines: int) -> list[dict]:
    filtered_by_file = {rel: strip_lines_for_dupes((root / rel).read_text()) for rel in rel_files}
    items: list[dict] = []
    for b in find_blocks(filtered_by_file, min_lines):
        a: Span = (b.file_a, b.start_a, b.end_a)
        other: Span = (b.file_b, b.start_b, b.end_b)
        items += [_dupe_item(a, other, b.lines), _dupe_item(other, a, b.lines)]
    return items
