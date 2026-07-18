"""UUID capability package.

Re-exports the public surface so callers can use
`from paxman._capabilities.uuid import UUIDCapability` (and the contract
sugar / Law 14 manifest) without reaching into submodules.
"""

from paxman._capabilities.uuid.canonicalizer import UUIDCapability
from paxman._capabilities.uuid.contract import UUID, CanonicalUUIDContract
from paxman._capabilities.uuid.grammar import GRAMMARS, recognize
from paxman._capabilities.uuid.rules import _RULE_AUTHORITIES

__all__ = [
    "GRAMMARS",
    "UUID",
    "_RULE_AUTHORITIES",
    "CanonicalUUIDContract",
    "UUIDCapability",
    "recognize",
]
