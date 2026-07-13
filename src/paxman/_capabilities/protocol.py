"""The Capability Protocol — the only extension point of Paxman v2.

Mandate §5.1: a capability transforms, it does not orchestrate. The
Protocol deliberately omits control-flow verbs (`next`, `execute`,
`pipeline`, `stage`, `context switching`, `branching`).

The Protocol is `@runtime_checkable` so the registry can validate
duck-typing at register time.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from paxman._contracts.contract import Contract
from paxman._core.types import CapabilityResult


@runtime_checkable
class Capability(Protocol):
    """A pure deterministic transformation that answers
    'Can I canonicalize this value, given this contract?'"""

    name: str

    def can_handle(self, contract: Contract, value: Any) -> bool: ...

    def canonicalize(self, value: Any, contract: Contract) -> CapabilityResult: ...
