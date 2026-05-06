from __future__ import annotations

from pathlib import Path

from pytest_bdd import given, parsers, scenarios, when
from typer.testing import CliRunner

from semanticlint.cli import app

scenarios("../features/cli/check_command.feature")

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


# ── Givens ────────────────────────────────────────────────────────────────────


@given("a valid SKOS Turtle file", target_fixture="cli_path")
def valid_skos_file(tmp_path: Path) -> Path:
    p = tmp_path / "vocab.ttl"
    p.write_text(_FULLY_VALID_SKOS)
    return p


@given("a Turtle file with invalid syntax", target_fixture="cli_path")
def invalid_turtle_file(tmp_path: Path) -> Path:
    p = tmp_path / "bad.ttl"
    p.write_text(_INVALID_TURTLE)
    return p


@given("a SKOS Turtle file with missing prefLabels", target_fixture="cli_path")
def skos_missing_labels(tmp_path: Path) -> Path:
    p = tmp_path / "warnings.ttl"
    p.write_text(_WARNING_SKOS)
    return p


@given("a non-existent path", target_fixture="cli_path")
def nonexistent_path(tmp_path: Path) -> Path:
    return tmp_path / "does_not_exist.ttl"


# ── When ──────────────────────────────────────────────────────────────────────


@when("I run semanticlint check", target_fixture="result")
def run_check(cli_path: Path):
    return runner.invoke(app, ["check", str(cli_path)])


@when(parsers.parse('I run semanticlint check with fail-on "{level}"'), target_fixture="result")
def run_check_fail_on(cli_path: Path, level: str):
    return runner.invoke(app, ["check", str(cli_path), "--fail-on", level])
