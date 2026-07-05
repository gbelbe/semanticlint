from __future__ import annotations

from pathlib import Path

from pytest_bdd import given, scenarios, when
from typer.testing import CliRunner

from semanticlint.checks.base import CheckConfig
from semanticlint.checks.lint.syntax import lint_syntax
from semanticlint.cli import app
from semanticlint.pipeline import check_graph
from semanticlint.shacl.discovery import discover_shapes_files, is_shapes_file, load_shapes

scenarios("../features/shacl/local_discovery.feature")

_SHAPE = """\
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix ex: <http://example.org/> .
ex:PersonEmploymentShape a sh:NodeShape ; sh:targetClass ex:Person ;
    sh:property [ sh:path ex:work_for ; sh:maxCount 1 ;
                  sh:message "A Person may work_for at most one Department" ] .
"""
_PERSON_TWO = (
    "@prefix ex: <http://example.org/> .\nex:alice a ex:Person ; ex:work_for ex:D1, ex:D2 .\n"
)
_PERSON_ONE = "@prefix ex: <http://example.org/> .\nex:alice a ex:Person ; ex:work_for ex:D1 .\n"


# ── Givens ────────────────────────────────────────────────────────────────────


@given("a project with a local Person-employment shape", target_fixture="project")
def project_with_shape(tmp_path: Path) -> Path:
    (tmp_path / "zoo.shapes.ttl").write_text(_SHAPE)
    return tmp_path


@given("the ontology has a Person working for two Departments")
def ontology_two(project: Path) -> None:
    (project / "zoo.ttl").write_text(_PERSON_TWO)


@given("the ontology has a Person working for one Department")
def ontology_one(project: Path) -> None:
    (project / "zoo.ttl").write_text(_PERSON_ONE)


# ── When ──────────────────────────────────────────────────────────────────────


@when("I check the project", target_fixture="violations")
def check_project(project: Path) -> list:
    shapes = load_shapes(discover_shapes_files(project))
    violations: list = []
    for data_file in sorted(project.glob("*.ttl")):
        if is_shapes_file(data_file):
            continue
        graph, syntax = lint_syntax(data_file)
        violations.extend(syntax)
        if graph is not None and len(graph) > 0:
            violations.extend(check_graph(graph, CheckConfig(), extra_shapes=shapes))
    return violations


@when("I run semanticlint check on the project", target_fixture="result")
def run_cli(project: Path):
    return CliRunner().invoke(app, ["check", str(project)])
