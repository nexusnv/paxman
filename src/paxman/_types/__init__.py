"""Shared contract-policy value types.

Mandate Law 5 (the contract is the truth): these types back the
policy fields of contract value objects, so a capability *reads* them
rather than inventing policy.
"""

from paxman._types.common import ProviderAliasesPolicy

__all__ = ["ProviderAliasesPolicy"]
