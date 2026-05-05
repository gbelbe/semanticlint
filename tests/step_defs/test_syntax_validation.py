from __future__ import annotations

from pathlib import Path

from pytest_bdd import given, scenarios, then, when

from semanticlint.checks.lint.syntax import lint_syntax
from tests.fixtures import (
    INVALID_TURTLE,
    VALID_JSONLD,
    VALID_NTRIPLES,
    VALID_RDFXML,
    VALID_SKOS_TURTLE,
)

scenarios("../features/lint/syntax_validation.feature")


# ── Givens ────────────────────────────────────────────────────────────────────


@given("a valid Turtle file", target_fixture="rdf_path")
def valid_turtle_file(tmp_path: Path) -> Path:
    path = tmp_path / "valid.ttl"
    path.write_text(VALID_SKOS_TURTLE)
    return path


@given("a Turtle file with a syntax error", target_fixture="rdf_path")
def broken_turtle_file(tmp_path: Path) -> Path:
    path = tmp_path / "broken.ttl"
    path.write_text(INVALID_TURTLE)
    return path


@given("a valid RDF/XML file", target_fixture="rdf_path")
def valid_rdfxml_file(tmp_path: Path) -> Path:
    path = tmp_path / "valid.rdf"
    path.write_text(VALID_RDFXML)
    return path


@given("a valid JSON-LD file", target_fixture="rdf_path")
def valid_jsonld_file(tmp_path: Path) -> Path:
    path = tmp_path / "valid.jsonld"
    path.write_text(VALID_JSONLD)
    return path


@given("a valid N-Triples file", target_fixture="rdf_path")
def valid_ntriples_file(tmp_path: Path) -> Path:
    path = tmp_path / "valid.nt"
    path.write_text(VALID_NTRIPLES)
    return path


@given("an empty RDF file", target_fixture="rdf_path")
def empty_rdf_file(tmp_path: Path) -> Path:
    path = tmp_path / "empty.ttl"
    path.write_text("")
    return path


# ── When ──────────────────────────────────────────────────────────────────────


@when("I run the syntax linter on it", target_fixture="violations")
def run_syntax_linter(rdf_path: Path) -> list:
    _, violations = lint_syntax(rdf_path)
    return violations


# ── Domain-specific Then ──────────────────────────────────────────────────────
# Generic "there are no violations", "there is a violation with id X", and
# "the violation severity is X" live in conftest.py.


@then("the violation location references the source file")
def violation_location_references_file(violations: list, rdf_path: Path) -> None:
    assert violations, "No violations to check location on"
    assert violations[0].location is not None
    assert Path(violations[0].location).name == rdf_path.name
