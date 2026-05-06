from __future__ import annotations

from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

from semanticlint.cli import app

scenarios("../features/cli/init_command.feature")

runner = CliRunner()

_WORKFLOW_PATH = Path(".github") / "workflows" / "ontology-ci.yml"
_SENTINEL = "# existing workflow\n"


# ── Givens ────────────────────────────────────────────────────────────────────


@given("a project directory with no CI workflow", target_fixture="project_root")
def no_workflow(tmp_path: Path) -> Path:
    return tmp_path


@given("a project directory with an existing CI workflow", target_fixture="project_root")
def existing_workflow(tmp_path: Path) -> Path:
    wf = tmp_path / _WORKFLOW_PATH
    wf.parent.mkdir(parents=True)
    wf.write_text(_SENTINEL)
    return tmp_path


@given("a project directory with no .github directory", target_fixture="project_root")
def no_github_dir(tmp_path: Path) -> Path:
    return tmp_path


# ── When ──────────────────────────────────────────────────────────────────────


@when("I run semanticlint init", target_fixture="result")
def run_init(project_root: Path):
    return runner.invoke(app, ["init", "--root", str(project_root)])


@when("I run semanticlint init with --force", target_fixture="result")
def run_init_force(project_root: Path):
    return runner.invoke(app, ["init", "--root", str(project_root), "--force"])


@when(parsers.parse("I run semanticlint init with --fail-on {level}"), target_fixture="result")
def run_init_fail_on(project_root: Path, level: str):
    return runner.invoke(app, ["init", "--root", str(project_root), "--fail-on", level])


# ── Then ──────────────────────────────────────────────────────────────────────


@then("the workflow file is created")
def workflow_created(project_root: Path) -> None:
    assert (project_root / _WORKFLOW_PATH).exists()


@then("the workflow file is not overwritten")
def workflow_not_overwritten(project_root: Path) -> None:
    assert (project_root / _WORKFLOW_PATH).read_text() == _SENTINEL


@then(parsers.parse('the workflow file contains "{text}"'))
def workflow_contains(project_root: Path, text: str) -> None:
    assert text in (project_root / _WORKFLOW_PATH).read_text()
