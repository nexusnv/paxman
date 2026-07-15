"""Mandate Law 1: replay_hash matches sha256(canonical_bytes())."""

from __future__ import annotations

import hashlib

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from paxman import _orchestrator_runtime
from paxman._capabilities.email import EmailCapability
from paxman._core.engine import canonicalize
from paxman._registry.capability_registry import CapabilityRegistry


@pytest.fixture(autouse=True)
def _isolated_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    r = CapabilityRegistry()
    r.register(EmailCapability())
    r.freeze()
    monkeypatch.setattr(_orchestrator_runtime, "default_registry", r)


@pytest.mark.property
@settings(max_examples=30, deadline=None, derandomize=True)
@given(value=st.text(min_size=0, max_size=32))
def test_replay_hash_matches_canonical_bytes(value: str) -> None:
    """Mandate Law 1."""
    art = canonicalize(value, {"kind": "canonical_email"})
    expected = hashlib.sha256(art.canonical_bytes()).hexdigest()
    assert art.replay_hash == expected
