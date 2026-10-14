#!/usr/bin/env python3
"""Report what a pull request loosens in craft-gate.toml.

A looser value fails no check: raising a complexity limit or lowering a threshold makes a red
gate green without touching the code. So the change itself is reported. This compares the
settings at the base of a pull request with the settings at its head, as parsed values (not
text, so reformatting is silent), and lists every value that makes the gates weaker: a limit
raised, a floor lowered, a gate switched off, an exemption widened, a pattern added to what is
not counted. Tightening is never listed. A repo with no config at the base is compared against
the defaults.

Advisory: it prints and exits 0. A person decides, ideally one named in CODEOWNERS for the file.

Usage:
    python scripts/config_loosening.py --base origin/main
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Any, NamedTuple

sys.path.insert(
    0, str(Path(__file__).resolve().parent)
)  # siblings by bare name, also when imported as scripts.<name>
from gate_config import (  # noqa: E402
    CHOICES,
    CONFIG_FILE,
    REFACTOR_FIRST,
    ConfigError,
    load_settings,
)
from gitdiff import base_ref_parser, git  # noqa: E402

CONFIG_SOURCES = (CONFIG_FILE, "pyproject.toml")
PER_FILE = CHOICES[(REFACTOR_FIRST, "per-file")]  # ordered strictest first

# For each key, the direction in which the gates get weaker. A key that is neither listed here
# nor in NEUTRAL has not been ruled on, and a test fails until it is.
_WEAKER = {
    "higher": lambda before, after: after > before,
    "lower": lambda before, after: after < before,
    "off": lambda before, after: before and not after,
    "on": lambda before, after: after and not before,
    "wider": lambda before, after: bool(set(after) - set(before)),
    "narrower": lambda before, after: bool(set(before) - set(after)),
    "later": lambda before, after: PER_FILE.index(after) > PER_FILE.index(before),
}
DIRECTION = {
    **dict.fromkeys(
        (
            "cyclomatic",
            "cognitive",
            "duplicated-literal-occurrences",
            "duplicated-literal-min-length",
            "max-parameters",
            "max-lines",
        ),
        "higher",
    ),
    **dict.fromkeys(("threshold", "improvement"), "lower"),
    "enabled": "off",
    **dict.fromkeys(("legacy-debt", "new-code"), "on"),
    "exclude": "wider",
    "paths": "narrower",
    "per-file": "later",
}
NEUTRAL = frozenset({"reason", "source"})  # words and a path: neither makes a gate weaker


class Loosened(NamedTuple):
    section: str
    key: str
    before: Any
    after: Any


def loosened(before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]]) -> list[Loosened]:
    """Every value in *after* that makes the gates weaker than it was in *before*."""
    found = []
    for section, keys in after.items():
        for key, value in keys.items():
            if key in NEUTRAL:
                continue
            if _WEAKER[DIRECTION[key]](before[section][key], value):
                found.append(Loosened(section, key, before[section][key], value))
    return found


def settings_at(root: Path, ref: str) -> dict[str, dict[str, Any]]:
    """The validated settings as committed at *ref*; the defaults where it has no config."""
    with tempfile.TemporaryDirectory(prefix="craft-gate-config-") as scratch:
        for name in CONFIG_SOURCES:
            text = git(["show", f"{ref}:{name}"], cwd=root, check=False)
            if text:
                (Path(scratch) / name).write_text(text)
        return load_settings(Path(scratch))


def review_config(root: Path, base: str) -> list[Loosened]:
    """What HEAD loosens since its merge-base with *base*. May raise ConfigError."""
    merge_base = git(["merge-base", base, "HEAD"], cwd=root).strip()
    return loosened(settings_at(root, merge_base), settings_at(root, "HEAD"))


def render_loosened(items: list[Loosened]) -> str:
    """The PR-comment section, or "" when nothing was loosened."""
    if not items:
        return ""
    rows = [f"| `{i.section}.{i.key}` | `{i.before}` | `{i.after}` |" for i in items]
    return "\n".join(
        [
            "**Thresholds loosened**",
            "",
            "This change makes the gates weaker. A looser value fails no check, so a person "
            "should decide it was meant, and why.",
            "",
            "| Setting | Before | After |",
            "|---|---|---|",
            *rows,
        ]
    )


def main() -> int:
    parser = base_ref_parser(__doc__)
    parser.add_argument("--path", default=".", help="repo root (default: current directory)")
    args = parser.parse_args()
    try:
        items = review_config(Path(args.path).resolve(), args.base)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(render_loosened(items))
    return 0


if __name__ == "__main__":
    sys.exit(main())
