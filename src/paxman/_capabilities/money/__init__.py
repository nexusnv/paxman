# src/paxman/_capabilities/money/__init__.py
"""Money capability package (re-exports).

This module only re-exports public symbols. Importing it has no side effects:
no capability is registered and no pipeline is modified. Every re-exported
symbol is deterministic and pure (MANDATE Law 1 — Identity, Law 2 —
Determinism). The registry is frozen by the engine on the first
`canonicalize`, not by importing this package.
"""

from __future__ import annotations

from paxman._capabilities.money.canonicalizer import MoneyCapability
from paxman._capabilities.money.contract import CanonicalMoneyContract, Money
from paxman._capabilities.money.rules import _RULE_AUTHORITIES

__all__ = [
    "_RULE_AUTHORITIES",
    "CanonicalMoneyContract",
    "Money",
    "MoneyCapability",
]
