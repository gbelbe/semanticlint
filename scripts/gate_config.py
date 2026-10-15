#!/usr/bin/env python3
"""Which of the test gates run in this repo: patch coverage, mutation, behaviour (Gherkin) coverage.

All three are on by default. A repo turns one off in pyproject.toml, with a reason:

    [tool.craft-gate.mutation]
    enabled = false
    reason = "suite takes 40 minutes; revisit when it is split"

A gate that cannot work (no pytest suite, no [tool.mutmut], no .feature files) is an error that
says what to add or how to opt out, rather than a job that passes because it found nothing to
check. Mutation and behaviour coverage both need the suite patch coverage measures, so they are
skipped, with that as the reason, when patch coverage is off.

Usage (as the CI template calls it):
    python scripts/gate_config.py <gate> [--path .]

Prints the decision, appends it to $GITHUB_OUTPUT when set (status=run|skip plus the gate's
settings) and exits 1 only on misconfiguration.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

RUN, SKIP, ERROR = "run", "skip", "error"
PATCH, MUTATION, BDD = "patch-coverage", "mutation", "bdd"
GATES = (PATCH, MUTATION, BDD)
ENABLED, REASON, THRESHOLD, PATHS, EXCLUDE = "enabled", "reason", "threshold", "paths", "exclude"
TABLE = "craft-gate"
CONFIG_FILE = "craft-gate.toml"
COMPLEXITY, REFACTOR_FIRST, DESIGN_REVIEW, EXEMPTIONS = (
    "complexity",
    "refactor-first",
    "design-review",
    "exemptions",
)

# Test code is executed by definition, so its own changed lines would pad the percentage; diff-cover
# is told to leave these globs out and judge production code only.
TEST_FILES = ["tests/*", "*/tests/*", "test_*.py", "*_test.py", "conftest.py"]

# Every value a repo can set, with the default each gate used when these were hard-coded.
DEFAULTS: dict[str, dict[str, Any]] = {
    PATCH: {ENABLED: True, REASON: "", THRESHOLD: 90, "source": "", EXCLUDE: TEST_FILES},
    MUTATION: {ENABLED: True, REASON: "", THRESHOLD: 80, "improvement": 20},
    BDD: {ENABLED: True, REASON: "", THRESHOLD: 80, PATHS: ["tests/features"], EXCLUDE: TEST_FILES},
    COMPLEXITY: {
        "cyclomatic": 15,
        "cognitive": 15,
        "duplicated-literal-occurrences": 3,
        "duplicated-literal-min-length": 5,
    },
    REFACTOR_FIRST: {"per-file": "must-decrease"},
    DESIGN_REVIEW: {"max-parameters": 2, "max-lines": 20},
    EXEMPTIONS: {"legacy-debt": True, "new-code": False},
}
CHOICES = {(REFACTOR_FIRST, "per-file"): ("must-decrease", "must-not-increase")}
PERCENT_KEYS = (THRESHOLD, "improvement")
MINIMUMS = {  # the smallest sensible value of each count; below it the gate would flag everything
    "cyclomatic": 1,
    "cognitive": 1,
    "duplicated-literal-occurrences": 2,
    "duplicated-literal-min-length": 1,
    "max-parameters": 0,
    "max-lines": 1,
}
NEEDS_COVERAGE = (MUTATION, BDD)
MARKER = "mutation"
MARKER_USE = f"pytest.mark.{MARKER}"
SELECTION_KEY = "pytest_add_cli_args_test_selection"
_PRUNED_DIRS = {".git", ".venv", "venv", "node_modules", "site-packages", "build", "dist", ".tox"}
_PERCENT_MAX = 100
_SOURCE = re.compile(r"[\w./-]*")  # a package or directory name, as --cov takes it


def _where(section: str | None = None) -> str:
    """How a section is spelled in craft-gate.toml or pyproject.toml, for messages."""
    if section is None:
        return f"{CONFIG_FILE} (or [tool.{TABLE}] in pyproject.toml)"
    return f"[{section}] in {CONFIG_FILE} (or [tool.{TABLE}.{section}])"


class ConfigError(Exception):
    """The craft-gate configuration is unusable."""


@dataclass(frozen=True)
class Waive:
    """Which rules a `Tidy-Exempt:` trailer waives: the debt rules, and the new-code rules."""

    legacy_debt: bool = False
    new_code: bool = False


def waive_from(settings: dict[str, dict[str, Any]], exempt: bool) -> Waive:
    """What the trailer waives, per the repo's `[exemptions]`; nothing without a trailer."""
    section = settings[EXEMPTIONS]
    return Waive(exempt and section["legacy-debt"], exempt and section["new-code"])


