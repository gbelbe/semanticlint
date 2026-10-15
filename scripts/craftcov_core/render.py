"""Rendering a scan: the text report, JSON, SARIF, and the detector listing."""

from __future__ import annotations

import json
from dataclasses import asdict

from .catalog import is_detectable
from .models import (
    BY_HEURISTIC,
    HEURISTIC_ID,
    TOTAL,
    Finding,
    ReportOptions,
    RunContext,
    ScanResults,
    Summary,
    Timing,
)
from .summary import diff_by_heuristic

SARIF_SCHEMA = (
    "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/Schemata/sarif-schema-2.1.0.json"
)


def _signed(delta: int) -> str:
    return f"+{delta}" if delta > 0 else str(delta)


def _diff_tag(old_count: int, new_count: int) -> str:
    if old_count == 0:
        return " (NEW)"
    return " (RESOLVED)" if new_count == 0 else ""


def print_diff_section(
    prev_snapshot: dict | None, agg: Summary, catalog_by_id: dict[str, dict]
) -> None:
    if prev_snapshot is None:
        print("Changes since last run: none — this is the first run (no previous snapshot).")
        print()
        return

    changed = diff_by_heuristic(prev_snapshot[BY_HEURISTIC], agg.by_heuristic)
    when = prev_snapshot.get("generated_at", "an earlier run")
    if not changed:
        print(f"Changes since last run ({when}): none — identical totals.")
        print()
        return

    print(f"Changes since last run ({when})")
    for hid, old_count, new_count in changed:
        code = catalog_by_id.get(hid, {}).get("code", "")
        delta = _signed(new_count - old_count)
        tag = _diff_tag(old_count, new_count)
        print(f"  {code:7s} {hid:38s} {old_count:5d} -> {new_count:<5d} ({delta}){tag}")
    old_total = prev_snapshot.get(TOTAL, 0)
    print(
        f"  {'':7s} {'TOTAL':38s} {old_total:5d} -> {agg.total:<5d} "
        f"({_signed(agg.total - old_total)})"
    )
    print()


def _print_header(scan_timing: Timing, scope_label: str | None) -> None:
    print("craftCov — craftsmanship heuristic scan")
    print(
        f"Scanned {scan_timing.total_files} files "
        f"({scan_timing.changed} changed, {scan_timing.cached} from cache) "
        f"in {scan_timing.elapsed:.2f}s"
    )
    if scan_timing.dupes_elapsed > 0:
        print(
            f"Duplicate-code pass: {scan_timing.dupes_elapsed:.2f}s "
            "(always full-corpus — see DESIGN.md)"
        )
    if scope_label:
        print(
            f"Reporting scope: {scope_label} only "
            "(full corpus was still scanned — see --file's help)"
        )
    print()


def _print_tables(agg: Summary, catalog_by_id: dict[str, dict]) -> None:
    print("By heuristic")
    print(f"{'CODE':7s} {'ID':38s} {'COUNT':>6s}  SOURCE")
    for hid, count in sorted(agg.by_heuristic.items(), key=lambda kv: -kv[1]):
        entry = catalog_by_id[hid]
        print(f"{entry.get('code', ''):7s} {hid:38s} {count:6d}  {entry['source']}")
    print(f"{'':7s} {'TOTAL':38s} {agg.total:6d}")
    print()

    print("By file (top 15)")
    for rel, count in sorted(agg.by_file.items(), key=lambda kv: -kv[1])[:15]:
        print(f"  {count:5d}  {rel}")
    print()

    print("By class (top 15, module-level findings excluded)")
    class_only = {k: v for k, v in agg.by_class.items() if "::" in k}
    for key, count in sorted(class_only.items(), key=lambda kv: -kv[1])[:15]:
        print(f"  {count:5d}  {key}")
    print()

    print("By library (top-level directory)")
    for lib, count in sorted(agg.by_library.items(), key=lambda kv: -kv[1]):
        print(f"  {count:5d}  {lib}")


def _finding_line(rel: str, f: dict) -> str:
    scope = f" [{f['class']}]" if f["class"] else ""
    rule = f"{f['tool']}:{f['rule']}" if f["rule"] else f["tool"]
    if f.get("confidence") is not None:
        rule += f" {f['confidence']}%"
    dup = f"  <-> {f['duplicate_of']} ({f['dup_lines']} lines)" if f.get("duplicate_of") else ""
    return f"  {rel}:{f['line']}  {f['heuristic_code']} {f['heuristic_id']} ({rule}){scope}{dup}"


def _print_every_finding(by_file: dict[str, list[Finding]]) -> None:
    print()
    print("Every finding")
    for rel, findings in sorted(by_file.items()):
        for f in sorted(findings, key=lambda x: x["line"]):
            print(_finding_line(rel, f))


