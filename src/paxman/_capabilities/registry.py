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
            raise FrozenRegistryError("cannot register capability: registry is frozen")
        if not isinstance(capability, Capability):
            raise ConfigurationError(f"object is not a Capability: {type(capability).__name__}")
        name = capability.name
        if name in self._capabilities:
            raise ConfigurationError(f"capability name already registered: {name!r}")
        self._capabilities[name] = capability

    def freeze(self) -> None:
        """Make the registry immutable. Idempotent."""
        self._frozen = True

    def load_builtins(self, builtins: list[Capability]) -> None:
        """Register built-in capabilities whose names are not already present.

        MANDATE §4.3 + Law 8a: built-in loading is explicit at the
        call site (the orchestrator's first-canonicalize step), never
        at import. Law 6: the loading happens inside the orchestrator,
        not as user-visible API.

        Idempotency + ordering invariants (spec §2.4):
        - skipping a name that is already registered is NOT a
          ConfigurationError — the user intentionally registered a
          capability of that name before their first canonicalize, and
          that registration is the one that wins (§5.3 litmus: the
          user's knowledge wins over Paxman's).
        - is a no-op when the registry is already frozen (defense in
          depth; the orchestrator only calls this when not frozen).
        - the resulting capabilities_hash includes ALL registered
          capabilities (user + built-in) so replay (which recompute-
          hashes the same default_registry) still matches.

        Args:
            builtins: the list returned by builtin_capabilities().
        """
        if self._frozen:
            return
        existing = set(self._capabilities.keys())
        for cap in builtins:
            if cap.name not in existing:
                self._capabilities[cap.name] = cap

    @property
    def is_frozen(self) -> bool:
        return self._frozen

    def resolve_all(self, contract: Contract, value: object) -> list[Capability]:
        """Return every capability that claims the (contract, value) pair.

        Callers (the orchestrator) inspect the full set and classify
        `Status.AMBIGUOUS` when the set has more than one entry
        (mandate §5.4). Callers MUST NOT silently pick a single entry.

        Results are sorted by capability name so two registries with
        the same capability set registered in different orders yield
        the same `resolve_all` output, the same `AMBIGUOUS` evidence
        string, and therefore the same `replay_hash` (mandate Law 1).
        Without this sort, the dict's insertion order would leak into
        the evidence and break replay byte-equality across registration
        orders.
        """
        claimants = [cap for cap in self._capabilities.values() if cap.can_handle(contract, value)]
        claimants.sort(key=lambda c: c.name)
        return claimants

    def capabilities_hash(self) -> str:
        """Deterministic hash of the registered capability set.

        Used as the `capabilities_hash` component of the VersionStamp
        recorded on every artifact (mandate Law 12, §8).
        """
        names = sorted(self._capabilities.keys())
        joined = "\n".join(names).encode("utf-8")
        return hashlib.sha256(joined).hexdigest()