@dataclass(frozen=True)
class Decision:
    gate: str
    status: str
    reason: str = ""
    settings: dict[str, Any] = field(default_factory=dict)


def _parse(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path.name} does not parse: {exc}") from exc


def _read_tool_table(root: Path) -> dict[str, Any]:
    return _parse(root / "pyproject.toml").get("tool", {})


def _read_table(root: Path, tool: dict[str, Any]) -> dict[str, Any]:
    """craft-gate.toml when the repo has one, otherwise pyproject.toml's [tool.craft-gate]."""
    if (root / CONFIG_FILE).is_file():
        return _parse(root / CONFIG_FILE)
    return tool.get(TABLE, {})


def _one_line(value: Any) -> bool:
    """A string with no newline or other control character: it is written to $GITHUB_OUTPUT as
    `key=value`, so a newline would let a config file add a line of its own (`status=skip`)."""
    return isinstance(value, str) and value.isprintable()


def _valid(section: str, key: str, value: Any) -> bool:
    default = DEFAULTS[section][key]
    if (section, key) in CHOICES:
        return value in CHOICES[(section, key)]
    if isinstance(default, bool):
        return isinstance(value, bool)
    if isinstance(default, int):
        if isinstance(value, bool) or not isinstance(value, int):
            return False
        return 0 <= value <= _PERCENT_MAX if key in PERCENT_KEYS else value >= MINIMUMS[key]
    if isinstance(default, list):
        return isinstance(value, list) and all(_one_line(p) for p in value)
    if key == "source":
        return _one_line(value) and _SOURCE.fullmatch(value) is not None
    return _one_line(value) if isinstance(default, str) else isinstance(value, type(default))


def _section_settings(table: dict[str, Any], section: str) -> dict[str, Any]:
    given = table.get(section, {})
    unknown = sorted(set(given) - set(DEFAULTS[section]))
    if unknown:
        raise ConfigError(f"{_where(section)} has unknown key(s): {', '.join(unknown)}")
    for key, value in given.items():
        if not _valid(section, key, value):
            raise ConfigError(f"{_where(section)} {key} is not valid: {value!r}")
    merged = {**DEFAULTS[section], **given}
    return {k: list(v) if isinstance(v, list) else v for k, v in merged.items()}


def _load(root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """(settings per section, the whole [tool] table), validated."""
    tool = _read_tool_table(root)
    table = _read_table(root, tool)
    unknown = sorted(set(table) - set(DEFAULTS))
    if unknown:
        raise ConfigError(f"{_where()} has unknown section(s): {', '.join(unknown)}")
    return {section: _section_settings(table, section) for section in DEFAULTS}, tool


def load_settings(root: Path) -> dict[str, dict[str, Any]]:
    """Every section's settings for the repo at *root*, defaults filled in. Raises ConfigError."""
    return _load(root)[0]


def find_root(start: Path) -> Path:
    """The nearest directory at or above *start* that holds the config, pyproject.toml or .git."""
    start = start.resolve()
    for directory in (start, *start.parents):
        if any((directory / name).exists() for name in (CONFIG_FILE, "pyproject.toml", ".git")):
            return directory
    return start


def _off_reason(settings: dict[str, Any], gate: str) -> str | None:
    """Why this gate is switched off, None when it is on. A switch with no reason is an error."""
    if settings[ENABLED]:
        return None
    reason = settings[REASON].strip()
    if not reason:
        raise ConfigError(f"{_where(gate)} enabled = false needs a non-empty reason")
    return reason


def _has_pytest_suite(root: Path) -> bool:
    for _dir, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in _PRUNED_DIRS]
        if any(
            f.startswith("test_") and f.endswith(".py") or f.endswith("_test.py") for f in files
        ):
            return True
    return False


def _has_features(root: Path, paths: list[str]) -> bool:
    return any(next((root / p).rglob("*.feature"), None) for p in paths if (root / p).is_dir())


def _registered_markers(root: Path, tool: dict[str, Any]) -> str:
    """Everywhere pytest can learn a marker, as one text: pyproject, the ini files, conftest."""
    options = tool.get("pytest", {}).get("ini_options", {})
    parts = [" ".join(map(str, options.get("markers", [])))]
    for name in ("pytest.ini", "tox.ini", "setup.cfg", "conftest.py", "tests/conftest.py"):
        if (root / name).is_file():
            parts.append((root / name).read_text(errors="replace"))
    return "\n".join(parts)


def _is_test_file(name: str) -> bool:
    """pytest's own default: test_*.py or *_test.py. Other files may merely mention the marker."""
    return name.endswith(".py") and (name.startswith("test_") or name.endswith("_test.py"))


