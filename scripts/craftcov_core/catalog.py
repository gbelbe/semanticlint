"""The catalog.yaml side of craftCov: loading it and mapping detectors to entries."""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

import yaml

CATALOG_PATH = Path(__file__).resolve().parent.parent.parent / "catalog.yaml"

RULE_BASED_TOOLS = {"ruff", "pylint"}
WHOLE_FILE_TOOLS = {"vulture"}
CORPUS_TOOLS = {"dupes"}  # needs the whole file set at once, not per-file


class DetectorIndex(NamedTuple):
    """Which catalog entry each detector's findings mean.

    rule_maps: tool -> {rule_code: catalog_entry}, for rule-granular tools
    (ruff, pylint). whole_tool: tool -> catalog_entry, for tools whose
    findings all mean one specific heuristic regardless of message
    (vulture) — one finding, one location. corpus_tool: tool ->
    {"entry": catalog_entry, **config}, for tools that need the whole file
    set at once rather than per-file (dupes — a duplicate only means
    anything relative to its other copy, possibly in a different file).
    """

    rule_maps: dict[str, dict[str, dict]]
    whole_tool: dict[str, dict]
    corpus_tool: dict[str, dict]


def is_detectable(entry: dict) -> bool:
    """True when craftCov has a mechanical detector for this catalog entry."""
    return bool(entry.get("detectors"))


def load_catalog() -> list[dict]:
    return yaml.safe_load(CATALOG_PATH.read_text())


def _claimed_twice(what: str, first_id: str, second_id: str) -> SystemExit:
    return SystemExit(f"✗ {what} is claimed by both {first_id} and {second_id} in catalog.yaml")


def _register_rules(bucket: dict[str, dict], tool: str, entry: dict, detector: dict) -> None:
    for rule in detector["rules"]:
        if rule in bucket:
            raise _claimed_twice(f"{tool} rule {rule}", bucket[rule]["id"], entry["id"])
        bucket[rule] = entry


def _register_whole_file(whole_tool: dict[str, dict], tool: str, entry: dict) -> None:
    if tool in whole_tool:
        raise _claimed_twice(f"{tool} (a whole-file detector)", whole_tool[tool]["id"], entry["id"])
    whole_tool[tool] = entry


def _register_corpus(corpus_tool: dict[str, dict], tool: str, entry: dict, detector: dict) -> None:
    if tool in corpus_tool:
        raise _claimed_twice(
            f"{tool} (a corpus-wide detector)", corpus_tool[tool]["entry"]["id"], entry["id"]
        )
    corpus_tool[tool] = {"entry": entry, **{k: v for k, v in detector.items() if k != "tool"}}


def build_detector_index(catalog: list[dict]) -> DetectorIndex:
    """Index every detector in *catalog* by what kind of tool it is.

    Each (tool, rule) or (tool) claims exactly one entry by construction —
    collisions are a catalog.yaml authoring error, not something to
    silently pick a winner for.
    """
    index = DetectorIndex({}, {}, {})
    for entry in catalog:
        for detector in entry.get("detectors", []):
            tool = detector["tool"]
            if tool in RULE_BASED_TOOLS:
                _register_rules(index.rule_maps.setdefault(tool, {}), tool, entry, detector)
            elif tool in WHOLE_FILE_TOOLS:
                _register_whole_file(index.whole_tool, tool, entry)
            elif tool in CORPUS_TOOLS:
                _register_corpus(index.corpus_tool, tool, entry, detector)
            else:
                raise SystemExit(f"✗ catalog.yaml: unknown detector tool '{tool}' on {entry['id']}")
    return index
