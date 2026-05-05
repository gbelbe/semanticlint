from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, Flag, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rdflib import Graph, URIRef


class VocabType(Flag):
    """Vocabulary paradigm detected in an RDF graph. Flags are combinable."""

    RDF = auto()  # always present — every file is RDF
    RDFS = auto()  # rdfs:Class usage without OWL
    OWL = auto()  # owl:Class or owl:Ontology
    SKOS = auto()  # skos:Concept or skos:ConceptScheme


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Violation:
    check_id: str
    message: str
    severity: Severity
    subject: URIRef | None = None  # offending RDF node
    location: str | None = None  # source file path


@dataclass
class CheckConfig:
    select: list[str] = field(default_factory=list)  # prefixes or IDs to run
    ignore: list[str] = field(default_factory=list)  # IDs to skip
    quality: dict = field(default_factory=dict)


class Check(ABC):
    """Base class for all semanticlint checks.

    Subclass, set the class attributes, and decorate with
    ``@CheckRegistry.register``.  The ``run`` method receives the already-parsed
    graph and the active configuration.
    """

    id: str
    description: str
    severity: Severity
    applies_to: VocabType

    @abstractmethod
    def run(self, graph: Graph, config: CheckConfig) -> list[Violation]: ...
