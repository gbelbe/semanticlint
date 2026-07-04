from __future__ import annotations

from rdflib import Literal, Namespace
from rdflib.namespace import (
    SH,  # noqa: N811
    SKOS,
)

from semanticlint.checks.base import CheckConfig
from semanticlint.shacl.builder import build_config_shapes

SLINT = Namespace("https://semanticlint.org/ns#")


def _qua003_shapes(graph):
    return list(graph.subjects(SLINT.checkId, Literal("QUA003")))


def test_defaults_to_english_when_no_languages_configured():
    graph = build_config_shapes(CheckConfig())
    assert len(_qua003_shapes(graph)) == 1


def test_builds_one_qua003_shape_per_required_language():
    graph = build_config_shapes(CheckConfig(quality={"languages": ["en", "fr", "de"]}))
    assert len(_qua003_shapes(graph)) == 3


def test_qua003_shape_targets_concepts_and_is_skos_scoped():
    graph = build_config_shapes(CheckConfig(quality={"languages": ["fr"]}))
    shape = _qua003_shapes(graph)[0]
    assert (shape, SH.targetClass, SKOS.Concept) in graph
    assert (shape, SLINT.appliesTo, Literal("SKOS")) in graph


def test_qua003_shape_constrains_the_configured_language():
    graph = build_config_shapes(CheckConfig(quality={"languages": ["fr"]}))
    # the required language is emitted as a sh:languageIn list entry
    list_head = next(graph.objects(predicate=SH.languageIn))
    from rdflib.collection import Collection

    assert Literal("fr") in list(Collection(graph, list_head))
