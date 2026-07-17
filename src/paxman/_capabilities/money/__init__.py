# src/paxman/_capabilities/money/__init__.py
"""Money capability package (re-exports)."""

from __future__ import annotations

from paxman._capabilities.money.contract import CanonicalMoneyContract, Money

__all__ = ["CanonicalMoneyContract", "Money"]
