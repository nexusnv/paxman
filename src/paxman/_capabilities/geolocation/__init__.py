# src/paxman/_capabilities/geolocation/__init__.py
"""Geolocation capability package (re-exports).

This module only re-exports public symbols. Importing it has no side effects:
no capability is registered and no pipeline is modified. Every re-exported
symbol is deterministic and pure (MANDATE Law 1 — Identity, Law 2 —
Determinism). The registry is frozen by the engine on the first
`canonicalize`, not by importing this package.
"""

from __future__ import annotations

from paxman._capabilities.geolocation.canonicalizer import GeolocationCapability
from paxman._capabilities.geolocation.contract import CanonicalGeolocationContract, Geolocation

__all__ = [
    "CanonicalGeolocationContract",
    "Geolocation",
    "GeolocationCapability",
]