def _marked_files(root: Path) -> set[str]:
    """Test files that carry @pytest.mark.mutation, as repo-relative posix paths."""
    found = set()
    for directory, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in _PRUNED_DIRS]
        for name in files:
            path = Path(directory) / name
            if _is_test_file(name) and MARKER_USE in path.read_text(errors="replace"):
                found.add(path.relative_to(root).as_posix())
    return found


def _selection_problem(root: Path, tool: dict[str, Any]) -> str | None:
    """What disagrees between mutmut's test selection and the `mutation` marker, if anything."""
    args = [str(a) for a in tool.get("mutmut", {}).get(SELECTION_KEY, [])]
    files = {a for a in args if a.endswith(".py")}
    uses_marker = "-m" in args and MARKER in args
    if uses_marker and f"{MARKER}:" not in _registered_markers(root, tool):
        return f"-m {MARKER} is selected but the marker is not registered (add it to markers)"
    gone = sorted(f for f in files if not (root / f).is_file())
    if gone:
        return f"{SELECTION_KEY} names file(s) that do not exist: {', '.join(gone)}"
    orphans = sorted(_marked_files(root) - files) if uses_marker else []
    if orphans:
        return (
            f"@pytest.mark.{MARKER} in file(s) missing from {SELECTION_KEY}: {', '.join(orphans)}"
        )
    return None


def _missing(gate: str, root: Path, settings: dict[str, Any], tool: dict[str, Any]) -> str | None:
    """What the gate needs and the repo lacks, as an instruction; None when it has it."""
    optout = f"or set [tool.{TABLE}.{gate}] enabled = false with a reason"
    if gate == PATCH and not _has_pytest_suite(root):
        return f"no pytest suite found; add tests, {optout}"
    if gate == MUTATION and "mutmut" not in tool:
        return f"[tool.mutmut] is missing from pyproject.toml; configure mutmut, {optout}"
    if gate == MUTATION and (problem := _selection_problem(root, tool)):
        return f"{problem}; fix the selection, {optout}"
    if gate == BDD and not _has_features(root, settings[PATHS]):
        return f"no .feature files under {', '.join(settings['paths'])}; add scenarios, {optout}"
    return None


def decide(root: Path, gate: str) -> Decision:
    try:
        settings, tool = _load(root)
        own = settings[gate]
        reason = _off_reason(own, gate)
        if reason is None and gate in NEEDS_COVERAGE:
            upstream = _off_reason(settings[PATCH], PATCH)
            reason = None if upstream is None else f"patch-coverage is off ({upstream})"
    except ConfigError as exc:
        return Decision(gate, ERROR, str(exc))
    if reason is not None:
        return Decision(gate, SKIP, reason)
    missing = _missing(gate, root, own, tool)
    if missing is not None:
        return Decision(gate, ERROR, missing)
    return Decision(gate, RUN, settings=own)


def skipped_gates(root: Path) -> list[tuple[str, str]]:
    decisions = (decide(root, gate) for gate in GATES)
    return [(d.gate, d.reason) for d in decisions if d.status == SKIP]


def render_skipped(skipped: list[tuple[str, str]]) -> str:
    """The PR-comment section naming each gate this repo has switched off, and why."""
    if not skipped:
        return ""
    rows = [f"| `{gate}` | {reason} |" for gate, reason in skipped]
    return "\n".join(
        ["**Gates switched off in this repo**", "", "| Gate | Reason |", "|---|---|", *rows]
    )


def _output_lines(decision: Decision) -> list[str]:
    lines = [f"status={decision.status}", f"reason={decision.reason}"]
    for key, value in decision.settings.items():
        text = " ".join(value) if isinstance(value, list) else str(value)
        lines.append(f"{key}={text}")
    return lines


def _publish(decision: Decision) -> None:
    target = os.environ.get("GITHUB_OUTPUT")
    if target:
        with open(target, "a") as handle:
            handle.write("\n".join(_output_lines(decision)) + "\n")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary and decision.status == SKIP:
        with open(summary, "a") as handle:
            handle.write(f"Skipped `{decision.gate}`: {decision.reason}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gate", choices=GATES)
    parser.add_argument("--path", default=".", help="repo root (default: current directory)")
    args = parser.parse_args(argv)

    decision = decide(Path(args.path).resolve(), args.gate)
    if decision.status == ERROR:
        print(f"✗ {decision.gate}: {decision.reason}", file=sys.stderr)
        return 1
    _publish(decision)
    if decision.status == SKIP:
        print(f"{decision.gate}: skipped on purpose: {decision.reason}")
    else:
        print(f"{decision.gate}: running")
    return 0


if __name__ == "__main__":
    sys.exit(main())
