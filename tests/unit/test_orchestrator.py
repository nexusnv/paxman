"""Tests for the orchestrator (the pipeline Paxman owns)."""
from __future__ import annotations

import pytest

from paxman._capabilities.builtins.email import EmailCapability
from paxman._capabilities.registry import CapabilityRegistry
from paxman._contracts.contract import parse_contract
from paxman._core.orchestrator import canonicalize
from paxman._core.types import Status
from paxman._errors import (
    CanonicalizationError,
    ContractError,
)


def _setup_email_registry() -> CapabilityRegistry:
    r = CapabilityRegistry()
    r.register(EmailCapability())
    r.freeze()
    return r


class TestOrchestrator:
    def test_canonicalize_canonicalizes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from paxman import _orchestrator_runtime
        monkeypatch.setattr(_orchestrator_runtime, "default_registry", _setup_email_registry())
        art = canonicalize("  John.Doe@Example.COM  ", {"kind": "canonical_email"})
        assert art.status is Status.CANONICALIZED
        assert art.value == "john.doe@example.com"

    def test_canonicalize_unknown_kind_yields_unsupported(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from paxman import _orchestrator_runtime
        monkeypatch.setattr(_orchestrator_runtime, "default_registry", _setup_email_registry())
        art = canonicalize("a@b.c", {"kind": "unknown_kind"})
        assert art.status is Status.UNSUPPORTED

    def test_canonicalize_with_no_matching_capability_yields_unsupported(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from paxman import _orchestrator_runtime
        # Empty registry: no capabilities at all.
        r = CapabilityRegistry()
        r.freeze()
        monkeypatch.setattr(_orchestrator_runtime, "default_registry", r)
        art = canonicalize("a@b.c", {"kind": "canonical_email"})
        assert art.status is Status.UNSUPPORTED

    def test_canonicalize_ambiguous_yields_ambiguous(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from paxman import _orchestrator_runtime
        # Two capabilities both claim the same pair.
        from paxman._core.types import CapabilityResult
        from paxman._contracts.contract import Contract

        class _A:
            name: str = "A"

            def can_handle(self, contract: Contract, value: object) -> bool:
                return True

            def canonicalize(self, value: object, contract: Contract) -> CapabilityResult:
                return CapabilityResult(
                    status=Status.CANONICALIZED, value=str(value)
                )

        class _B:
            name: str = "B"

            def can_handle(self, contract: Contract, value: object) -> bool:
                return True

            def canonicalize(self, value: object, contract: Contract) -> CapabilityResult:
                return CapabilityResult(
                    status=Status.CANONICALIZED, value=str(value)
                )

        r = CapabilityRegistry()
        r.register(_A())
        r.register(_B())
        r.freeze()
        monkeypatch.setattr(_orchestrator_runtime, "default_registry", r)
        art = canonicalize("a@b.c", {"kind": "canonical_email"})
        assert art.status is Status.AMBIGUOUS
        rule_names = {e.rule for e in art.evidence}
        assert "multiple_claimants" in rule_names

    def test_canonicalize_invalid_yields_invalid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from paxman import _orchestrator_runtime
        monkeypatch.setattr(_orchestrator_runtime, "default_registry", _setup_email_registry())
        art = canonicalize("not-an-email", {"kind": "canonical_email"})
        assert art.status is Status.INVALID
