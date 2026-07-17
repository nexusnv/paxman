"""Tests for the public API surface (mandate §1.3)."""

from __future__ import annotations

import pytest

import paxman


class TestPublicAPI:
    def test_canonicalize_is_exported(self) -> None:
        assert hasattr(paxman, "canonicalize")
        assert callable(paxman.canonicalize)

    def test_replay_is_exported(self) -> None:
        assert hasattr(paxman, "replay")
        assert callable(paxman.replay)

    def test_register_capability_is_exported(self) -> None:
        assert hasattr(paxman, "register_capability")
        assert callable(paxman.register_capability)

    def test_version_is_present(self) -> None:
        assert isinstance(paxman.__version__, str)
        assert paxman.__version__  # non-empty

    def test_no_unexpected_public_symbols(self) -> None:
        # The v2.0.0 public surface is exactly the set below. Adding
        # to this set requires a design spec and an implementation
        # plan (mandate: one spec + one plan per change). The check
        # is exact (==) so a stray import is caught.
        #
        # 'Any' is a typing primitive leaked by the PEP 562 __getattr__
        # return type. The v2.0.0 plan explicitly accepts this trade-off.
        expected = {
            "Any",
            "canonicalize",
            "replay",
            "register_capability",
            "ExecutionArtifact",
            "Status",
            "Evidence",
            "VersionStamp",
            "CapabilityResult",
            "ValidationResult",
            "Contract",
            "CanonicalBooleanContract",
            "CanonicalDateContract",
            "CanonicalEmailContract",
            "CanonicalGeolocationContract",
            "CanonicalIPContract",
            "CanonicalPhoneContract",
            "CanonicalUUIDContract",
            "CanonicalURLContract",
            "parse_contract",
            "Capability",
            "CapabilityRegistry",
            "PaxmanError",
            "CanonicalizationError",
            "ContractError",
            "Email",
            "Date",
            "UUID",
            "Phone",
            "URL",
            "ConfigurationError",
            "FrozenRegistryError",
            "Geolocation",
            "IP",
            "UnsupportedContractError",
            "VersionMismatchError",
            "Boolean",
            "Money",
            "CanonicalMoneyContract",
            "annotations",
        }
        actual = {n for n in dir(paxman) if not n.startswith("_")}
        assert actual == expected

    def test_canonicalize_end_to_end(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from paxman import _orchestrator_runtime
        from paxman._capabilities.email import EmailCapability
        from paxman._registry.capability_registry import CapabilityRegistry

        r = CapabilityRegistry()
        r.register(EmailCapability())
        r.freeze()
        monkeypatch.setattr(_orchestrator_runtime, "default_registry", r)
        art = paxman.canonicalize("  John.Doe@Example.COM  ", {"kind": "canonical_email"})
        assert art.status.value == "canonicalized"
        assert art.value == "john.doe@example.com"

    def test_replay_end_to_end(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from paxman import _orchestrator_runtime
        from paxman._capabilities.email import EmailCapability
        from paxman._registry.capability_registry import CapabilityRegistry

        r = CapabilityRegistry()
        r.register(EmailCapability())
        r.freeze()
        monkeypatch.setattr(_orchestrator_runtime, "default_registry", r)
        art = paxman.canonicalize("a@b.c", {"kind": "canonical_email"})
        rehydrated = paxman.replay(art, {"kind": "canonical_email"})
        assert rehydrated == art
        assert rehydrated.canonical_bytes() == art.canonical_bytes()
