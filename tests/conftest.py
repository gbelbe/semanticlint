from __future__ import annotations

import pytest
from pytest_bdd import parsers, then


@pytest.fixture()
def clean_registry():
    """Restore CheckRegistry state after a test that registers custom checks."""
    from semanticlint.checks.registry import CheckRegistry

    saved = dict(CheckRegistry._checks)
    yield CheckRegistry
    CheckRegistry._checks = saved


# ── Shared BDD "Then" steps ───────────────────────────────────────────────────
# All "When" steps across every feature file must produce a `violations` fixture
# (a plain list[Violation]) so these steps can consume it.


@then("there are no violations")
def no_violations(violations: list) -> None:
    assert violations == [], f"Expected no violations, got: {[v.check_id for v in violations]}"


@then(parsers.parse('there is a violation with id "{check_id}"'))
def violation_with_id(violations: list, check_id: str) -> None:
    assert any(v.check_id == check_id for v in violations), (
        f"Expected violation {check_id!r}, got: {[v.check_id for v in violations]}"
    )


@then(parsers.parse('there is no violation with id "{check_id}"'))
def no_violation_with_id(violations: list, check_id: str) -> None:
    assert not any(v.check_id == check_id for v in violations), (
        f"Expected no {check_id!r} violation, got: {[v.check_id for v in violations]}"
    )


@then(parsers.parse('the violation severity is "{severity}"'))
def violation_severity(violations: list, severity: str) -> None:
    assert violations, "No violations to check severity on"
    assert violations[0].severity.value == severity
