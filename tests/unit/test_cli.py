from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from semanticlint.cli import app

runner = CliRunner()

_FULLY_VALID_SKOS = """\
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix ex:   <http://example.org/> .

ex:Scheme a skos:ConceptScheme .
ex:C1 a skos:Concept ;
    skos:inScheme ex:Scheme ;
    skos:prefLabel "Concept One"@en ;
    skos:definition "The first concept."@en .
"""

_WARNING_SKOS = """\
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix ex:   <http://example.org/> .

ex:Scheme a skos:ConceptScheme .
ex:C1 a skos:Concept ; skos:inScheme ex:Scheme .
ex:C2 a skos:Concept ; skos:inScheme ex:Scheme .
"""

_INVALID_TURTLE = """\
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
ex:C1 a skos:Concept
"""


@pytest.fixture()
def valid_ttl(tmp_path: Path) -> Path:
    p = tmp_path / "vocab.ttl"
    p.write_text(_FULLY_VALID_SKOS)
    return p


@pytest.fixture()
def warning_ttl(tmp_path: Path) -> Path:
    p = tmp_path / "warnings.ttl"
    p.write_text(_WARNING_SKOS)
    return p


@pytest.fixture()
def invalid_ttl(tmp_path: Path) -> Path:
    p = tmp_path / "bad.ttl"
    p.write_text(_INVALID_TURTLE)
    return p


# ── Exit code tests ───────────────────────────────────────────────────────────


def test_check_valid_skos_file_exits_zero(valid_ttl: Path) -> None:
    result = runner.invoke(app, ["check", str(valid_ttl)])
    assert result.exit_code == 0


def test_check_invalid_turtle_exits_one(invalid_ttl: Path) -> None:
    result = runner.invoke(app, ["check", str(invalid_ttl)])
    assert result.exit_code == 1


def test_check_fail_on_error_ignores_warnings(warning_ttl: Path) -> None:
    result = runner.invoke(app, ["check", str(warning_ttl), "--fail-on", "error"])
    assert result.exit_code == 0


def test_check_fail_on_warning_exits_one(warning_ttl: Path) -> None:
    result = runner.invoke(app, ["check", str(warning_ttl), "--fail-on", "warning"])
    assert result.exit_code == 1


def test_check_fail_on_info_exits_one(warning_ttl: Path) -> None:
    result = runner.invoke(app, ["check", str(warning_ttl), "--fail-on", "info"])
    assert result.exit_code == 1


def test_check_nonexistent_path_shows_error(tmp_path: Path) -> None:
    result = runner.invoke(app, ["check", str(tmp_path / "missing.ttl")])
    assert result.exit_code == 1


def test_check_default_fail_on_is_error(warning_ttl: Path) -> None:
    default = runner.invoke(app, ["check", str(warning_ttl)])
    explicit = runner.invoke(app, ["check", str(warning_ttl), "--fail-on", "error"])
    assert default.exit_code == explicit.exit_code == 0


# ── Directory support ─────────────────────────────────────────────────────────


def test_check_directory_processes_ttl_files(tmp_path: Path) -> None:
    (tmp_path / "a.ttl").write_text(_FULLY_VALID_SKOS)
    (tmp_path / "b.ttl").write_text(_FULLY_VALID_SKOS)
    result = runner.invoke(app, ["check", str(tmp_path)])
    assert result.exit_code == 0


# ── Output content tests ──────────────────────────────────────────────────────


def test_check_output_shows_check_id(warning_ttl: Path) -> None:
    result = runner.invoke(app, ["check", str(warning_ttl), "--fail-on", "info"])
    assert "SKO002" in result.output


def test_check_output_shows_summary(warning_ttl: Path) -> None:
    result = runner.invoke(app, ["check", str(warning_ttl), "--fail-on", "info"])
    assert "violation" in result.output


# ── Config file ───────────────────────────────────────────────────────────────


def test_check_with_config_file(tmp_path: Path) -> None:
    (tmp_path / "vocab.ttl").write_text(_WARNING_SKOS)
    # Zero thresholds so no quality violations fire; still has SKO002 warnings
    (tmp_path / "onto-ci.yml").write_text(
        "quality:\n  min_label_coverage: 0.0\n  min_definition_coverage: 0.0\n"
    )
    result = runner.invoke(
        app, ["check", str(tmp_path / "vocab.ttl"), "--config", str(tmp_path / "onto-ci.yml")]
    )
    # SKO002 warnings still fire; with default fail-on error, exit 0
    assert result.exit_code == 0
