from __future__ import annotations

import semanticlint.checks.skos  # noqa: F401 — registers all built-in SKOS checks
from semanticlint.checks.base import Check, Severity, Violation, VocabType
from semanticlint.checks.registry import CheckRegistry

__all__ = ["Check", "CheckRegistry", "Severity", "VocabType", "Violation"]
