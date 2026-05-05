from __future__ import annotations

import pytest
from rdflib import Graph

from semanticlint.checks.base import Check, CheckConfig, Severity, Violation, VocabType


class _FakeSkosCheck(Check):
    id = "TST001"
    description = "Test SKOS check"
    severity = Severity.WARNING
    applies_to = VocabType.SKOS

    def run(self, graph: Graph, config: CheckConfig) -> list[Violation]:
        return [Violation(self.id, "test", self.severity)]


class _FakeOwlCheck(Check):
    id = "TST002"
    description = "Test OWL check"
    severity = Severity.ERROR
    applies_to = VocabType.OWL

    def run(self, graph: Graph, config: CheckConfig) -> list[Violation]:
        return []


def test_register_decorator_adds_check(clean_registry):
    @clean_registry.register
    class MyCheck(Check):
        id = "TST099"
        description = "ad-hoc test"
        severity = Severity.INFO
        applies_to = VocabType.RDF

        def run(self, graph, config):
            return []

    assert "TST099" in clean_registry._checks


def test_registered_check_is_returned_unchanged(clean_registry):
    @clean_registry.register
    class MyCheck(Check):
        id = "TST098"
        description = "returned as-is"
        severity = Severity.INFO
        applies_to = VocabType.RDF

        def run(self, graph, config):
            return []

    assert clean_registry._checks["TST098"] is MyCheck


def test_duplicate_id_raises(clean_registry):
    clean_registry.register(_FakeSkosCheck)
    with pytest.raises(ValueError, match="TST001"):

        @clean_registry.register
        class Duplicate(Check):
            id = "TST001"
            description = "duplicate"
            severity = Severity.INFO
            applies_to = VocabType.SKOS

            def run(self, graph, config):
                return []


def test_for_vocab_returns_matching_checks(clean_registry):
    clean_registry.register(_FakeSkosCheck)
    clean_registry.register(_FakeOwlCheck)
    skos_checks = clean_registry.for_vocab(VocabType.SKOS)
    ids = [c.id for c in skos_checks]
    assert "TST001" in ids
    assert "TST002" not in ids


def test_for_vocab_skips_non_matching_type(clean_registry):
    clean_registry.register(_FakeSkosCheck)
    owl_checks = clean_registry.for_vocab(VocabType.OWL)
    ids = [c.id for c in owl_checks]
    assert "TST001" not in ids


def test_for_vocab_combined_flag_matches_both(clean_registry):
    clean_registry.register(_FakeSkosCheck)
    clean_registry.register(_FakeOwlCheck)
    combined = VocabType.SKOS | VocabType.OWL
    checks = clean_registry.for_vocab(combined)
    ids = [c.id for c in checks]
    assert "TST001" in ids
    assert "TST002" in ids


def test_custom_check_registered_and_runs(clean_registry):
    @clean_registry.register
    class AlwaysViolates(Check):
        id = "TST097"
        description = "always violates"
        severity = Severity.WARNING
        applies_to = VocabType.RDF

        def run(self, graph, config):
            return [Violation(self.id, "always", self.severity)]

    instance = clean_registry._checks["TST097"]()
    violations = instance.run(Graph(), CheckConfig())
    assert len(violations) == 1
    assert violations[0].check_id == "TST097"


def test_all_returns_every_registered_check(clean_registry):
    clean_registry.register(_FakeSkosCheck)
    clean_registry.register(_FakeOwlCheck)
    all_checks = clean_registry.all()
    ids = [c.id for c in all_checks]
    assert "TST001" in ids
    assert "TST002" in ids
