"""Config-driven SHACL shapes.

Some checks depend on configuration, so their shapes cannot be static files —
they are generated from :class:`~semanticlint.checks.base.CheckConfig` at run time.
Currently: QUA003 (language coverage) emits one shape per required language, each
requiring a ``skos:prefLabel`` in that language (``sh:languageIn`` +
``sh:qualifiedMinCount``).
"""

from __future__ import annotations

from rdflib import BNode, Graph, Literal, Namespace
from rdflib.collection import Collection
from rdflib.namespace import (
    RDF,
    SH,  # noqa: N811 — SHACL namespace
    SKOS,
)

from semanticlint.checks.base import CheckConfig

SLINT = Namespace("https://semanticlint.org/ns#")

DEFAULT_LANGUAGES = ["en"]


def build_config_shapes(config: CheckConfig) -> Graph:
    """A shapes graph generated from *config* (empty when nothing applies)."""
    graph = Graph()
    _add_language_coverage_shapes(graph, config)
    return graph


def _add_language_coverage_shapes(graph: Graph, config: CheckConfig) -> None:
    """QUA003 — one NodeShape per required language: every skos:Concept must carry a
    skos:prefLabel in that language."""
    languages = config.quality.get("languages", DEFAULT_LANGUAGES)
    for lang in languages:
        shape = SLINT[f"QUA003_{lang}"]
        graph.add((shape, RDF.type, SH.NodeShape))
        graph.add((shape, SLINT.checkId, Literal("QUA003")))
        graph.add((shape, SLINT.appliesTo, Literal("SKOS")))
        graph.add((shape, SH.targetClass, SKOS.Concept))

        prop = BNode()
        graph.add((shape, SH.property, prop))
        graph.add((prop, SH.path, SKOS.prefLabel))
        graph.add((prop, SH.qualifiedMinCount, Literal(1)))
        graph.add((prop, SH.severity, SH.Warning))
        graph.add((prop, SH.message, Literal(f"Concept missing prefLabel in language '{lang}'")))

        qualified = BNode()
        graph.add((prop, SH.qualifiedValueShape, qualified))
        lang_list = BNode()
        graph.add((qualified, SH.languageIn, lang_list))
        Collection(graph, lang_list, [Literal(lang)])
