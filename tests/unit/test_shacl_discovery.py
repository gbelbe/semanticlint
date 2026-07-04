from __future__ import annotations

from pathlib import Path

from rdflib import Graph

from semanticlint.checks.base import CheckConfig
from semanticlint.cli import _collect_files
from semanticlint.shacl.discovery import discover_shapes_files, is_shapes_file, load_shapes
from semanticlint.shacl.runner import run_shapes

_SHAPE = """\
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix ex: <http://example.org/> .
ex:PersonEmploymentShape a sh:NodeShape ; sh:targetClass ex:Person ;
    sh:property [ sh:path ex:work_for ; sh:maxCount 1 ;
                  sh:message "A Person may work_for at most one Department" ] .
"""
_PERSON_TWO = """\
@prefix ex: <http://example.org/> .
ex:alice a ex:Person ; ex:work_for ex:D1, ex:D2 .
"""
_PERSON_ONE = """\
@prefix ex: <http://example.org/> .
ex:alice a ex:Person ; ex:work_for ex:D1 .
"""


# ── discovery helpers ─────────────────────────────────────────────────────────


def test_is_shapes_file():
    assert is_shapes_file(Path("zoo.shapes.ttl"))
    assert not is_shapes_file(Path("zoo.ttl"))


def test_discover_for_a_file_returns_sibling_shapes(tmp_path: Path):
    (tmp_path / "zoo.ttl").write_text(_PERSON_ONE)
    shapes = tmp_path / "zoo.shapes.ttl"
    shapes.write_text(_SHAPE)
    assert discover_shapes_files(tmp_path / "zoo.ttl") == [shapes]


def test_discover_for_a_directory_walks_the_tree(tmp_path: Path):
    (tmp_path / "a.shapes.ttl").write_text(_SHAPE)
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.shapes.ttl").write_text(_SHAPE)
    assert len(discover_shapes_files(tmp_path)) == 2


def test_collect_files_excludes_shapes_files(tmp_path: Path):
    (tmp_path / "zoo.ttl").write_text(_PERSON_ONE)
    (tmp_path / "zoo.shapes.ttl").write_text(_SHAPE)
    files = _collect_files(tmp_path)
    assert tmp_path / "zoo.ttl" in files
    assert tmp_path / "zoo.shapes.ttl" not in files


def test_load_shapes_unions(tmp_path: Path):
    (tmp_path / "a.shapes.ttl").write_text(_SHAPE)
    graph = load_shapes([tmp_path / "a.shapes.ttl"])
    assert len(graph) > 0


# ── enforcement via run_shapes(extra_shapes=…) ────────────────────────────────


def _run(data_ttl: str) -> list:
    data = Graph().parse(data=data_ttl, format="turtle")
    shapes = Graph().parse(data=_SHAPE, format="turtle")
    return run_shapes(data, CheckConfig(), extra_shapes=shapes)


def test_local_rule_is_enforced_with_id_derived_from_shape_name():
    violations = _run(_PERSON_TWO)
    v = [x for x in violations if x.check_id == "PersonEmploymentShape"]
    assert v and str(v[0].subject).endswith("alice")


def test_local_rule_applies_regardless_of_vocab_type():
    # The data is plain RDF (no OWL/SKOS declarations); an un-annotated local shape
    # still fires because its sh:targetClass gates relevance, not slint:appliesTo.
    assert any(x.check_id == "PersonEmploymentShape" for x in _run(_PERSON_TWO))


def test_conforming_data_passes_the_local_rule():
    assert not [x for x in _run(_PERSON_ONE) if x.check_id == "PersonEmploymentShape"]
