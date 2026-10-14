#!/usr/bin/env python3
"""Diff-aware mutation-testing ratchet — kill rate for touched functions only.

The mechanical enforcement CRAFTSMANSHIP.md's "Mutation ratchet" section documents.
It has no catalog entry: this is a test-quality gate, not a design heuristic. Independent of every
other gate: doesn't run mutmut itself (a prior `mutmut run` step must have
already populated `mutants/`, normally cached between CI runs the way
`node_modules` or `.venv` are), just reads its results and a git diff.

Fails when a function this change's diff actually touches has a mutation
score (killed / (killed + survived), mutmut's own definition — see
`mutmut badge`) below --threshold. Not base-vs-head like the complexity
ratchet: mutation testing is too expensive to run twice per PR (it reruns
the whole test suite once per mutant), so this checks touched functions
against a floor on the current tree only. The floor is --threshold; a
function that already has a score in the baseline file may instead improve on
that score by --improvement percent. A function with *no* recorded baseline
has no score to improve on, so it must reach --threshold outright: a first
sighting is not a free pass. A genuinely equivalent mutant belongs behind mutmut's own
`# pragma: no mutate` (mutmut's answer to this, same idea as coverage.py's
`# pragma: no cover`) — fix the false positive at its source, not by
lowering this gate's bar.

Reaches into mutmut's internals (`mutmut.utils.format_utils.
orig_function_and_class_names_from_key`) to map a mutant key like
"pkg.mod.x_foo__mutmut_3" back to the function it mutated ("foo"), rather
than mutmut's own per-mutant line-span index (`mutants/<file>.spans`) —
verified against a real run that those spans are lines in the *generated*
mutants file, not the original source, so they can't be intersected with
a `git diff` on the original file directly. This is a real coupling to an
internal, not-obviously-public module; pin mutmut's version range and
re-verify this mapping on any major-version bump.

Usage:
    python scripts/check_mutation_ratchet.py [--base origin/main] [--path .]
        [--mutants-dir mutants] [--threshold 80]
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parent)
)  # siblings by bare name, also when imported as scripts.<name>
from astfuncs import walk_functions  # noqa: E402
from gitdiff import touched_names  # noqa: E402

DEFAULT_THRESHOLD = 80.0

# mutmut's own exit-code -> outcome mapping (mutmut.stats.status_by_exit_code,
# mirrored rather than imported: that module pulls in mutmut's full click/UI
# stack on import, for a handful of int literals this ratchet needs).
_KILLED_CODES = {1, 3, 36, -24, 24, 152, 255}  # killed, incl. timeout as a kill
_SURVIVED_CODES = {0}
_NO_TESTS_CODES = {5, 33}


def function_ranges(root: Path, rel_path: str) -> dict[str, tuple[int, int]]:
    """Map ``<rel_path>::<qualified function name>`` -> (lineno, endline)."""
    path = root / rel_path
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return {}
    ranges = {}
    for name, node in walk_functions(tree, []):
        end = getattr(node, "end_lineno", node.lineno) or node.lineno
        ranges[f"{rel_path}::{name}"] = (node.lineno, end)
    return ranges


def qualified_name_from_mutant_key(key: str) -> str | None:
    """ "pkg.mod.x_foo__mutmut_3" -> "foo"; "pkg.xǁMyClassǁmethod__mutmut_1" -> "MyClass.method".

    Returns None for a key this mutmut version's naming convention doesn't
    match — treated as "not touched" by the caller (fails safe: at worst
    under-counts, never blocks a PR over a mutant it can't place).
    """
    try:
        from mutmut.utils.format_utils import orig_function_and_class_names_from_key
    except ImportError:
        return None
    try:
        func, cls = orig_function_and_class_names_from_key(key)
    except (AssertionError, ValueError):
        return None
    return f"{cls}.{func}" if cls else func


def mutant_outcome(exit_code: int | None) -> str:
    if exit_code in _KILLED_CODES:
        return "killed"
    if exit_code in _SURVIVED_CODES:
        return "survived"
    if exit_code in _NO_TESTS_CODES:
        return "no_tests"
    if exit_code is None:
        return "pending"  # a verdict dropped (or never made) and not yet re-tested
    return "other"  # skipped / suspicious / caught-by-typecheck / segfault / not-checked


def collect_touched_results(
    root: Path, mutants_dir: Path, touched_by_file: dict[str, set[str]]
) -> dict[str, dict[str, int]]:
    """touched_by_file: {relpath: {touched qualified names}} -> per-name outcome counts."""
    results: dict[str, dict[str, int]] = {}
    for rel, names in touched_by_file.items():
        meta_path = mutants_dir / (rel + ".meta")
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text())
        except json.JSONDecodeError:
            continue
        for mutant_key, exit_code in meta.get("exit_code_by_key", {}).items():
            qual = qualified_name_from_mutant_key(mutant_key)
            if qual is None or qual not in names:
                continue
            full_name = f"{rel}::{qual}"
            if full_name not in results:
                results[full_name] = {
                    "killed": 0,
                    "survived": 0,
                    "no_tests": 0,
                    "other": 0,
                    "pending": 0,
                }
            results[full_name][mutant_outcome(exit_code)] += 1
    return results


def find_violations(results: dict[str, dict[str, int]], threshold: float) -> list[str]:
    violations = []
    for name, counts in sorted(results.items()):
        tested = counts["killed"] + counts["survived"]
        if tested == 0:
            if counts["no_tests"]:
                violations.append(
                    f"{name}: {counts['no_tests']} mutant(s) with no covering test — untested code"
                )
            continue
        score = 100.0 * counts["killed"] / tested
        if score < threshold:
            violations.append(
                f"{name}: mutation score {score:.0f}% ({counts['killed']}/{tested} killed, "
                f"< {threshold:.0f}%) — strengthen the test, or mark a genuinely equivalent "
                f"mutant `# pragma: no mutate`"
            )
    return violations


def _score_violation(name: str, score: float, needs: str) -> str:
    return f"{name}: mutation score {score:.0f}%, {needs}"


def evaluate_results(
    results: dict[str, dict[str, int]],
    baseline: dict[str, float],
    threshold: float = DEFAULT_THRESHOLD,
    improvement: float = 20.0,
) -> tuple[list[str], dict[str, float]]:
    """Apply the absolute floor, or the improvement rule for a function with a recorded baseline.

    A function scoring below *threshold* is judged by whether it has a baseline:
    - recorded: it must improve on it by *improvement* percent;
    - none (new, or never recorded): refused. The improvement path needs a score
      to improve on, and a first sighting must not be a free pass.
    At or above *threshold* a function always passes.
    """
    violations: list[str] = []
    updated = dict(baseline)
    for name, counts in sorted(results.items()):
        tested = counts["killed"] + counts["survived"]
        if not tested:
            if counts["no_tests"]:
                violations.append(f"{name}: no covering tests")
            continue
        score = 100.0 * counts["killed"] / tested
        previous = baseline.get(name)
        if score < threshold:
            if previous is None:
                needs = f"a function with no recorded baseline needs >= {threshold:.0f}%"
                violations.append(_score_violation(name, score, needs))
            elif score < (required := previous * (1.0 + improvement / 100.0)):
                violations.append(_score_violation(name, score, f"needs >= {required:.0f}%"))
        updated[name] = round(score, 4)
    return violations, updated


def evaluate_domain(
    results: dict[str, dict[str, int]],
    baseline: dict[str, float],
    tolerance: float = 0.0,
) -> tuple[list[str], dict[str, float]]:
    """Judge functions re-tested because their *tests* changed, not the function itself.

    They are not held to the threshold (the diff did not touch them), but a test change must
    not leave one weaker than its recorded score by more than *tolerance* points. A stronger
    score raises the baseline; a function with no baseline is recorded. The baseline never goes
    down, so a weakened score is refused rather than quietly accepted.
    """
    violations: list[str] = []
    updated = dict(baseline)
    for name, counts in sorted(results.items()):
        if counts.get("pending"):
            left = counts["pending"]
            violations.append(
                f"{name}: {left} mutant(s) were not re-tested after the plan reset them"
            )
            continue
        tested = counts["killed"] + counts["survived"]
        if not tested:
            continue
        score = 100.0 * counts["killed"] / tested
        previous = baseline.get(name)
        if previous is not None and score < previous - tolerance:
            was, now = f"{previous:.0f}%", f"{score:.0f}%"
            violations.append(
                f"{name}: a test change lowered its mutation score from {was} to {now}"
            )
            continue
        updated[name] = round(max(score, previous or 0.0), 4)
    return violations, updated


def diff_fingerprint(root: Path, base_ref: str) -> str:
    diff = subprocess.run(
        ["git", "-c", "core.quotepath=false", "diff", "--no-ext-diff", base_ref, "--", "*.py"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    return hashlib.sha256(diff.encode()).hexdigest()


PLAN_FILE = "mutation-plan.json"  # written by mutation_plan.py: the functions it had re-tested


def group_by_file(names: set[str]) -> dict[str, set[str]]:
    """{'rel::qual', ...} -> {rel: {qual, ...}}."""
    grouped: dict[str, set[str]] = {}
    for full in names:
        rel, qual = full.split("::", 1)
        grouped.setdefault(rel, set()).add(qual)
    return grouped


def load_baseline(path: Path) -> dict:
    try:
        return json.loads(path.read_text()) if path.exists() else {}
    except json.JSONDecodeError:
        return {}


def planned_domain(mutants_dir: Path) -> set[str]:
    """'rel::qual' for each function mutation_plan.py re-tested because its tests changed."""
    try:
        planned = json.loads((mutants_dir / PLAN_FILE).read_text()).get("reset_functions", [])
    except (OSError, json.JSONDecodeError):
        return set()
    names: set[str] = set()
    for mangled in planned:
        module, _, _function = mangled.rpartition(".x")
        qual = qualified_name_from_mutant_key(f"{mangled}__mutmut_1")
        if module and qual:
            names.add(f"{module.replace('.', '/')}.py::{qual}")
    return names


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main", help="git ref to compare against")
    parser.add_argument("--path", default=".", help="source directory to scan")
    parser.add_argument("--mutants-dir", default="mutants", help="mutmut's output directory")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--improvement", type=float, default=20.0)
    parser.add_argument("--baseline", default=".mutation-baseline.json")
    parser.add_argument(
        "--regression-tolerance",
        type=float,
        default=0.0,
        help="points a re-tested function (tests changed, function untouched) may lose",
    )
    args = parser.parse_args(argv)

    root = Path(args.path)
    mutants_dir = root / args.mutants_dir
    if not mutants_dir.exists():
        print(f"error: {mutants_dir} not found — run `mutmut run` first.", file=sys.stderr)
        return 2

    all_ranges: dict[str, tuple[int, int]] = {}
    for meta_path in sorted(mutants_dir.rglob("*.meta")):
        rel = str(meta_path.relative_to(mutants_dir))[: -len(".meta")]
        all_ranges.update(function_ranges(root, rel))
    if not all_ranges:
        print("Mutation ratchet: no mutated files with recoverable function ranges.")
        return 0

    touched = touched_names(root, args.base, all_ranges)
    retested = (planned_domain(mutants_dir) & set(all_ranges)) - touched
    if not touched and not retested:
        print("Mutation ratchet: no touched functions with mutation data.")
        return 0

    baseline_path = root / args.baseline
    baseline = load_baseline(baseline_path)
    fingerprint = diff_fingerprint(root, args.base)
    metadata = baseline.pop("__meta__", {})
    if metadata.get("diff_fingerprint") == fingerprint:
        violations, updated = [], {**baseline, "__meta__": metadata}
    else:
        results = collect_touched_results(root, mutants_dir, group_by_file(touched))
        violations, updated = evaluate_results(results, baseline, args.threshold, args.improvement)
        domain = collect_touched_results(root, mutants_dir, group_by_file(retested))
        weaker, raised = evaluate_domain(domain, baseline, args.regression_tolerance)
        violations += weaker
        updated.update({k: v for k, v in raised.items() if k in domain})
        updated["__meta__"] = {"diff_fingerprint": fingerprint}

    if not violations:
        baseline_path.write_text(json.dumps(updated, indent=2, sort_keys=True) + "\n")

    if violations:
        print(f"Mutation ratchet: {len(violations)} violation(s):", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1

    print(f"Mutation ratchet: OK (touched functions >= {args.threshold:.0f}% mutation score).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
