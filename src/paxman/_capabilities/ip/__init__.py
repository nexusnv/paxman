# src/paxman/_capabilities/ip/__init__.py
"""IP capability package (contract surface; canonicalizer added later)."""

from paxman._capabilities.ip.contract import IP, CanonicalIPContract

__all__ = [
    "IP",
    "CanonicalIPContract",
]
