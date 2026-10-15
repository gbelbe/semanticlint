#!/usr/bin/env python3
"""Where a gate spends its time: a trace of its steps, and the slowest tests behind a mutation run.

A gate script wraps each of its stages in `step("name")`. The stage's duration is printed to
stderr (so it is in the job log) and, when `CRAFT_GATE_TIMINGS` names a file, appended to it as
one JSON line. A CI job then renders that file into its step summary:

    python scripts/gate_timing.py report timings.jsonl >> "$GITHUB_STEP_SUMMARY"

The second question, "which tests make every mutant slow?", is answered from the durations mutmut
already recorded:

    python scripts/gate_timing.py mutants [--mutants-dir mutants] [--top 10]

For the history of a whole workflow across runs, see ci_history.py.

Copied into consuming repos next to the scripts that import it (see bootstrap.sh).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

ENV_VAR = "CRAFT_GATE_TIMINGS"
STATS_FILE = "mutmut-stats.json"
NAME, SECONDS = "name", "seconds"
_PERCENT = 100


@contextmanager
def step(name: str) -> Iterator[None]:
    """Time the block; print the duration, and append it to $CRAFT_GATE_TIMINGS when that is set."""
    started = time.monotonic()
    try:
        yield
    finally:
        seconds = time.monotonic() - started
        print(f"⏱ {name}: {seconds:.1f}s", file=sys.stderr)
        record(name, seconds)


def record(name: str, seconds: float) -> None:
    """Append one measurement to the file $CRAFT_GATE_TIMINGS names; nothing when it is unset."""
    target = os.environ.get(ENV_VAR)
    if target:
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(json.dumps({NAME: name, SECONDS: round(seconds, 3)}) + "\n")


def read_records(path: Path) -> list[dict]:
    """The measurements in a timings file; a missing file is no measurements."""
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def render_steps(records: list[dict]) -> str:
    """The steps as a markdown table, the slowest first, with each one's share of the total."""
    if not records:
        return "No gate steps were timed."
    total = sum(r[SECONDS] for r in records)
    ordered = sorted(records, key=lambda r: r[SECONDS], reverse=True)
    rows = [
        (r[NAME], f"{r[SECONDS]:.1f}s", f"{_PERCENT * r[SECONDS] / total:.0f}%") for r in ordered
    ]
    return f"**Gate steps, {total:.1f}s in all**\n\n" + _table(("Step", "Time", "Share"), rows)


def mutation_costs(stats: dict) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
    """(slowest tests, costliest functions), each as (name, seconds), slowest first.

    A function's cost is the time of the tests that cover it: every mutant of it runs them all.
    """
    durations: dict[str, float] = stats.get("duration_by_test", {})
    by_function: dict[str, list[str]] = stats.get("tests_by_mangled_function_name", {})
    tests = sorted(durations.items(), key=lambda item: item[1], reverse=True)
    functions = {
        name: sum(durations.get(test, 0.0) for test in covering)
        for name, covering in by_function.items()
    }
    return tests, sorted(functions.items(), key=lambda item: item[1], reverse=True)


def render_mutation_costs(stats: dict, top: int) -> str:
    tests, functions = mutation_costs(stats)
    if not tests:
        return "No test durations recorded: run `mutmut run` first."
    slow_tests = _table(("Test", "Seconds"), [(n, f"{s:.2f}") for n, s in tests[:top]])
    costly = _table(
        ("Function (mutmut name)", "Seconds per mutant"),
        [(n, f"{s:.2f}") for n, s in functions[:top]],
    )
    return (
        f"**Slowest tests** (of {len(tests)})\n\n{slow_tests}\n\n"
        f"**Functions whose mutants cost the most** (of {len(functions)})\n\n{costly}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    shown = commands.add_parser("report", help="render a timings file as a markdown table")
    shown.add_argument("file", type=Path)
    costs = commands.add_parser("mutants", help="the slowest tests behind a mutation run")
    costs.add_argument("--mutants-dir", type=Path, default=Path("mutants"))
    costs.add_argument("--top", type=int, default=10)
    args = parser.parse_args(argv)

    if args.command == "report":
        print(render_steps(read_records(args.file)))
        return 0
    stats_path = args.mutants_dir / STATS_FILE
    stats = json.loads(stats_path.read_text()) if stats_path.is_file() else {}
    print(render_mutation_costs(stats, args.top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
