"""Counting findings: totals per heuristic/file/class/library, and run-to-run diffs."""

from __future__ import annotations

from pathlib import Path

from .models import Finding, Summary


def diff_by_heuristic(
    old: dict[str, int] | None, new: dict[str, int]
) -> list[tuple[str, int, int]]:
    """(heuristic_id, old_count, new_count) for every heuristic whose count
    changed — old_count/new_count are 0 for a heuristic that's new or fully
    resolved. Empty list (not None) when old is None (first-ever run) is the
    caller's job to distinguish, since "no previous snapshot" and "nothing
    changed" need different messages."""
    ids = set(old or {}) | set(new)
    changed = []
    for hid in ids:
        old_count = (old or {}).get(hid, 0)
        new_count = new.get(hid, 0)
        if old_count != new_count:
            changed.append((hid, old_count, new_count))
    changed.sort(key=lambda t: -abs(t[2] - t[1]))
    return changed


def aggregate(by_file: dict[str, list[Finding]]) -> Summary:
    by_heuristic: dict[str, int] = {}
    by_file_count: dict[str, int] = {}
    by_class: dict[str, int] = {}
    by_library: dict[str, int] = {}
    total = 0

    for rel, findings in by_file.items():
        if not findings:
            continue
        by_file_count[rel] = len(findings)
        parts = Path(rel).parts
        library = parts[0] if len(parts) > 1 else "(root)"
        for f in findings:
            total += 1
            by_heuristic[f["heuristic_id"]] = by_heuristic.get(f["heuristic_id"], 0) + 1
            by_library[library] = by_library.get(library, 0) + 1
            key = f"{rel}::{f['class']}" if f["class"] else rel
            by_class[key] = by_class.get(key, 0) + 1

    return Summary(total, by_heuristic, by_file_count, by_class, by_library)
