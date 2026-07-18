"""Boolean capability package.

Re-exports the public surface so callers can use
`from paxman._capabilities.boolean import BooleanCapability` (and the contract
sugar / Law 14 manifest) without reaching into submodules.
"""

from paxman._capabilities.boolean.canonicalizer import BooleanCapability
from paxman._capabilities.boolean.contract import Boolean, CanonicalBooleanContract
from paxman._capabilities.boolean.grammar import GRAMMARS, recognize
from paxman._capabilities.boolean.rules import _RULE_AUTHORITIES

__all__ = [
    "GRAMMARS",
    "_RULE_AUTHORITIES",
    "Boolean",
    "BooleanCapability",
    "CanonicalBooleanContract",
    "recognize",
]
