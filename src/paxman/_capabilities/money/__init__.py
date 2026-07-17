# src/paxman/_capabilities/money/__init__.py
"""Money capability package (re-exports)."""

from __future__ import annotations

from paxman._capabilities.money.canonicalizer import MoneyCapability
from paxman._capabilities.money.contract import CanonicalMoneyContract, Money
from paxman._capabilities.money.rules import _RULE_PROVENANCE

__all__ = [
    "_RULE_PROVENANCE",
    "CanonicalMoneyContract",
    "Money",
    "MoneyCapability",
]
