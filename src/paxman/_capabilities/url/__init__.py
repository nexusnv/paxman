from paxman._capabilities.url.canonicalizer import URLCapability
from paxman._capabilities.url.contract import URL, CanonicalURLContract
from paxman._capabilities.url.grammar import GRAMMARS, recognize
from paxman._capabilities.url.rules import _RULE_PROVENANCE

# Importing this package fires contract.py's register_contract("canonical_url", ...)
# side-effect (self-registration, MANDATE §6.5).
__all__ = [
    "GRAMMARS",
    "URL",
    "_RULE_PROVENANCE",
    "CanonicalURLContract",
    "URLCapability",
    "recognize",
]