def _print_detector_coverage(catalog_by_id: dict[str, dict]) -> None:
    n_detectable = sum(1 for e in catalog_by_id.values() if is_detectable(e))
    n_total = len(catalog_by_id)
    print()
    print(
        f"{n_detectable}/{n_total} heuristics have an automatic detector "
        f"({100 * n_detectable // n_total}%) — the rest need the procedure in "
        f"CRAFTSMANSHIP.md (ask the developer), not a scan. Run with "
        f"--list-detectors to see which is which."
    )


def print_text_report(scan: ScanResults, ctx: RunContext, verbose: bool) -> None:
    _print_header(ctx.timing, ctx.scope_label)
    if ctx.diff_active:
        print_diff_section(ctx.prev_snapshot, scan.agg, scan.catalog_by_id)

    if scan.agg.total == 0:
        print("No findings for the detectable heuristics. ✓")
    else:
        _print_tables(scan.agg, scan.catalog_by_id)
        if verbose:
            _print_every_finding(scan.by_file)

    _print_detector_coverage(scan.catalog_by_id)


def format_sarif(by_file: dict[str, list[Finding]], catalog: list[dict]) -> dict:
    """A SARIF 2.1.0 document for `by_file`'s findings, for `github/codeql-
    action/upload-sarif` — feeds GitHub's own code-scanning dashboard
    (history, per-finding tracking, a native alert count) rather than a
    hand-rolled report needing its own hosting. See DESIGN.md's Reporting
    section for the CI wiring.

    Rules cover every detectable catalog entry (`detectors` present),
    whether or not it fired this run — SARIF's `rules` array is the tool's
    rule catalog, not a per-run fired-list, the same distinction
    `--list-detectors` already draws. All findings are `level: warning`:
    none of these are security issues, but they're not mere style notes
    either — matches how GitHub surfaces them by default (a `note`-level
    result is filtered out of the default alerts view).
    """
    detectable = [e for e in catalog if is_detectable(e)]
    rules = [
        {
            "id": e["id"],
            "name": e["id"],
            "shortDescription": {"text": e.get("smell", e["name"])},
            "help": {"text": e.get("action", "")},
            "properties": {"tags": ["craftsmanship", e.get("code", "")]},
        }
        for e in detectable
    ]

    results = []
    for rel, findings in sorted(by_file.items()):
        for f in findings:
            hid, hcode = f[HEURISTIC_ID], f["heuristic_code"]
            results.append(
                {
                    "ruleId": hid,
                    "level": "warning",
                    "message": {"text": f"{hid} ({hcode})"},
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {"uri": rel},
                                "region": {"startLine": max(f["line"], 1)},
                            }
                        }
                    ],
                }
            )

    return {
        "$schema": SARIF_SCHEMA,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "craftCov",
                        "informationUri": "https://github.com/gbelbe/craft-gate",
                        "rules": rules,
                    }
                },
                "results": results,
            }
        ],
    }


def print_detector_list(catalog: list[dict]) -> None:
    for e in catalog:
        detectors = e.get("detectors")
        if not detectors:
            status = "— (needs judgment, see procedure)"
        else:
            parts = []
            for d in detectors:
                rules = d.get("rules")
                parts.append(f"{d['tool']}: {', '.join(rules)}" if rules else d["tool"])
            status = " + ".join(parts)
        print(f"{e.get('code', ''):7s} {e['id']:38s} {status}")


def json_payload(scan: ScanResults, ctx: RunContext) -> dict:
    payload = {
        "summary": scan.agg.to_dict(),
        "findings": scan.by_file,
        "timing": asdict(ctx.timing),
        "scope": ctx.scope_label,
    }
    if ctx.diff_active:
        payload["diff"] = {
            "previous_generated_at": (ctx.prev_snapshot or {}).get("generated_at"),
            BY_HEURISTIC: [
                {HEURISTIC_ID: hid, "old": old_count, "new": new_count}
                for hid, old_count, new_count in diff_by_heuristic(
                    (ctx.prev_snapshot or {}).get(BY_HEURISTIC), scan.agg.by_heuristic
                )
            ],
        }
    return payload


def print_report(options: ReportOptions, scan: ScanResults, ctx: RunContext) -> None:
    """Dispatch on the output format."""
    if options.fmt == "json":
        print(json.dumps(json_payload(scan, ctx), indent=2))
    elif options.fmt == "sarif":
        print(json.dumps(format_sarif(scan.by_file, scan.catalog), indent=2))
    else:
        print_text_report(scan, ctx, options.verbose)
