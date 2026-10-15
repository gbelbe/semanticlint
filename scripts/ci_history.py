#!/usr/bin/env python3
"""Where a workflow's time goes, across its recent runs: per job, and per step inside each job.

GitHub already records when every step of every run started and ended, so a repo with some history
needs no instrumentation to see which jobs set the wall-clock time and which steps dominate them.

    python scripts/ci_history.py --repo OWNER/NAME [--workflow ci.yml] [--runs 30] [--branch main]

needs the `gh` CLI, logged in. To analyse without the network (or to keep a snapshot):

    python scripts/ci_history.py --repo OWNER/NAME --save history.json
    python scripts/ci_history.py --from-json history.json

Per job and per step it prints the median and 90th percentile across runs, and how much of the
workflow's total job time it takes. "Job minutes" is what the runs billed or consumed, each job
rounded up to a whole minute as GitHub does; "wall clock" is what a developer waited.

Copied into consuming repos next to the scripts that import it (see bootstrap.sh).
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

_SECONDS_PER_MINUTE = 60
_PERCENT = 100
_P90 = 0.9
_SKIPPED = "skipped"


def parse_time(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def seconds_between(start: str | None, end: str | None) -> float | None:
    """Seconds from *start* to *end*, None when either is missing or the thing was skipped."""
    a, b = parse_time(start), parse_time(end)
    return None if a is None or b is None else max((b - a).total_seconds(), 0.0)


def percentile(values: list[float], fraction: float) -> float:
    """Nearest-rank percentile; *values* must not be empty."""
    ordered = sorted(values)
    return ordered[max(math.ceil(fraction * len(ordered)) - 1, 0)]


@dataclass(frozen=True)
class Stats:
    """How long something took across the runs it appeared in."""

    count: int
    median: float
    p90: float
    total: float


@dataclass(frozen=True)
class JobStats:
    stats: Stats
    steps: dict[str, Stats]


@dataclass(frozen=True)
class Summary:
    runs: int
    wall_clock: Stats | None
    job_minutes: Stats | None
    jobs: dict[str, JobStats]


def _stats(values: list[float]) -> Stats:
    return Stats(len(values), statistics.median(values), percentile(values, _P90), sum(values))


def _ran(item: dict[str, Any]) -> bool:
    return item.get("conclusion") != _SKIPPED


def job_seconds(job: dict[str, Any]) -> float | None:
    return seconds_between(job.get("started_at"), job.get("completed_at")) if _ran(job) else None


def _by_job(history: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in history:
        for job in entry["jobs"]:
            if job_seconds(job) is not None:
                grouped.setdefault(job["name"], []).append(job)
    return grouped


def _step_durations(jobs: list[dict[str, Any]]) -> dict[str, list[float]]:
    steps: dict[str, list[float]] = {}
    for job in jobs:
        for item in job.get("steps", []):
            took = seconds_between(item.get("started_at"), item.get("completed_at"))
            if took is not None and _ran(item):
                steps.setdefault(item["name"], []).append(took)
    return steps


def run_job_minutes(entry: dict[str, Any]) -> int:
    """Minutes one run consumed: each job rounded up to a whole minute."""
    times = [job_seconds(job) for job in entry["jobs"]]
    return sum(math.ceil(t / _SECONDS_PER_MINUTE) for t in times if t is not None)


def run_wall_clock(entry: dict[str, Any]) -> float | None:
    run = entry["run"]
    return seconds_between(run.get("run_started_at"), run.get("updated_at"))


def summarize(history: list[dict[str, Any]]) -> Summary:
    """Per-run totals, and for every job its timing and the timing of each of its steps."""
    wall = [t for t in map(run_wall_clock, history) if t is not None]
    minutes = [float(run_job_minutes(entry)) for entry in history]
    jobs = {
        name: JobStats(_stats([job_seconds(j) for j in group]), _step_stats(group))
        for name, group in _by_job(history).items()
    }
    return Summary(
        len(history), _stats(wall) if wall else None, _stats(minutes) if minutes else None, jobs
    )


def _step_stats(jobs: list[dict[str, Any]]) -> dict[str, Stats]:
    return {name: _stats(values) for name, values in _step_durations(jobs).items()}


def _fmt(seconds: float) -> str:
    minutes, rest = divmod(round(seconds), _SECONDS_PER_MINUTE)
    return f"{minutes}m{rest:02d}s" if minutes else f"{rest}s"


def _table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    return "\n".join(lines + ["| " + " | ".join(row) + " |" for row in rows])


def _cells(stats: Stats, grand: float) -> tuple[str, str, str]:
    """Median, p90 and share of the job time, as table cells."""
    return _fmt(stats.median), _fmt(stats.p90), f"{_PERCENT * stats.total / grand:.0f}%"


def render(summary: Summary, top: int = 8) -> str:
    """The summary as markdown: the workflow's totals, the jobs, then the heaviest steps."""
    if not summary.runs:
        return "No completed runs to analyse."
    grand = sum(job.stats.total for job in summary.jobs.values()) or 1.0
    ordered = sorted(summary.jobs.items(), key=lambda item: item[1].stats.total, reverse=True)
    job_rows = [(name, str(job.stats.count), *_cells(job.stats, grand)) for name, job in ordered]
    jobs = _table(("Job", "Runs", "Median", "p90", "Share of job time"), job_rows)
    return "\n\n".join([_totals(summary), jobs, _heaviest_steps(ordered, top, grand)])


