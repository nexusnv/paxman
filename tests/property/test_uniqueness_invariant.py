"""Mandate §5.4: multiple claimants -> Status.AMBIGUOUS, never a silent pick."""
from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from paxman._capabilities.registry import CapabilityRegistry
from paxman._core.types import CapabilityResult, Status
from paxman import _orchestrator_runtime
from paxman._core.orchestrator import canonicalize


class _A:
    name = "A"
    def can_handle(self, c, v): return True
    def canonicalize(self, v, c):
        return CapabilityResult(status=Status.CANONICALIZED, value=str(v))


class _B:
    name = "B"
    def can_handle(self, c, v): return True
    def canonicalize(self, v, c):
        return CapabilityResult(status=Status.CANONICALIZED, value=str(v))


@settings(max_examples=30, deadline=None)
@given(value=st.text(min_size=1, max_size=32))
def test_uniqueness_invariant(value: str) -> None:
    r = CapabilityRegistry()
    r.register(_A())
    r.register(_B())
    r.freeze()
    _orchestrator_runtime.default_registry = r
    art = canonicalize(value, {"kind": "canonical_email"})
    assert art.status is Status.AMBIGUOUS
    rule_names = {e.rule for e in art.evidence}
    assert "multiple_claimants" in rule_names
