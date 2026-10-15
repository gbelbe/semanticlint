"""The command line: argument parsing and the top-level flow of a run."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import __doc__ as PACKAGE_DOC
from .cache import load_report_snapshot, save_report_snapshot
from .catalog import build_detector_index, load_catalog
from .models import ReportOptions, RunContext, ScanResults
from .pipeline import ScanSettings, restrict_to_file, scan_repository
from .render import print_detector_list, print_report
from .summary import aggregate

DEFAULT_CACHE_PATH = Path(".craftcov_cache.json")
DEFAULT_SNAPSHOT_PATH = Path(".craftcov_last_report.json")
_FLAG = {"action": "store_true"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=PACKAGE_DOC, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--path", default=".", help="repo root to scan (default: .)")
    parser.add_argument("--cache-file", default=str(DEFAULT_CACHE_PATH))
    parser.add_argument("--no-cache", help="ignore and overwrite the existing cache", **_FLAG)
    parser.add_argument(
        "--snapshot-file",
        default=str(DEFAULT_SNAPSHOT_PATH),
        help="where the by-heuristic totals from this run are saved, to diff against next time",
    )
    parser.add_argument(
        "--no-diff",
        **_FLAG,
        help="don't print the 'changes since last run' section "
        "(the snapshot still updates for next time)",
    )
    parser.add_argument("--format", choices=["text", "json", "sarif"], default="text")
    parser.add_argument("--verbose", "-v", help="list every finding, not just the summary", **_FLAG)
    parser.add_argument(
        "--list-detectors",
        **_FLAG,
        help="print which heuristics are detectable and how, then exit",
    )
    parser.add_argument(
        "--file",
        default=None,
        help="report only findings in this one file (a REPORT filter, applied after the "
        "full corpus scan — dupes still needs every file scanned to find a match's "
        "other half, so this never restricts what gets scanned, only what gets "
        "shown/counted). Path relative to --path, or absolute.",
    )
    parser.add_argument(
        "--class",
        dest="cls",
        default=None,
        help="further restrict --file to one enclosing class (module-level findings "
        "excluded). Ignored without --file.",
    )
    parser.add_argument(
        "--vulture-min-confidence",
        type=int,
        default=0,
        metavar="N",
        help="vulture's own confidence floor (0-100, default 0 = vulture's default: "
        "report everything). On a real codebase this tends to cluster at 60%% "
        "(functions/classes/methods, vulture's own 'fairly sure but could be wrong' "
        "tier) and 100%% (unused variables, redundant with ruff's own F841). The cache "
        "doesn't know about this flag — changing it between runs needs --no-cache "
        "to actually take effect.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    catalog = load_catalog()
    if args.list_detectors:
        print_detector_list(catalog)
        return 0

    root = Path(args.path).resolve()
    snapshot_path = Path(args.snapshot_file)
    # --file scopes the report to a slice of the repo; the snapshot/diff
    # feature is a whole-repo view (and shared by every scoped run, so a
    # scoped run must not read or overwrite it — that'd corrupt the next
    # whole-repo run's baseline with a single file's totals).
    diff_active = not args.no_diff and not args.file
    prev_snapshot = load_report_snapshot(snapshot_path) if diff_active else None

    settings = ScanSettings(
        root, Path(args.cache_file), not args.no_cache, args.vulture_min_confidence
    )
    files, by_file, timing = scan_repository(settings, build_detector_index(catalog))

    scope_label = None
    if args.file:
        by_file, scope_label = restrict_to_file(root, files, by_file, args.file, args.cls)

    agg = aggregate(by_file)
    print_report(
        ReportOptions(args.format, args.verbose),
        ScanResults(agg, by_file, catalog),
        RunContext(timing, prev_snapshot, diff_active, scope_label),
    )

    if not args.file:
        save_report_snapshot(snapshot_path, agg)

    return 0
