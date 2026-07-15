"""Tests for the CapabilityRegistry — the resolver / dispatcher.

Mandate §5.4: every supported (contract, value) pair must resolve to at
most one capability. Multiple claimants at resolve time yield
`Status.AMBIGUOUS` (handled by the orchestrator, not the registry).
"""

from __future__ import annotations

from typing import Any

import pytest

from paxman._capabilities.email.contract import CanonicalEmailContract
from paxman._core.result import CapabilityResult
from paxman._core.status import Status
from paxman._dsl.parser import parse_contract
from paxman._errors import ConfigurationError, FrozenRegistryError
from paxman._registry.capability_registry import CapabilityRegistry


class _AlwaysTrue:
    name: str = "A"

    def can_handle(self, contract: CanonicalEmailContract, value: object) -> bool:
        return True

    def canonicalize(self, value: object, contract: CanonicalEmailContract) -> CapabilityResult:
        return CapabilityResult(status=Status.CANONICALIZED, value=str(value))


class _AlsoAlwaysTrue:
    name: str = "B"

    def can_handle(self, contract: CanonicalEmailContract, value: object) -> bool:
        return True

    def canonicalize(self, value: object, contract: CanonicalEmailContract) -> CapabilityResult:
        return CapabilityResult(status=Status.CANONICALIZED, value=str(value))


class TestRegister:
    def test_register_then_resolve_all_finds_it(self) -> None:
        r = CapabilityRegistry()
        r.register(_AlwaysTrue())
        c = parse_contract({"kind": "canonical_email"})
        claimants = r.resolve_all(c, "x@y.z")
        assert len(claimants) == 1
        assert claimants[0].name == "A"

    def test_duplicate_name_raises(self) -> None:
        r = CapabilityRegistry()
        r.register(_AlwaysTrue())
        r.register(_AlsoAlwaysTrue())  # different name — no conflict

        # Now register a duplicate of "A"
        class _Dup:
            name: str = "A"

            def can_handle(self, contract: Any, value: Any) -> bool:
                return True

            def canonicalize(self, value: Any, contract: Any) -> CapabilityResult:
                return CapabilityResult(status=Status.CANONICALIZED, value=str(value))

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


class TestResolveAll:
    def test_resolve_all_with_no_matching_capability_returns_empty(self) -> None:
        r = CapabilityRegistry()
        c = parse_contract({"kind": "canonical_email"})
        assert r.resolve_all(c, "x@y.z") == []

    def test_resolve_all_returns_capability_when_match(self) -> None:
        r = CapabilityRegistry()
        r.register(_AlwaysTrue())
        c = parse_contract({"kind": "canonical_email"})
        claimants = r.resolve_all(c, "x@y.z")
        assert len(claimants) == 1
        assert claimants[0].name == "A"

    def test_resolve_all_returns_all_claimants(self) -> None:
        # Mandate §5.4: the registry returns every claimant; the
        # orchestrator maps multiple claimants to Status.AMBIGUOUS.
        r = CapabilityRegistry()
        r.register(_AlwaysTrue())
        r.register(_AlsoAlwaysTrue())
        c = parse_contract({"kind": "canonical_email"})
        claimants = r.resolve_all(c, "x@y.z")
        assert len(claimants) == 2
        assert {c.name for c in claimants} == {"A", "B"}
