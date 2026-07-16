"""Phone capability package.

Re-exports the public surface so callers can use
`from paxman._capabilities.phone import PhoneCapability` (and the contract
sugar / Law 14 manifest) without reaching into submodules. Importing this
package triggers `contract.py`'s `register_contract` side-effect.
"""

from paxman._capabilities.phone.canonicalizer import PhoneCapability
from paxman._capabilities.phone.contract import CanonicalPhoneContract, Phone
from paxman._capabilities.phone.grammar import GRAMMARS, recognize
from paxman._capabilities.phone.rules import _RULE_PROVENANCE

__all__ = [
    "GRAMMARS",
    "_RULE_PROVENANCE",
    "CanonicalPhoneContract",
    "Phone",
    "PhoneCapability",
    "recognize",
]
