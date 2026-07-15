"""Mandate Law 12: replay(artifact) == artifact byte-for-byte."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from paxman import _orchestrator_runtime
from paxman._capabilities.email import EmailCapability
from paxman._core.engine import canonicalize
from paxman._core.replay import replay
from paxman._registry.capability_registry import CapabilityRegistry


@pytest.fixture(autouse=True)
def _isolated_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    r = CapabilityRegistry()
    r.register(EmailCapability())
    r.freeze()
    monkeypatch.setattr(_orchestrator_runtime, "default_registry", r)


@pytest.mark.property
@settings(max_examples=50, deadline=None, derandomize=True)
@given(value=st.text(min_size=0, max_size=64))
def test_replay_byte_equal_invariant(value: str) -> None:
    """Mandate Law 12: replay holds for every artifact, not only canonicalized ones."""
    art = canonicalize(value, {"kind": "canonical_email"})
    rehydrated = replay(art, {"kind": "canonical_email"})
    assert rehydrated == art
    assert rehydrated.canonical_bytes() == art.canonical_bytes()
