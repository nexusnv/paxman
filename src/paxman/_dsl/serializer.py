"""Contract value-object -> Dict DSL serializer (inverse of parser)."""

from __future__ import annotations

from typing import Any

from paxman._core.contracts import Contract


def serialize_contract(contract: Contract) -> dict[str, Any]:
    """Return the Dict DSL form of `contract` (round-trips via parse_contract)."""
    return contract.as_dict()
