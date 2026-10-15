"""Adapters for the external detectors (ruff, pylint, vulture).

Each returns a flat list of {rel, line, col, tool, rule} — normalized
before anything downstream has to know these are three different tools.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from .discovery import normalize_path


def run_ruff(root: Path, rel_files: list[str], rules: list[str]) -> list[dict]:
    if not rel_files:
        return []
    try:
        proc = subprocess.run(
            ["ruff", "check", "--select", ",".join(rules), "--output-format=json", *rel_files],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,  # ruff exits 1 when it finds anything — not our error
        )
    except FileNotFoundError:
        raise SystemExit(
            "✗ craftcov needs `ruff` on PATH for this catalog's ruff-mapped entries — "
            "pip install ruff."
        ) from None
    if proc.returncode not in (0, 1):
        raise SystemExit(f"✗ ruff failed:\n{proc.stderr}")
    items = []
    for item in json.loads(proc.stdout or "[]"):
        rel = normalize_path(root, item["filename"])
        if rel is None:
            continue
        items.append(
            {
                "rel": rel,
                "line": item["location"]["row"],
                "col": item["location"]["column"],
                "tool": "ruff",
                "rule": item["code"],
            }
        )
    return items


def run_pylint(root: Path, rel_files: list[str], rules: list[str]) -> list[dict]:
    if not rel_files:
        return []
    try:
        proc = subprocess.run(
            [
                "pylint",
                "--disable=all",
                f"--enable={','.join(rules)}",
                "--output-format=json",
                *rel_files,
            ],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,  # pylint's exit code is a findings bitmask, not a crash signal
        )
    except FileNotFoundError:
        raise SystemExit(
            "✗ craftcov needs `pylint` on PATH for this catalog's pylint-mapped entries "
            "(extract-class) — pip install pylint, or drop that entry's detector in catalog.yaml."
        ) from None
    try:
        raw = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        raise SystemExit(
            f"✗ pylint produced unparseable output:\n{proc.stdout}\n{proc.stderr}"
        ) from None
    items = []
    for item in raw:
        rel = normalize_path(root, item["path"])
        if rel is None:
            continue
        items.append(
            {
                "rel": rel,
                "line": item["line"],
                "col": item.get("column", 0),
                "tool": "pylint",
                "rule": item["message-id"],
            }
        )
    return items


_VULTURE_LINE = re.compile(r"^(?P<path>.+):(?P<line>\d+): .+ \((?P<pct>\d+)% confidence\)$")


def run_vulture(root: Path, rel_files: list[str], min_confidence: int) -> list[dict]:
    """min_confidence is vulture's own per-finding score, not craftcov's
    invention — on a real codebase (kai-ster, checked while building this)
    it clusters hard into two tiers: unused *variables* at 100% (redundant
    with ruff's own F841 — vulture adds nothing there) and unused
    functions/classes/methods at 60% (vulture's own floor for "fairly sure
    but could be wrong" — decorator-registered pytest-bdd steps and
    Textual's on_* naming-convention handlers are exactly the kind of
    indirect-call pattern that scores here without being genuinely dead).
    Default 0 (vulture's own default: report everything) trades precision
    for recall on purpose — raise it via --vulture-min-confidence once
    you've triaged a first pass and know your codebase's noise floor."""
    if not rel_files:
        return []
    try:
        proc = subprocess.run(
            ["vulture", f"--min-confidence={min_confidence}", *rel_files],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,  # vulture exits non-zero when it finds anything — not our error
        )
    except FileNotFoundError:
        raise SystemExit(
            "✗ craftcov needs `vulture` on PATH for this catalog's vulture-mapped entries "
            "(dead-code) — pip install vulture, or drop that entry's vulture detector "
            "in catalog.yaml."
        ) from None
    items = []
    for line in proc.stdout.splitlines():
        m = _VULTURE_LINE.match(line)
        if not m:
            # vulture has no machine-readable format; skip anything that doesn't parse
            continue
        rel = normalize_path(root, m.group("path"))
        if rel is None:
            continue
        items.append(
            {
                "rel": rel,
                "line": int(m.group("line")),
                "col": 0,
                "tool": "vulture",
                "rule": None,
                "confidence": int(m.group("pct")),
            }
        )
    return items
