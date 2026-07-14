"""Mandate Law 2: canonicalize(canonicalize(x)) == canonicalize(x) for dates."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from paxman import Date, _orchestrator_runtime
from paxman._capabilities.builtins.date import DateCapability
from paxman._capabilities.registry import CapabilityRegistry
from paxman._core.orchestrator import canonicalize
from paxman._core.types import Status


@pytest.fixture(autouse=True)
def _isolated_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    r = CapabilityRegistry()
    r.register(DateCapability())
    r.freeze()
    monkeypatch.setattr(_orchestrator_runtime, "default_registry", r)


_ISO_DATES = st.builds(
    lambda y, m, d: f"{y:04d}-{m:02d}-{d:02d}",
    st.integers(1970, 2999),
    st.integers(1, 12),
    st.integers(1, 28),
)


@pytest.mark.property
@settings(max_examples=50, deadline=None, derandomize=True)
@given(value=_ISO_DATES)
def test_date_idempotence(value: str) -> None:
    first = canonicalize(value, Date(locale="ISO"))
    if first.status is not Status.CANONICALIZED:
        return
    second = canonicalize(first.value, Date(locale="ISO"))
    assert second.status is Status.CANONICALIZED
    assert second.value == first.value
