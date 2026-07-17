"""Property tests for the CountryCapability invariants (MANDATE §1.2)."""

from __future__ import annotations

import hypothesis.strategies as st
from hypothesis import given, settings

from paxman import Country, canonicalize, replay
from paxman._core.status import Status

# A small but representative set of CANONICALIZED inputs.
_canonical_inputs = st.sampled_from(
    ["US", "us", "USA", "United States", "UK", "GB", "DE", "germany", "France"]
)


@settings(derandomize=True, max_examples=50)
@given(_canonical_inputs)
def test_idempotence_invariant(value: str) -> None:
    c = Country()
    first = canonicalize(value, c)
    assert first.status == Status.CANONICALIZED
    second = canonicalize(first.value, c)
    assert second.value == first.value


@settings(derandomize=True, max_examples=50)
@given(_canonical_inputs)
def test_replay_invariant(value: str) -> None:
    c = Country()
    result = canonicalize(value, c)
    assert result.status == Status.CANONICALIZED
    rehydrated = replay(result, c)
    assert rehydrated == result


@settings(derandomize=True, max_examples=50)
@given(_canonical_inputs)
def test_artifact_immutable(value: str) -> None:
    import attrs

    c = Country()
    result = canonicalize(value, c)
    try:
        result.status = Status.INVALID  # type: ignore[misc]
    except attrs.exceptions.FrozenInstanceError:
        pass
    else:
        raise AssertionError("artifact was mutable")
