"""CapabilityRegistry: the resolver / dispatcher.

Mandate §6.1: this replaces the v1.x planner. The registry holds
capabilities and answers `resolve(contract, value)` with the single
capability (or set of claimants) that explicitly declares it
canonicalizes the pair. There is no ranking, no scoring, no "best
match" (mandate Law 3).

`freeze()` makes the capability set immutable. After the first
canonicalize call, the default registry is frozen implicitly; further
`register` calls raise `FrozenRegistryError`. The frozen-registry
invariant is what makes the capability set part of the determinism
invariant (mandate §1.2, Law 1) mechanically enforceable.
"""
from __future__ import annotations

import hashlib
from typing import Any

from paxman._capabilities.protocol import Capability
from paxman._contracts.contract import Contract
from paxman._errors import ConfigurationError, FrozenRegistryError


class CapabilityRegistry:
    """The default, module-level registry used by `paxman.canonicalize`."""

    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}
        self._frozen: bool = False

    def register(self, capability: Capability) -> None:
        """Register a capability. Raises if the name is taken or the
        registry is frozen."""
        if self._frozen:
            raise FrozenRegistryError(
                "cannot register capability: registry is frozen"
            )
        if not isinstance(capability, Capability):
            raise ConfigurationError(
                f"object is not a Capability: {type(capability).__name__}"
            )
        name = capability.name
        if name in self._capabilities:
            raise ConfigurationError(
                f"capability name already registered: {name!r}"
            )
        self._capabilities[name] = capability

    def freeze(self) -> None:
        """Make the registry immutable. Idempotent."""
        self._frozen = True

    @property
    def is_frozen(self) -> bool:
        return self._frozen

    def resolve(self, contract: Contract, value: Any) -> Capability | None:
        """Return the single matching capability, or None.

        If multiple capabilities claim the same pair, returns the first
        (in registration order) but `resolve_all` returns the full set.
        The orchestrator uses `resolve_all` so the per-call
        determination is correct under any order.
        """
        claimants = self.resolve_all(contract, value)
        if not claimants:
            return None
        return claimants[0]

    def resolve_all(self, contract: Contract, value: Any) -> list[Capability]:
        """Return every capability that claims the (contract, value) pair."""
        return [
            cap
            for cap in self._capabilities.values()
            if cap.can_handle(contract, value)
        ]

    def capabilities_hash(self) -> str:
        """Deterministic hash of the registered capability set.

        Used as the `capabilities_hash` component of the VersionStamp
        recorded on every artifact (mandate Law 12, §8).
        """
        names = sorted(self._capabilities.keys())
        joined = "\n".join(names).encode("utf-8")
        return hashlib.sha256(joined).hexdigest()
