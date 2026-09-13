"""Boot-migration SQL resources (ADR-0016).

The statements live in this package as `.sql` files — one statement per
file, grouped in subdirectories (`schema/`, `decor/`, …). SQL is a
foreign language and stays out of Python string literals; filename order
(numeric prefixes) is the single source of truth for execution order.
"""
from __future__ import annotations

from importlib import resources
from typing import ClassVar


class migrations:
    """Namespace-only owner (snake_case by doctrine: groups behavior,
    never instantiated)."""

    PACKAGE: ClassVar[str] = "nylium.server.migrations"

    @classmethod
    def statement(cls, name: str) -> str:
        """Load a single `.sql` resource by package-relative name."""
        return (resources.files(cls.PACKAGE) / name).read_text()

    @classmethod
    def group(cls, name: str) -> list[str]:
        """Load every statement of a group subdirectory, in filename order."""
        directory = resources.files(cls.PACKAGE) / name
        return [
            path.read_text()
            for path in sorted(directory.iterdir(), key=lambda p: p.name)
            if path.name.endswith(".sql")
        ]
