"""Structured provenance for grammar rules (mandate Law 14).

Each Grammar is bound to a ``Provenance`` object naming the standard or
specification it recognises. Evidence carries this provenance forward.
"""

from __future__ import annotations

import attrs


@attrs.frozen
class Provenance:
    """Structured provenance for a grammar rule.

    Attributes:
        name: The standard/spec name (e.g., ``"ISO 8601"``, ``"CLDR month names"``).
        version: Optional version (e.g., ``"2024"``, ``"RFC 5905"``).
        citation: Optional formal citation or URL.
    """

    name: str
    version: str | None = None
    citation: str | None = None
