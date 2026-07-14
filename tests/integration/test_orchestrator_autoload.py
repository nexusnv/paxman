"""Tests that the orchestrator lazily auto-loads built-in capabilities.

Spec §2.4: the orchestrator calls registry.load_builtins(
builtin_capabilities()) BEFORE registry.freeze() on the first
canonicalize. This makes the built-in email capability available to a
novice who has not called register_capability.

This test uses a fresh, empty registry via monkeypatch — the novice's
"did nothing" path. The built-in auto-loads on the first canonicalize;
replay then recomputes the same capabilities_hash from the same
default_registry and matches.
"""

from __future__ import annotations

import pytest

import paxman
from paxman import Email, FrozenRegistryError, Status, _orchestrator_runtime
from paxman._capabilities.builtins.email import EmailCapability
from paxman._capabilities.registry import CapabilityRegistry


@pytest.fixture(autouse=True)
def _fresh_empty_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the module-level default_registry with a fresh one.

    This is the novice-did-nothing path: the registry starts empty and
    unfrozen. The orchestrator must auto-load built-ins on the first
    canonicalize.

    We use monkeypatch.setattr (NOT a hypothetical reset()/clear()
    method — none exists on CapabilityRegistry; spec §4.1).
    """
    monkeypatch.setattr(_orchestrator_runtime, "default_registry", CapabilityRegistry())


@pytest.mark.integration
class TestOrchestratorAutoLoads:
    def test_canonicalize_works_without_register_capability(self) -> None:
        """The novice did NOTHING. No register_capability call.

        The built-in EmailCapability auto-loaded on this call.
        """
        result = paxman.canonicalize("a@b.c", {"kind": "canonical_email"})
        assert result.status is Status.CANONICALIZED
        assert result.value == "a@b.c"

    def test_registry_is_frozen_after_first_canonicalize(self) -> None:
        """After the first canonicalize, the registry is frozen."""
        paxman.canonicalize("a@b.c", {"kind": "canonical_email"})
        from paxman import _orchestrator_runtime

        assert _orchestrator_runtime.default_registry.is_frozen is True

    def test_replay_works_after_autoload(self) -> None:
        """Replay recomputes capabilities_hash from the same
        default_registry. The built-in auto-loaded into the same
        registry, so the hash matches.
        """
        artifact = paxman.canonicalize("a@b.c", {"kind": "canonical_email"})
        rehydrated = paxman.replay(artifact, {"kind": "canonical_email"})
        assert rehydrated == artifact
        assert rehydrated.canonical_bytes() == artifact.canonical_bytes()

    def test_frozen_registry_error_on_register_after_canonicalize(self) -> None:
        """After canonicalize, the registry is frozen and register must raise."""
        paxman.canonicalize("a@b.c", {"kind": "canonical_email"})
        with pytest.raises(FrozenRegistryError):
            paxman.register_capability(EmailCapability())

    def test_works_with_email_factory_too(self) -> None:
        """Using the Email() factory as the contract also works."""

        result = paxman.canonicalize("  John.Doe@Example.COM  ", Email())
        assert result.status is Status.CANONICALIZED
        assert result.value == "john.doe@example.com"