def _totals(summary: Summary) -> str:
    line = f"**{summary.runs} runs.**"
    if summary.wall_clock:
        wall = summary.wall_clock
        line += f" Wall clock: median {_fmt(wall.median)}, p90 {_fmt(wall.p90)}."
    if summary.job_minutes:
        minutes = summary.job_minutes
        line += f" Job minutes per run: median {minutes.median:.0f}, p90 {minutes.p90:.0f}."
    return line


def _heaviest_steps(ordered: list[tuple[str, JobStats]], top: int, grand: float) -> str:
    steps = [(job, name, s) for job, data in ordered for name, s in data.steps.items()]
    heaviest = sorted(steps, key=lambda row: row[2].total, reverse=True)[:top]
    rows = [(job, name, *_cells(stats, grand)) for job, name, stats in heaviest]
    return "**Heaviest steps**\n\n" + _table(
        ("Job", "Step", "Median", "p90", "Share of job time"), rows
    )


def gh_json(*args: str) -> Any:
    done = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise SystemExit(f"✗ gh {' '.join(args)} failed:\n{done.stderr}")
    return json.loads(done.stdout)


def fetch(repo: str, workflow: str, limit: int, branch: str | None) -> list[dict[str, Any]]:
    """The last *limit* completed runs of *workflow*, each with its jobs and their steps."""
    query = f"repos/{repo}/actions/workflows/{workflow}/runs?status=completed&per_page={limit}"
    if branch:
        query += f"&branch={branch}"
    runs = gh_json("api", query)["workflow_runs"]
    return [
        {
            "run": run,
            "jobs": gh_json("api", f"repos/{repo}/actions/runs/{run['id']}/jobs?per_page=100")[
                "jobs"
            ],
        }
        for run in runs
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--repo", help="OWNER/NAME")
    parser.add_argument("--workflow", default="ci.yml")
    parser.add_argument("--runs", type=int, default=30)
    parser.add_argument("--branch", help="only runs on this branch")
    parser.add_argument("--top", type=int, default=8, help="how many steps to list")
    parser.add_argument("--save", type=Path, help="also write the fetched history here")
    parser.add_argument("--from-json", type=Path, help="analyse a saved history, no network")
    args = parser.parse_args(argv)

    if args.from_json:
        history = json.loads(args.from_json.read_text())
    elif args.repo:
        history = fetch(args.repo, args.workflow, args.runs, args.branch)
    else:
        parser.error("give --repo OWNER/NAME, or --from-json FILE")
    if args.save:
        args.save.write_text(json.dumps(history))
    print(render(summarize(history), args.top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
