"""Date capability package.

Re-exports the public surface so callers can use
`from paxman._capabilities.date import DateCapability` (and the contract
sugar / Law 14 manifest) without reaching into submodules.
"""

from paxman._capabilities.date.canonicalizer import DateCapability
from paxman._capabilities.date.contract import CanonicalDateContract, Date
from paxman._capabilities.date.rules import _RULE_AUTHORITIES

__all__ = [
    "_RULE_AUTHORITIES",
    "CanonicalDateContract",
    "Date",
    "DateCapability",
]
