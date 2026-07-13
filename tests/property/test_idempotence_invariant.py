"""Mandate Law 2: canonicalize(canonicalize(x)) == canonicalize(x)."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from paxman import _orchestrator_runtime
from paxman._capabilities.builtins.email import EmailCapability
from paxman._capabilities.registry import CapabilityRegistry
from paxman._core.orchestrator import canonicalize
from paxman._core.types import Status


@pytest.fixture(autouse=True)
def _isolated_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    r = CapabilityRegistry()
    r.register(EmailCapability())
    r.freeze()
    monkeypatch.setattr(_orchestrator_runtime, "default_registry", r)


@pytest.mark.property
@settings(max_examples=50, deadline=None, derandomize=True)
@given(value=st.text(min_size=0, max_size=64))
def test_idempotence_invariant(value: str) -> None:
    """Mandate Law 2."""
    first = canonicalize(value, {"kind": "canonical_email"})
    if first.status is not Status.CANONICALIZED:
        return
    second = canonicalize(first.value, {"kind": "canonical_email"})
    assert second.status is Status.CANONICALIZED
    assert second.value == first.value
