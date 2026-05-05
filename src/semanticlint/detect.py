from __future__ import annotations

from rdflib import RDF, Graph
from rdflib.namespace import OWL, RDFS
from rdflib.namespace import SKOS as SKOS_NS

from semanticlint.checks.base import VocabType


def detect_vocab_type(graph: Graph) -> VocabType:
    """Infer the vocabulary paradigm(s) present in *graph*.

    ``VocabType.RDF`` is always included.  Additional flags are OR-ed in when
    the corresponding classes or declarations are found.  ``VocabType.RDFS`` is
    only set when RDFS classes are present *without* OWL — OWL supersedes RDFS
    for the purpose of check selection.
    """
    result = VocabType.RDF

    if any(graph.subjects(RDF.type, SKOS_NS.Concept)) or any(
        graph.subjects(RDF.type, SKOS_NS.ConceptScheme)
    ):
        result |= VocabType.SKOS

    if any(graph.subjects(RDF.type, OWL.Class)) or any(graph.subjects(RDF.type, OWL.Ontology)):
        result |= VocabType.OWL

    if not (result & VocabType.OWL) and any(graph.subjects(RDF.type, RDFS.Class)):
        result |= VocabType.RDFS

    return result
