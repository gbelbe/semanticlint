from __future__ import annotations

import semanticlint.checks.owl  # noqa: F401 — registers all built-in OWL checks
import semanticlint.checks.quality  # noqa: F401 — registers all built-in quality checks
import semanticlint.checks.rdf  # noqa: F401 — registers all built-in RDF URI checks
import semanticlint.checks.rdfs  # noqa: F401 — registers all built-in RDFS checks
import semanticlint.checks.skos  # noqa: F401 — registers all built-in SKOS checks
from semanticlint.checks.base import Check, Severity, Violation, VocabType
from semanticlint.checks.registry import CheckRegistry

__all__ = ["Check", "CheckRegistry", "Severity", "VocabType", "Violation"]
