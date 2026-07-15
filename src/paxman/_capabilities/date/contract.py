"""Date contract value object and domain-type factory.

Migrated from ``paxman._contracts.contract`` as part of the additive
reorganisation into ``paxman._capabilities.date``.
"""

from __future__ import annotations

from typing import Any, Literal

import attrs

from paxman._errors import ContractError
from paxman._registry.contract_registry import register_contract


@attrs.frozen
class CanonicalDateContract:
    """The date contract (MANDATE §4: the contract is the user's language).

    ``locale`` is REQUIRED — there is no default and no ``auto_detect``
    (Law 7 — Explicit Over Clever). A numeric slash form cannot be resolved
    to a unique reading without it (Law 4).
    """

    locale: Literal["ISO", "US", "EU"]
    kind: str = "canonical_date"
    version_field: int = 1

    def as_dict(self) -> dict[str, Any]:
        """Return the Dict DSL form of this contract (round-trips via parse_contract)."""
        return {
            "kind": self.kind,
            "locale": self.locale,
            "version_field": self.version_field,
        }


def Date(*, locale: Literal["ISO", "US", "EU"]) -> CanonicalDateContract:
    """Domain-type sugar: declare a date contract in user vocabulary.

    ``locale`` has NO default — the caller must state the reading policy
    explicitly (Law 7). MANDATE §6.4 shows ``CanonicalDate(locale="MY")``.
    """
    return CanonicalDateContract(locale=locale)


def _build_date(spec: dict[str, Any]) -> CanonicalDateContract:
    locale = spec.get("locale")
    if locale not in {"ISO", "US", "EU"}:
        raise ContractError(f"invalid or missing locale: {locale!r}; allowed: ['ISO', 'US', 'EU']")
    return CanonicalDateContract(locale=locale)


register_contract("canonical_date", _build_date)
