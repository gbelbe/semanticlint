#!/usr/bin/env python3
"""Refactor First gate — see CRAFTSMANSHIP.md's "Refactor First" section for
the workflow this enforces the outcome of, not the procedure.

Fails when a touched `.py` file's total across the 8 mechanically-detectable
heuristics (craftcov.py --list-detectors) did not go down relative to where
this branch diverged from its base — unless it was already at 0, in which
case it must simply stay at 0 (a clean file can't be made dirtier and still
pass). Total-based, not per-heuristic: fixing one instance of every present
heuristic type (the workflow this gate checks the outcome of) always drops
the total by exactly the number of heuristic types that were present, so a
strict total decrease is exactly what that workflow produces.

Also fails on any finding that sits on a line the change added or rewrote: new
code is not legacy, so there is nothing to grandfather. A new file must scan clean.

A `Tidy-Exempt:` trailer anywhere in the commit range — the same escape hatch
check_tidy_ratchet.sh uses — waives the per-file ratchet above (nothing to tidy,
so no tidy to demand), not the new-code rule.

Needs its own full-corpus scan of the merge-base tree via a throwaway `git
worktree` (dupes is corpus-wide — a duplicate only means anything relative
to its other copy, so there's no way to get an accurate "before" count for
one file without scanning every file at that revision too), plus a scan of
the current tree. Both calls bypass craftcov.py's on-disk cache entirely
(this script calls its scan functions directly) since a merge-base worktree
is thrown away right after and a repeat run should never see stale numbers.

Usage:
    python3 scripts/check_refactor_first.py --base <ref> [--head <ref>]

Examples:
    python3 scripts/check_refactor_first.py --base origin/main
    python3 scripts/check_refactor_first.py --base origin/main --head HEAD
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parent)
)  # siblings by bare name, also when imported as scripts.<name>
from craftcov import (  # noqa: E402
    Finding,
    aggregate,
    build_detector_index,
    discover_python_files,
    load_catalog,
    merge_corpus_findings,
    scan_files,
)
from gate_config import (  # noqa: E402
    REFACTOR_FIRST,
    ConfigError,
    Waive,
    find_root,
    load_settings,
    waive_from,
)
from gitdiff import (  # noqa: E402
    added_lines,
    base_ref_parser,
    git,
    has_tidy_exempt,
    touched_python_files,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
MUST_DECREASE = "must-decrease"


def scan_findings(root: Path) -> dict[str, list[Finding]]:
    """Every finding across the 8 detectable heuristics, per file, for a
    full scan of `root` — bypasses craftcov.py's cache (see module docstring).

    `root` MUST be fully resolved (no symlink components) before this is
    called, matching craftcov.py's own `main()` convention: ruff/vulture
    report back absolute paths in their own resolved form, and
    `_normalize_path`'s `relative_to(root)` silently drops a finding (not
    an error — it's designed to tolerate a path outside root) if `root`
    itself wasn't resolved the same way. On macOS in particular, /tmp is a
    symlink to /private/tmp, so an unresolved tempfile-based worktree path
    reliably reproduces this and silently reports zero findings."""
    catalog = load_catalog()
    rule_maps, whole_tool, corpus_tool = build_detector_index(catalog)
    files = discover_python_files(root)
    by_file = scan_files(root, files, rule_maps, whole_tool, vulture_min_confidence=0)
    merge_corpus_findings(root, files, by_file, corpus_tool)
    return by_file


def per_file_totals(root: Path) -> dict[str, int]:
    """rel -> number of findings; a file with 0 findings is simply absent."""
    return aggregate(scan_findings(root)).by_file


def scan_ref(repo: Path, ref: str, scratch_parent: Path, scan=scan_findings):
    """`scan` (findings by default) of `ref`, checked out into a throwaway worktree —
    unless `ref` is exactly what's already on disk (HEAD in the normal CI
    checkout), which is scanned in place to skip a redundant checkout."""
    if ref == "HEAD":
        return scan(repo)
    worktree = (scratch_parent / "refactor-first-ref").resolve()
    git(["worktree", "add", "--detach", str(worktree), ref], cwd=repo)
    try:
        return scan(worktree)
    finally:
        git(["worktree", "remove", "--force", str(worktree)], cwd=repo, check=False)


def regressions(
    pairs: list[tuple[str, str]],
    base_totals: dict[str, int],
    head_totals: dict[str, int],
    mode: str = MUST_DECREASE,
) -> list[str]:
    """One report line per touched file whose total broke the per-file rule.

    A clean file must stay clean. Otherwise *mode* decides: "must-decrease" (the default)
    wants a strictly lower total; "must-not-increase" accepts an unchanged one.
    """
    strict = mode == MUST_DECREASE
    failures: list[str] = []
    for old_rel, new_rel in pairs:
        before = base_totals.get(old_rel, 0)
        after = head_totals.get(new_rel, 0)
        if (after == 0) if before == 0 else ((after < before) if strict else (after <= before)):
            continue
        label = new_rel if old_rel == new_rel else f"{old_rel} -> {new_rel}"
        needed = "0" if before == 0 else f"{'<' if strict else '<='} {before}"
        failures.append(f"  {label}: {before} -> {after} (needed {needed})")
    return failures


def new_code_findings(
    repo: Path,
    span: tuple[str, str],
    pairs: list[tuple[str, str]],
    head_findings: dict[str, list[Finding]],
) -> list[str]:
    """One report line per finding sitting on a line this change added or rewrote.

    New code has no legacy to grandfather, so this holds whatever a `Tidy-Exempt:` trailer
    says. A brand-new file is all added lines, so it must scan clean.
    """
    base, head = span
    failures: list[str] = []
    for old_rel, new_rel in pairs:
        added = added_lines(base, head, repo, tuple(dict.fromkeys((old_rel, new_rel))))
        for f in sorted(head_findings.get(new_rel, []), key=lambda x: x["line"]):
            if f["line"] in added:
                failures.append(
                    f"  {new_rel}:{f['line']}  {f['heuristic_code']} {f['heuristic_id']}"
                )
    return failures


def report_new_code(failures: list[str]) -> None:
    print(
        "✗ Refactor First gate: new code is not clean "
        "(a Tidy-Exempt: trailer does not waive this):",
        file=sys.stderr,
    )
    for f in failures:
        print(f, file=sys.stderr)
    print(
        "\n  A finding on a line this change added is not legacy to grandfather. Fix it in the\n"
        "  same change (see CRAFTSMANSHIP.md's 'Refactor First'; craftcov.py --file <path>).",
        file=sys.stderr,
    )


def report_failures(failures: list[str]) -> None:
    print(
        "✗ Refactor First gate: total detectable-heuristic count did not go down for:",
        file=sys.stderr,
    )
    for f in failures:
        print(f, file=sys.stderr)
    print(
        "\n  Fix one instance of every heuristic craftcov.py finds present in a touched\n"
        "  file (see CRAFTSMANSHIP.md's 'Refactor First'), bundled into one tidy(multi):\n"
        "  commit, or add a Tidy-Exempt: trailer if nothing genuinely applies.",
        file=sys.stderr,
    )


def _waived(waive: Waive) -> str:
    rules = [
        name
        for name, off in (
            ("the per-file ratchet", waive.legacy_debt),
            ("the new-code rule", waive.new_code),
        )
        if off
    ]
    return " and ".join(rules)


def main() -> int:
    parser = base_ref_parser(__doc__)
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--path", default=str(REPO_ROOT), help="repo root (default: this repo)")
    args = parser.parse_args()

    repo = Path(args.path).resolve()

    if not git(["rev-parse", "--verify", "--quiet", args.base], cwd=repo, check=False).strip():
        print(
            f"⚠ refactor-first gate: '{args.base}' not found locally — "
            "skipping (git fetch it first)",
            file=sys.stderr,
        )
        return 0

    merge_base = git(["merge-base", args.base, args.head], cwd=repo).strip()

    pairs = touched_python_files(repo, merge_base, args.head)
    if not pairs:
        return 0  # nothing touched, nothing to check

    try:
        settings = load_settings(find_root(repo))
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    waive = waive_from(settings, has_tidy_exempt(merge_base, args.head, cwd=repo))
    if waive.legacy_debt or waive.new_code:
        print(
            f"refactor-first gate: Tidy-Exempt: trailer found in {merge_base[:8]}..{args.head}"
            f" — waiving: {_waived(waive)}."
        )

    with tempfile.TemporaryDirectory(prefix="craft-gate-refactor-first-") as tmp:
        scratch = Path(tmp)
        head_findings = scan_ref(repo, args.head, scratch)
        base_totals = (
            {} if waive.legacy_debt else scan_ref(repo, merge_base, scratch, per_file_totals)
        )

    status = 0
    head_totals = aggregate(head_findings).by_file
    mode = settings[REFACTOR_FIRST]["per-file"]
    failures = [] if waive.legacy_debt else regressions(pairs, base_totals, head_totals, mode)
    if failures:
        report_failures(failures)
        status = 1
    spans = (merge_base, args.head)
    new_failures = [] if waive.new_code else new_code_findings(repo, spans, pairs, head_findings)
    if new_failures:
        report_new_code(new_failures)
        status = 1

    if status == 0:
        print(f"✓ Refactor First gate: {len(pairs)} touched file(s) OK.")
    return status


if __name__ == "__main__":
    sys.exit(main())
