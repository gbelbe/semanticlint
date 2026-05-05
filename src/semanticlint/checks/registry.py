from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from semanticlint.checks.base import Check, VocabType


class CheckRegistry:
    """Global registry of all available checks.

    Use ``@CheckRegistry.register`` as a class decorator to enroll a check.
    The registry is a module-level singleton — tests that add temporary checks
    should use the ``clean_registry`` fixture to restore state afterwards.
    """

    _checks: dict[str, type[Check]] = {}

    @classmethod
    def register(cls, check_cls: type[Check]) -> type[Check]:
        """Register *check_cls* and return it unchanged (usable as decorator)."""
        if check_cls.id in cls._checks:
            raise ValueError(
                f"Check ID {check_cls.id!r} is already registered. Use a unique ID for every check."
            )
        cls._checks[check_cls.id] = check_cls
        return check_cls

    @classmethod
    def for_vocab(cls, vtype: VocabType) -> list[type[Check]]:
        """Return checks whose ``applies_to`` flag overlaps with *vtype*."""
        return [c for c in cls._checks.values() if c.applies_to & vtype]

    @classmethod
    def all(cls) -> list[type[Check]]:
        return list(cls._checks.values())

    @classmethod
    def get(cls, check_id: str) -> type[Check] | None:
        return cls._checks.get(check_id)
