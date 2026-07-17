# src/paxman/_capabilities/country/__init__.py
"""Country capability package (re-exports)."""

from __future__ import annotations

from paxman._capabilities.country.contract import CanonicalCountryContract, Country

__all__ = [
    "CanonicalCountryContract",
    "Country",
]
