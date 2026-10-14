"""One craftCov run: discover, scan what changed, merge corpus findings, scope the result."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from .cache import empty_cache, load_cache, save_cache
from .catalog import DetectorIndex
from .discovery import discover_python_files, file_hash, normalize_path
from .models import Finding, Timing
from .scan import merge_corpus_findings, scan_files


@dataclass
class ScanSettings:
    """How to scan: where, and how much of the previous run to trust."""

    root: Path
    cache_path: Path
    use_cache: bool = True
    vulture_min_confidence: int = 0


def _load_state(settings: ScanSettings) -> dict:
    if settings.use_cache:
        return load_cache(settings.cache_path)
    return empty_cache()


def scan_repository(
    settings: ScanSettings, index: DetectorIndex
) -> tuple[list[str], dict[str, list[Finding]], Timing]:
    """(files, findings by file, timing) for the whole repository.

    Per-file engines only re-run on files whose content hash changed since the
    cached run; corpus-wide engines (dupes) always see every file.
    """
    root = settings.root
    t0 = time.monotonic()
    files = discover_python_files(root)  # relative paths
    cache = _load_state(settings)
    cached_files = cache["files"]

    hashes = {rel: file_hash(root, rel) for rel in files}
    changed = [rel for rel in files if cached_files.get(rel, {}).get("hash") != hashes[rel]]
    unchanged = [rel for rel in files if rel not in changed]

    new_findings = (
        scan_files(
            root, changed, index.rule_maps, index.whole_tool, settings.vulture_min_confidence
        )
        if changed
        else {}
    )

    by_file: dict[str, list[Finding]] = {rel: cached_files[rel]["findings"] for rel in unchanged}
    for rel in changed:
        by_file[rel] = new_findings.get(rel, [])
        cached_files[rel] = {"hash": hashes[rel], "findings": by_file[rel]}

    # drop cache entries for files that no longer exist
    for stale in set(cached_files) - set(hashes):
        del cached_files[stale]

    save_cache(settings.cache_path, cache)  # before dupes: those never get persisted

    dupes_t0 = time.monotonic()
    merge_corpus_findings(root, files, by_file, index.corpus_tool)
    dupes_elapsed = time.monotonic() - dupes_t0

    timing = Timing(
        total_files=len(files),
        changed=len(changed),
        cached=len(unchanged),
        elapsed=time.monotonic() - t0,
        dupes_elapsed=dupes_elapsed,
    )
    return files, by_file, timing


def restrict_to_file(
    root: Path,
    files: list[str],
    by_file: dict[str, list[Finding]],
    file_arg: str,
    class_name: str | None,
) -> tuple[dict[str, list[Finding]], str]:
    """Narrow a finished scan to one file (and optionally one class) — a REPORT
    filter, so what was scanned is untouched. Returns (by_file, scope label)."""
    target = normalize_path(root, file_arg)
    if target is None or target not in files:
        raise SystemExit(
            f"✗ --file {file_arg!r} not found among this repo's tracked "
            f".py files (relative to {root})"
        )
    findings = by_file.get(target, [])
    if class_name:
        findings = [f for f in findings if f.get("class") == class_name]
    label = f"{target}::{class_name}" if class_name else target
    return {target: findings}, label
