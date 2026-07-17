# src/paxman/_capabilities/country/__init__.py
"""Country capability package (re-exports)."""

from __future__ import annotations

from paxman._capabilities.country.canonicalizer import CountryCapability
from paxman._capabilities.country.contract import CanonicalCountryContract, Country
from paxman._capabilities.country.rules import _RULE_PROVENANCE

__all__ = [
    "_RULE_PROVENANCE",
    "CanonicalCountryContract",
    "Country",
    "CountryCapability",
]
