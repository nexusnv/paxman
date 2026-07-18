# src/paxman/_capabilities/country/__init__.py
"""Country capability package (re-exports).

Mandate scope: this package implements a single deterministic capability
(``CountryCapability``) that canonicalizes country representations to ISO
3166-1 alpha-2 codes. It operates under MANDATE Law 8a (side-effect-free
capability boundary — depends only on bundled, versioned state) and Law 14 /
Law 15 (provenance: every rule cites a source; the cited ISO 3166-1:2024
enumeration is adopted in full via the shared ``_iso3166`` module). No
re-export here violates any mandate law; these are the public surface of a
single capability.
"""

from __future__ import annotations

from paxman._capabilities.country.canonicalizer import CountryCapability
from paxman._capabilities.country.contract import CanonicalCountryContract, Country
from paxman._capabilities.country.rules import _RULE_AUTHORITIES

__all__ = [
    "_RULE_AUTHORITIES",
    "CanonicalCountryContract",
    "Country",
    "CountryCapability",
]
