"""The two small state files craftCov keeps between runs.

The per-file findings cache is about incremental *scanning*; the report
snapshot is about "what did the summary look like last time a report was
shown". Deliberately separate files: the snapshot should survive --no-cache
(forcing a recompute doesn't mean you no longer want to know what changed)
and does need to cover dupes (it's just the aggregate, tool-agnostic),
while the cache doesn't cover dupes at all.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from .models import BY_HEURISTIC, TOTAL, Summary

CACHE_VERSION = 5  # 5: nested class names lost their doubled dot ("A..B" -> "A.B")


def empty_cache() -> dict:
    return {"version": CACHE_VERSION, "files": {}}


def load_cache(cache_path: Path) -> dict:
    if not cache_path.exists():
        return empty_cache()
    try:
        data = json.loads(cache_path.read_text())
    except (json.JSONDecodeError, OSError):
        return empty_cache()
    if data.get("version") != CACHE_VERSION:
        return empty_cache()  # schema changed — start fresh, don't crash
    return data


def save_cache(cache_path: Path, cache: dict) -> None:
    cache_path.write_text(json.dumps(cache, indent=0))


def load_report_snapshot(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    if BY_HEURISTIC not in data:
        return None  # schema changed — treat as "no previous snapshot" rather than crash
    return data


def save_report_snapshot(path: Path, agg: Summary) -> None:
    path.write_text(
        json.dumps(
            {
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                BY_HEURISTIC: agg.by_heuristic,
                TOTAL: agg.total,
            },
            indent=2,
        )
    )
