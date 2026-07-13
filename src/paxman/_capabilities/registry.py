"""CapabilityRegistry: the resolver / dispatcher.

Mandate §6.1: this replaces the v1.x planner. The registry holds
capabilities and answers `resolve_all(contract, value)` with the set of
capabilities that explicitly declare they canonicalize the pair. There
is no ranking, no scoring, and no arbitrary selection among claimants
(mandate Law 3).

The orchestrator reads the full claimant set and classifies
`Status.AMBIGUOUS` when more than one capability claims the same pair
(mandate §5.4, Law 4). Callers must not silently pick a single
claimant.

`freeze()` makes the capability set immutable. After the first
canonicalize call, the default registry is frozen implicitly; further
`register` calls raise `FrozenRegistryError`. The frozen-registry
invariant is what makes the capability set part of the determinism
invariant (mandate §1.2, Law 1) mechanically enforceable.
"""
from __future__ import annotations

import hashlib

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

    def resolve_all(self, contract: Contract, value: object) -> list[Capability]:
        """Return every capability that claims the (contract, value) pair.

        Callers (the orchestrator) inspect the full set and classify
        `Status.AMBIGUOUS` when the set has more than one entry
        (mandate §5.4). Callers MUST NOT silently pick a single entry.
        """
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
