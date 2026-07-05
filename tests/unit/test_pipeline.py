from __future__ import annotations

from rdflib import RDF, Graph, Namespace
from rdflib.namespace import OWL, RDFS

from semanticlint.checks.base import CheckConfig
from semanticlint.pipeline import check_graph, check_included

EX = Namespace("http://example.org/")


def _owl(*triples) -> Graph:
    g = Graph()
    g.add((EX.O, RDF.type, OWL.Ontology))
    for t in triples:
        g.add(t)
    return g


# ── check_included (select / ignore) ──────────────────────────────────────────


def test_included_by_default():
    assert check_included("OWL001", CheckConfig()) is True


def test_ignore_exact_and_prefix():
    assert check_included("OWL001", CheckConfig(ignore=["OWL001"])) is False
    assert check_included("OWL001", CheckConfig(ignore=["OWL"])) is False
    assert check_included("SKO001", CheckConfig(ignore=["OWL"])) is True


def test_select_restricts_to_prefix():
    assert check_included("OWL001", CheckConfig(select=["OWL"])) is True
    assert check_included("SKO001", CheckConfig(select=["OWL"])) is False


# ── check_graph combines SHACL + Python checks ────────────────────────────────


def test_check_graph_yields_shacl_and_python_checks():
    # OWL001 comes from the SHACL pass; OWL003 from the Python check.
    g = _owl(
        (EX.p, RDF.type, OWL.ObjectProperty),
        (EX.p, RDFS.range, EX.T),  # missing domain → OWL001
        (EX.i, RDF.type, OWL.NamedIndividual),  # untyped individual → OWL003
    )
    ids = {v.check_id for v in check_graph(g, CheckConfig())}
    assert "OWL001" in ids  # SHACL-backed
    assert "OWL003" in ids  # Python check


def test_check_graph_applies_ignore_to_shacl_ids():
    g = _owl((EX.p, RDF.type, OWL.ObjectProperty), (EX.p, RDFS.range, EX.T))
    ids = {v.check_id for v in check_graph(g, CheckConfig(ignore=["OWL001"]))}
    assert "OWL001" not in ids
