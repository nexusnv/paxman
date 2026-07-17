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
    # Law 12 (Replayability): the rehydrated artifact must be byte-for-byte
    # equal to the original, not just object-equal. canonical_bytes() is the
    # deterministic serialization used for the replay_hash.
    assert rehydrated.canonical_bytes() == result.canonical_bytes()


@settings(derandomize=True, max_examples=50)
@given(_canonical_inputs)
def test_artifact_immutable(value: str) -> None:
    import attrs

    c = Country()
    result = canonicalize(value, c)
    try:
        setattr(result, "status", Status.INVALID)  # noqa: B010 - testing frozen immutability
    except attrs.exceptions.FrozenInstanceError:
        pass
    else:
        raise AssertionError("artifact was mutable")


# Expansion axes (numeric / localized / historical) must also satisfy the
# idempotence and replay invariants — these are the riskiest new code paths.
_numeric_inputs = st.sampled_from(["840", "392", "076", "004", "276", "156"])
_localized_inputs = st.sampled_from(
    ["日本", "中华人民共和国", "Россия", "المملكة المتحدة", "대한민국", "États-Unis", "états-unis"]
)
_historical_inputs = st.sampled_from(
    ["BURMA", "SWAZILAND", "CEYLON", "PERSIA", "ZAIRE", "YUGOSLAVIA", "SIAM"]
)


@settings(derandomize=True, max_examples=50)
@given(_numeric_inputs)
def test_numeric_axis_idempotent_replay(value: str) -> None:
    c = Country()
    first = canonicalize(value, c)
    assert first.status == Status.CANONICALIZED
    second = canonicalize(first.value, c)
    assert second.value == first.value
    assert replay(first, c) == first
    assert replay(first, c).canonical_bytes() == first.canonical_bytes()


@settings(derandomize=True, max_examples=50)
@given(_localized_inputs)
def test_localized_axis_idempotent_replay(value: str) -> None:
    c = Country(localized_names=True)
    first = canonicalize(value, c)
    assert first.status == Status.CANONICALIZED
    second = canonicalize(first.value, c)
    assert second.value == first.value
    assert replay(first, c) == first
    assert replay(first, c).canonical_bytes() == first.canonical_bytes()


@settings(derandomize=True, max_examples=50)
@given(_historical_inputs)
def test_historical_axis_idempotent_replay(value: str) -> None:
    c = Country(historical_names=True)
    first = canonicalize(value, c)
    assert first.status == Status.CANONICALIZED
    second = canonicalize(first.value, c)
    assert second.value == first.value
    assert replay(first, c) == first
    assert replay(first, c).canonical_bytes() == first.canonical_bytes()
