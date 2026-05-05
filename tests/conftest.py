from __future__ import annotations

import pytest


@pytest.fixture()
def clean_registry():
    """Restore CheckRegistry state after a test that registers custom checks."""
    from semanticlint.checks.registry import CheckRegistry

    saved = dict(CheckRegistry._checks)
    yield CheckRegistry
    CheckRegistry._checks = saved
