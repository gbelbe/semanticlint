from __future__ import annotations

import sys
from pathlib import Path

import typer
import yaml
from rich.console import Console

import semanticlint  # noqa: F401 — registers all built-in checks
from semanticlint.checks.base import CheckConfig, Severity
from semanticlint.checks.lint.syntax import lint_syntax
from semanticlint.checks.registry import CheckRegistry
from semanticlint.detect import detect_vocab_type

app = typer.Typer(help="Lint and quality-check RDF, SKOS, OWL and RDFS vocabularies.")

_SEVERITY_ORDER = {Severity.INFO: 0, Severity.WARNING: 1, Severity.ERROR: 2}

_SEVERITY_STYLE = {
    Severity.ERROR: "bold red",
    Severity.WARNING: "yellow",
    Severity.INFO: "blue",
}

_RDF_EXTENSIONS = {".ttl", ".rdf", ".owl", ".n3", ".nt", ".jsonld", ".json"}


def _collect_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(p for p in path.rglob("*") if p.suffix.lower() in _RDF_EXTENSIONS)


def _load_config(config_path: Path | None, search_dir: Path) -> CheckConfig:
    candidate = config_path or search_dir / "onto-ci.yml"
    if candidate.exists():
        with open(candidate) as f:
            data = yaml.safe_load(f) or {}
        return CheckConfig(
            select=data.get("select", []),
            ignore=data.get("ignore", []),
            quality=data.get("quality", {}),
        )
    return CheckConfig()


def _meets_threshold(severity: Severity, threshold: Severity) -> bool:
    return _SEVERITY_ORDER[severity] >= _SEVERITY_ORDER[threshold]


@app.command()
def check(
    path: Path = typer.Argument(Path("."), help="File or directory to check."),
    config: Path | None = typer.Option(None, "--config", help="Path to onto-ci.yml."),
    fail_on: str = typer.Option(
        "error", "--fail-on", help="Minimum severity that causes exit 1 [error|warning|info]."
    ),
) -> None:
    console = Console(file=sys.stdout, highlight=False)

    if not path.exists():
        console.print(f"[bold red]Error:[/] path not found: {path}")
        raise typer.Exit(1)

    try:
        fail_on_severity = Severity(fail_on)
    except ValueError:
        console.print("[bold red]Error:[/] --fail-on must be one of: error, warning, info")
        raise typer.Exit(1)

    search_dir = path.parent if path.is_file() else path
    cfg = _load_config(config, search_dir)
    files = _collect_files(path)

    if not files:
        console.print(f"[yellow]No RDF files found in {path}[/]")
        raise typer.Exit(0)

    all_violations = []

    for file_path in files:
        graph, syntax_violations = lint_syntax(file_path)
        file_violations = list(syntax_violations)

        if graph is not None and len(graph) > 0:
            vtype = detect_vocab_type(graph)
            for check_cls in CheckRegistry.for_vocab(vtype):
                file_violations.extend(check_cls().run(graph, cfg))

        if file_violations:
            console.print(f"\n[bold]{file_path}[/]")
            for v in file_violations:
                style = _SEVERITY_STYLE[v.severity]
                label = f"[{style}]{v.severity.value.upper():7}[/{style}]"
                subj = f" {str(v.subject).split('/')[-1].split('#')[-1]}" if v.subject else ""
                console.print(f"  {label} [{v.check_id}]{subj}: {v.message}")

        all_violations.extend(file_violations)

    errors = sum(1 for v in all_violations if v.severity == Severity.ERROR)
    warnings = sum(1 for v in all_violations if v.severity == Severity.WARNING)
    infos = sum(1 for v in all_violations if v.severity == Severity.INFO)

    console.print()
    console.rule()

    if not all_violations:
        console.print("[bold green]No violations found.[/]")
    else:
        parts = []
        if errors:
            parts.append(f"[bold red]{errors} error{'s' if errors != 1 else ''}[/]")
        if warnings:
            parts.append(f"[yellow]{warnings} warning{'s' if warnings != 1 else ''}[/]")
        if infos:
            parts.append(f"[blue]{infos} info[/]")
        total = len(all_violations)
        console.print(
            f"{total} violation{'s' if total != 1 else ''}: "
            + ", ".join(parts)
            + f"  (fail-on: {fail_on})"
        )

    if any(_meets_threshold(v.severity, fail_on_severity) for v in all_violations):
        raise typer.Exit(1)


@app.command()
def version() -> None:
    """Print the installed version."""
    from importlib.metadata import version as pkg_version

    typer.echo(pkg_version("semanticlint"))


_WORKFLOW_TEMPLATE = """\
name: Ontology CI

on:
  push:
    branches: ["master", "main"]
    paths: ["**.ttl", "**.rdf", "**.owl", "onto-ci.yml"]
  pull_request:
    branches: ["master", "main"]
    paths: ["**.ttl", "**.rdf", "**.owl", "onto-ci.yml"]

jobs:
  lint:
    name: Lint vocabulary files
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: gbelbe/semanticlint@{action_version}
        with:
          path: "."
          fail-on: {fail_on}
"""

_WORKFLOW_FILE = Path(".github") / "workflows" / "ontology-ci.yml"


@app.command()
def init(
    root: Path = typer.Option(Path("."), "--root", help="Project root directory."),
    fail_on: str = typer.Option(
        "error", "--fail-on", help="fail-on level written into the generated workflow."
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing workflow."),
) -> None:
    """Generate a GitHub Actions CI workflow for this vocabulary project."""
    from importlib.metadata import version as pkg_version

    console = Console(file=sys.stdout, highlight=False)
    workflow_path = root / _WORKFLOW_FILE

    if workflow_path.exists() and not force:
        console.print(f"[yellow]Workflow already exists:[/] {workflow_path}")
        console.print("Run with [bold]--force[/] to overwrite.")
        raise typer.Exit(0)

    action_version = f"v{pkg_version('semanticlint')}"
    workflow_path.parent.mkdir(parents=True, exist_ok=True)
    workflow_path.write_text(
        _WORKFLOW_TEMPLATE.format(fail_on=fail_on, action_version=action_version)
    )
    console.print(f"[bold green]Created:[/] {workflow_path}")


def main() -> None:
    app()
