from __future__ import annotations

from pathlib import Path

from semanticlint.checks.base import Severity
from semanticlint.checks.lint.syntax import lint_syntax
from tests.fixtures import (
    INVALID_TURTLE,
    VALID_JSONLD,
    VALID_NTRIPLES,
    VALID_RDFXML,
    VALID_SKOS_TURTLE,
)


def _write(tmp_path: Path, filename: str, content: str) -> Path:
    p = tmp_path / filename
    p.write_text(content)
    return p


def test_valid_turtle_no_violations(tmp_path):
    path = _write(tmp_path, "valid.ttl", VALID_SKOS_TURTLE)
    _, violations = lint_syntax(path)
    assert violations == []


def test_invalid_turtle_returns_rdf001(tmp_path):
    path = _write(tmp_path, "broken.ttl", INVALID_TURTLE)
    _, violations = lint_syntax(path)
    assert any(v.check_id == "RDF001" for v in violations)


def test_invalid_turtle_graph_is_none(tmp_path):
    path = _write(tmp_path, "broken.ttl", INVALID_TURTLE)
    graph, _ = lint_syntax(path)
    assert graph is None


def test_valid_rdfxml_no_violations(tmp_path):
    path = _write(tmp_path, "valid.rdf", VALID_RDFXML)
    _, violations = lint_syntax(path)
    assert violations == []


def test_valid_jsonld_no_violations(tmp_path):
    path = _write(tmp_path, "valid.jsonld", VALID_JSONLD)
    _, violations = lint_syntax(path)
    assert violations == []


def test_valid_ntriples_no_violations(tmp_path):
    path = _write(tmp_path, "valid.nt", VALID_NTRIPLES)
    _, violations = lint_syntax(path)
    assert violations == []


def test_empty_file_returns_rdf002(tmp_path):
    path = _write(tmp_path, "empty.ttl", "")
    _, violations = lint_syntax(path)
    assert any(v.check_id == "RDF002" for v in violations)


def test_comments_only_returns_rdf002(tmp_path):
    path = _write(tmp_path, "comments.ttl", "# just a comment\n# nothing else\n")
    _, violations = lint_syntax(path)
    assert any(v.check_id == "RDF002" for v in violations)


def test_violation_carries_file_path(tmp_path):
    path = _write(tmp_path, "broken.ttl", INVALID_TURTLE)
    _, violations = lint_syntax(path)
    assert violations[0].location == str(path)


def test_violation_severity_is_error(tmp_path):
    path = _write(tmp_path, "broken.ttl", INVALID_TURTLE)
    _, violations = lint_syntax(path)
    assert violations[0].severity == Severity.ERROR


def test_rdf002_severity_is_warning(tmp_path):
    path = _write(tmp_path, "empty.ttl", "")
    _, violations = lint_syntax(path)
    assert violations[0].severity == Severity.WARNING


def test_explicit_format_overrides_extension(tmp_path):
    path = _write(tmp_path, "wrongext.rdf", VALID_SKOS_TURTLE)
    _, violations = lint_syntax(path, fmt="turtle")
    assert violations == []


def test_valid_graph_returned_on_success(tmp_path):
    path = _write(tmp_path, "valid.ttl", VALID_SKOS_TURTLE)
    graph, violations = lint_syntax(path)
    assert graph is not None
    assert len(graph) > 0
    assert violations == []
