# src/paxman/_capabilities/ip/__init__.py
"""IP capability package.

Re-exports the public surface so callers can use
`from paxman._capabilities.ip import IPCapability` (and the contract
sugar / Law 14 manifest) without reaching into submodules.
"""

from paxman._capabilities.ip.canonicalizer import IPCapability
from paxman._capabilities.ip.contract import IP, CanonicalIPContract
from paxman._capabilities.ip.grammar import GRAMMARS, recognize
from paxman._capabilities.ip.rules import _RULE_AUTHORITIES

__all__ = [
    "GRAMMARS",
    "IP",
    "_RULE_AUTHORITIES",
    "CanonicalIPContract",
    "IPCapability",
    "recognize",
]
