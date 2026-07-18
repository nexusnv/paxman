"""Email capability package.

Re-exports the public surface so callers can use
`from paxman._capabilities.email import EmailCapability` (and the contract
sugar / Law 14 manifest) without reaching into submodules.
"""

from paxman._capabilities.email.canonicalizer import EmailCapability
from paxman._capabilities.email.contract import CanonicalEmailContract, Email
from paxman._capabilities.email.grammar import GRAMMARS, recognize
from paxman._capabilities.email.rules import _RULE_AUTHORITIES

__all__ = [
    "GRAMMARS",
    "_RULE_AUTHORITIES",
    "CanonicalEmailContract",
    "Email",
    "EmailCapability",
    "recognize",
]
