"""Tests for the CapabilityRegistry — the resolver / dispatcher.

Mandate §5.4: every supported (contract, value) pair must resolve to at
most one capability. Multiple claimants at resolve time yield
`Status.AMBIGUOUS` (handled by the orchestrator, not the registry).
"""
from __future__ import annotations

import pytest

from paxman._capabilities.protocol import Capability
from paxman._capabilities.registry import CapabilityRegistry
from paxman._contracts.contract import CanonicalEmailContract, parse_contract
from paxman._core.types import CapabilityResult, Status
from paxman._errors import ConfigurationError, FrozenRegistryError


class _AlwaysTrue:
    name = "A"

    def can_handle(self, contract, value):  # type: ignore[no-untyped-def]
        return True

    def canonicalize(self, value, contract):  # type: ignore[no-untyped-def]
        return CapabilityResult(status=Status.CANONICALIZED, value=value)


class _AlsoAlwaysTrue:
    name = "B"

    def can_handle(self, contract, value):  # type: ignore[no-untyped-def]
        return True

    def canonicalize(self, value, contract):  # type: ignore[no-untyped-def]
        return CapabilityResult(status=Status.CANONICALIZED, value=value)


class TestRegister:
    def test_register_then_resolve(self) -> None:
        r = CapabilityRegistry()
        r.register(_AlwaysTrue())
        c = parse_contract({"kind": "canonical_email"})
        assert r.resolve(c, "x@y.z") is not None
        assert r.resolve(c, "x@y.z").name == "A"

    def test_duplicate_name_raises(self) -> None:
        r = CapabilityRegistry()
        r.register(_AlwaysTrue())
        # Different name — no conflict.
        r.register(_AlsoAlwaysTrue())
        # Now register a duplicate of "A"
        class _Dup:
            name = "A"
            def can_handle(self, contract, value): return True
            def canonicalize(self, value, contract):
                return CapabilityResult(status=Status.CANONICALIZED, value=value)
        with pytest.raises(ConfigurationError):
            r.register(_Dup())

    def test_register_after_freeze_raises(self) -> None:
        r = CapabilityRegistry()
        r.register(_AlwaysTrue())
        r.freeze()
        with pytest.raises(FrozenRegistryError):
            r.register(_AlsoAlwaysTrue())

    def test_capability_set_hash_is_deterministic(self) -> None:
        r1 = CapabilityRegistry()
        r1.register(_AlwaysTrue())
        r1.register(_AlsoAlwaysTrue())
        r2 = CapabilityRegistry()
        r2.register(_AlsoAlwaysTrue())
        r2.register(_AlwaysTrue())
        # Same names in different order produce the same hash because
        # the hash is over a sorted tuple.
        assert r1.capabilities_hash() == r2.capabilities_hash()


class TestResolve:
    def test_resolve_with_no_matching_capability_returns_none(self) -> None:
        r = CapabilityRegistry()
        # No capabilities registered.
        c = parse_contract({"kind": "canonical_email"})
        assert r.resolve(c, "x@y.z") is None

    def test_resolve_returns_capability_when_match(self) -> None:
        r = CapabilityRegistry()
        r.register(_AlwaysTrue())
        c = parse_contract({"kind": "canonical_email"})
        cap = r.resolve(c, "x@y.z")
        assert cap is not None
        assert cap.name == "A"

    def test_resolve_returns_all_claimants(self) -> None:
        # Mandate §5.4: the registry can return multiple claimants; the
        # orchestrator maps that to Status.AMBIGUOUS.
        r = CapabilityRegistry()
        r.register(_AlwaysTrue())
        r.register(_AlsoAlwaysTrue())
        c = parse_contract({"kind": "canonical_email"})
        claimants = r.resolve_all(c, "x@y.z")
        assert len(claimants) == 2
        assert {c.name for c in claimants} == {"A", "B"}
