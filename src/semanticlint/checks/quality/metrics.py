from __future__ import annotations

from rdflib import RDF, Graph, Literal
from rdflib.namespace import OWL, RDFS, SKOS

from semanticlint.checks.base import Check, CheckConfig, Severity, Violation, VocabType
from semanticlint.checks.registry import CheckRegistry


def _concepts(graph: Graph) -> list:
    return list(graph.subjects(RDF.type, SKOS.Concept))


def _classes(graph: Graph) -> list:
    return list(
        set(graph.subjects(RDF.type, OWL.Class)) | set(graph.subjects(RDF.type, RDFS.Class))
    )


def _properties(graph: Graph) -> list:
    return list(
        set(graph.subjects(RDF.type, OWL.ObjectProperty))
        | set(graph.subjects(RDF.type, OWL.DatatypeProperty))
    )


@CheckRegistry.register
class LabelCoverageCheck(Check):
    id = "QUA001"
    description = "Fraction of skos:Concept with skos:prefLabel should meet min_label_coverage"
    severity = Severity.WARNING
    applies_to = VocabType.SKOS

    def run(self, graph: Graph, config: CheckConfig) -> list[Violation]:
        threshold = config.quality.get("min_label_coverage", 1.0)
        concepts = _concepts(graph)
        if not concepts:
            return []
        labeled = sum(1 for c in concepts if any(graph.objects(c, SKOS.prefLabel)))
        coverage = labeled / len(concepts)
        if coverage < threshold:
            return [
                Violation(
                    self.id,
                    f"Label coverage {coverage:.0%} is below threshold {threshold:.0%}",
                    self.severity,
                )
            ]
        return []


@CheckRegistry.register
class DefinitionCoverageCheck(Check):
    id = "QUA002"
    description = (
        "Fraction of skos:Concept with skos:definition should meet min_definition_coverage"
    )
    severity = Severity.INFO
    applies_to = VocabType.SKOS

    def run(self, graph: Graph, config: CheckConfig) -> list[Violation]:
        threshold = config.quality.get("min_definition_coverage", 0.5)
        concepts = _concepts(graph)
        if not concepts:
            return []
        defined = sum(1 for c in concepts if any(graph.objects(c, SKOS.definition)))
        coverage = defined / len(concepts)
        if coverage < threshold:
            return [
                Violation(
                    self.id,
                    f"Definition coverage {coverage:.0%} is below threshold {threshold:.0%}",
                    self.severity,
                )
            ]
        return []


@CheckRegistry.register
class LanguageCoverageCheck(Check):
    id = "QUA003"
    description = "Every skos:Concept should have a skos:prefLabel in each required language"
    severity = Severity.WARNING
    applies_to = VocabType.SKOS

    def run(self, graph: Graph, config: CheckConfig) -> list[Violation]:
        languages: list[str] = config.quality.get("languages", ["en"])
        violations = []
        for concept in _concepts(graph):
            langs_present = {
                str(o.language)  # type: ignore[union-attr]
                for o in graph.objects(concept, SKOS.prefLabel)
                if isinstance(o, Literal) and o.language
            }
            for lang in languages:
                if lang not in langs_present:
                    violations.append(
                        Violation(
                            self.id,
                            f"Concept missing prefLabel in language '{lang}'",
                            self.severity,
                            subject=concept,  # type: ignore[arg-type]
                        )
                    )
        return violations


@CheckRegistry.register
class ClassLabelCoverageCheck(Check):
    id = "QUA004"
    description = (
        "Fraction of owl:Class/rdfs:Class with rdfs:label should meet min_class_label_coverage"
    )
    severity = Severity.WARNING
    applies_to = VocabType.OWL | VocabType.RDFS

    def run(self, graph: Graph, config: CheckConfig) -> list[Violation]:
        threshold = config.quality.get("min_class_label_coverage", 1.0)
        classes = _classes(graph)
        if not classes:
            return []
        labeled = sum(1 for c in classes if any(graph.objects(c, RDFS.label)))
        coverage = labeled / len(classes)
        if coverage < threshold:
            return [
                Violation(
                    self.id,
                    f"Class label coverage {coverage:.0%} is below threshold {threshold:.0%}",
                    self.severity,
                )
            ]
        return []


@CheckRegistry.register
class PropertyLabelCoverageCheck(Check):
    id = "QUA005"
    description = (
        "Fraction of OWL properties with rdfs:label should meet min_property_label_coverage"
    )
    severity = Severity.WARNING
    applies_to = VocabType.OWL

    def run(self, graph: Graph, config: CheckConfig) -> list[Violation]:
        threshold = config.quality.get("min_property_label_coverage", 1.0)
        props = _properties(graph)
        if not props:
            return []
        labeled = sum(1 for p in props if any(graph.objects(p, RDFS.label)))
        coverage = labeled / len(props)
        if coverage < threshold:
            return [
                Violation(
                    self.id,
                    f"Property label coverage {coverage:.0%} is below threshold {threshold:.0%}",
                    self.severity,
                )
            ]
        return []
