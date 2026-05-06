from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from semanticlint.cli import app

runner = CliRunner()

_WORKFLOW_PATH = Path(".github") / "workflows" / "ontology-ci.yml"
_SENTINEL = "# existing workflow\n"


def _init(tmp_path: Path, *extra_args: str):
    return runner.invoke(app, ["init", "--root", str(tmp_path), *extra_args])


# ── Core behaviour ────────────────────────────────────────────────────────────


def test_init_creates_workflow_when_missing(tmp_path: Path) -> None:
    result = _init(tmp_path)
    assert result.exit_code == 0
    assert (tmp_path / _WORKFLOW_PATH).exists()


def test_init_skips_existing_workflow(tmp_path: Path) -> None:
    wf = tmp_path / _WORKFLOW_PATH
    wf.parent.mkdir(parents=True)
    wf.write_text(_SENTINEL)
    _init(tmp_path)
    assert wf.read_text() == _SENTINEL


def test_init_force_overwrites_existing(tmp_path: Path) -> None:
    wf = tmp_path / _WORKFLOW_PATH
    wf.parent.mkdir(parents=True)
    wf.write_text(_SENTINEL)
    _init(tmp_path, "--force")
    assert wf.read_text() != _SENTINEL


def test_init_creates_missing_github_dir(tmp_path: Path) -> None:
    assert not (tmp_path / ".github").exists()
    _init(tmp_path)
    assert (tmp_path / _WORKFLOW_PATH).exists()


# ── Generated content ─────────────────────────────────────────────────────────


def test_init_workflow_contains_checkout_action(tmp_path: Path) -> None:
    _init(tmp_path)
    content = (tmp_path / _WORKFLOW_PATH).read_text()
    assert "actions/checkout" in content


def test_init_workflow_contains_semanticlint_action(tmp_path: Path) -> None:
    _init(tmp_path)
    content = (tmp_path / _WORKFLOW_PATH).read_text()
    assert "gbelbe/semanticlint" in content


def test_init_custom_fail_on_in_generated_file(tmp_path: Path) -> None:
    _init(tmp_path, "--fail-on", "warning")
    content = (tmp_path / _WORKFLOW_PATH).read_text()
    assert "fail-on: warning" in content
