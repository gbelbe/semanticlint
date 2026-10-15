"""Running the detectors over files and turning their raw items into findings."""

from __future__ import annotations

from pathlib import Path

from .adapters import run_pylint, run_ruff, run_vulture
from .catalog import RULE_BASED_TOOLS
from .dupes import run_dupes
from .models import CONFIDENCE, DuplicateFinding, Finding
from .scopes import Scope, build_scope_index, enclosing_class

ScopeCache = dict[str, list[Scope]]


def _class_of(scopes_cache: ScopeCache, root: Path, rel: str, line: int) -> str | None:
    if rel not in scopes_cache:
        scopes_cache[rel] = build_scope_index((root / rel).read_text())
    return enclosing_class(scopes_cache[rel], line)


def _raw_items(
    root: Path,
    rel_files: list[str],
    rule_maps: dict[str, dict[str, dict]],
    whole_tool: dict[str, dict],
    vulture_min_confidence: int,
) -> list[dict]:
    items: list[dict] = []
    if "ruff" in rule_maps:
        items += run_ruff(root, rel_files, sorted(rule_maps["ruff"]))
    if "pylint" in rule_maps:
        items += run_pylint(root, rel_files, sorted(rule_maps["pylint"]))
    if "vulture" in whole_tool:
        items += run_vulture(root, rel_files, vulture_min_confidence)
    return items


def _entry_for(
    item: dict, rule_maps: dict[str, dict[str, dict]], whole_tool: dict[str, dict]
) -> dict | None:
    if item["tool"] in RULE_BASED_TOOLS:
        return rule_maps.get(item["tool"], {}).get(item["rule"])
    return whole_tool.get(item["tool"])


def _finding(item: dict, entry: dict, cls: str | None) -> Finding:
    return {
        "line": item["line"],
        "col": item["col"],
        "tool": item["tool"],
        "rule": item["rule"],
        CONFIDENCE: item.get(CONFIDENCE),  # only vulture sets this
        "heuristic_id": entry["id"],
        "heuristic_code": entry.get("code", ""),
        "class": cls,
    }


def scan_files(
    root: Path,
    rel_files: list[str],
    rule_maps: dict[str, dict[str, dict]],
    whole_tool: dict[str, dict],
    vulture_min_confidence: int = 0,
) -> dict[str, list[Finding]]:
    """relative path -> list of finding dicts, for exactly these files."""
    raw_items = _raw_items(root, rel_files, rule_maps, whole_tool, vulture_min_confidence)

    by_file: dict[str, list[Finding]] = {rel: [] for rel in rel_files}
    scopes_cache: ScopeCache = {}
    seen: set[tuple[str, int, str]] = set()  # (rel, line, heuristic_id) — dedup across tools

    for item in raw_items:
        rel = item["rel"]
        if rel not in by_file:
            continue  # not one of the files we were asked to scan this run
        entry = _entry_for(item, rule_maps, whole_tool)
        if entry is None:
            continue  # shouldn't happen (we only ask for mapped rules), but don't crash on it

        dedup_key = (rel, item["line"], entry["id"])
        if dedup_key in seen:
            continue  # another tool already flagged this exact line for this heuristic
        seen.add(dedup_key)

        cls = _class_of(scopes_cache, root, rel, item["line"])
        by_file[rel].append(_finding(item, entry, cls))
    return by_file


def merge_corpus_findings(
    root: Path,
    all_files: list[str],
    by_file: dict[str, list[Finding]],
    corpus_tool: dict[str, dict],
) -> None:
    """Runs corpus-wide tools (currently just `dupes`) over every file,
    every run — never through the per-file cache (see dupes.py's header
    for why). Appends into by_file in place."""
    if "dupes" not in corpus_tool:
        return
    cfg = corpus_tool["dupes"]
    entry = cfg["entry"]
    min_lines = cfg.get(
        "min_lines", 8
    )  # see catalog.yaml's comment for the PMD-calibration behind this
    items = run_dupes(root, all_files, min_lines)

    scopes_cache: ScopeCache = {}
    for item in items:
        cls = _class_of(scopes_cache, root, item["rel"], item["line"])
        finding = DuplicateFinding(
            **_finding({**item, CONFIDENCE: None}, entry, cls),
            duplicate_of=item["duplicate_of"],
            dup_lines=item["dup_lines"],
        )
        by_file.setdefault(item["rel"], []).append(finding)
