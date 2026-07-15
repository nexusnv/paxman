"""Shared primitive types for Paxman v2.

Domain-free. Holds only closed Literal aliases and cross-cutting
primitives that no single capability owns.
"""

from __future__ import annotations

from typing import Literal

# Closed enum for provider_aliases in the v2.0.0 contract (mandate §6
# openness about deliberate scope).
ProviderAliasesPolicy = Literal["none", "gmail"]
