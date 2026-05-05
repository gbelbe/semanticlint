from __future__ import annotations

from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when

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


@when("I run the syntax linter on it", target_fixture="lint_result")
def run_syntax_linter(rdf_path: Path):
    return lint_syntax(rdf_path)


# ── Thens ─────────────────────────────────────────────────────────────────────


@then("there are no violations")
def no_violations(lint_result):
    _, violations = lint_result
    assert violations == []


@then(parsers.parse('there is a violation with id "{check_id}"'))
def violation_with_id(lint_result, check_id: str):
    _, violations = lint_result
    assert any(v.check_id == check_id for v in violations), (
        f"Expected violation {check_id!r}, got: {[v.check_id for v in violations]}"
    )


@then(parsers.parse('the violation severity is "{severity}"'))
def violation_severity(lint_result, severity: str):
    _, violations = lint_result
    assert violations, "No violations to check severity on"
    assert violations[0].severity.value == severity


@then("the violation location references the source file")
def violation_location_references_file(lint_result, rdf_path: Path):
    _, violations = lint_result
    assert violations, "No violations to check location on"
    assert violations[0].location is not None
    assert Path(violations[0].location).name == rdf_path.name
