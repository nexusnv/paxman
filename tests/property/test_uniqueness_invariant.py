"""Mandate §5.4: multiple claimants -> Status.AMBIGUOUS, never a silent pick."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from paxman import _orchestrator_runtime
from paxman._core.engine import canonicalize
from paxman._core.result import CapabilityResult
from paxman._core.status import Status
from paxman._registry.capability_registry import CapabilityRegistry


class _A:
    name = "A"

    def can_handle(self, contract: object, value: object) -> bool:
        return True

    def canonicalize(self, value: object, contract: object) -> CapabilityResult:
        return CapabilityResult(status=Status.CANONICALIZED, value=str(value))


class _B:
    name = "B"

    def can_handle(self, contract: object, value: object) -> bool:
        return True

    def canonicalize(self, value: object, contract: object) -> CapabilityResult:
        return CapabilityResult(status=Status.CANONICALIZED, value=str(value))


@pytest.fixture(autouse=True)
def _two_claimants_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    r = CapabilityRegistry()
    r.register(_A())
    r.register(_B())
    r.freeze()
    monkeypatch.setattr(_orchestrator_runtime, "default_registry", r)


@pytest.mark.property
@settings(max_examples=30, deadline=None, derandomize=True)
@given(value=st.text(min_size=1, max_size=32))
def test_uniqueness_invariant(value: str) -> None:
    art = canonicalize(value, {"kind": "canonical_email"})
    assert art.status is Status.AMBIGUOUS
    rule_names = {e.rule for e in art.evidence}
    assert "multiple_claimants" in rule_names
