"""Contract adapters (v2.0.0: the Dict DSL only)."""

from paxman._contracts.contract import (
    CanonicalEmailContract,
    Contract,
    parse_contract,
)

__all__ = [
    "CanonicalEmailContract",
    "Contract",
    "parse_contract",
]
