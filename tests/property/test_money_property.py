"""Money-specific invariant property tests (mandate Laws 1, 2, 12).

Complements the generic engine property tests: every supported money input
canonicalizes deterministically, replays byte-equal, and yields a canonical
form whose amount is an exact decimal (never a float). Derandomized per
AGENTS.md (mandate Law 1 — no randomness).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from paxman import Money, canonicalize, replay
from paxman._core.status import Status

_currencies = st.sampled_from(["MYR", "USD", "EUR", "GBP", "JPY", "SGD"])
_whole = st.integers(min_value=0, max_value=10**9).map(str)
_decimal = st.tuples(
    st.integers(min_value=0, max_value=10**6),
    st.integers(min_value=0, max_value=10**4),
).map(lambda t: f"{t[0]}.{t[1]}")
_amounts = st.one_of(_whole, _decimal)


@pytest.mark.property
@settings(derandomize=True)
@given(currency=_currencies, amount=_amounts)
def test_determinism(currency: str, amount: str) -> None:
    contract = Money(currency=currency)
    r1 = canonicalize(amount, contract)
    r2 = canonicalize(amount, contract)
    assert r1.status == r2.status
    assert r1.value == r2.value
    assert r1.evidence == r2.evidence


@pytest.mark.property
@settings(derandomize=True)
@given(currency=_currencies, amount=_amounts)
def test_replay_byte_equal(currency: str, amount: str) -> None:
    contract = Money(currency=currency)
    artifact = canonicalize(amount, contract)
    if artifact.status is not Status.CANONICALIZED:
        return
    replayed = replay(artifact, contract)
    assert replayed == artifact
    assert replayed.canonical_bytes() == artifact.canonical_bytes()


@pytest.mark.property
@settings(derandomize=True)
@given(currency=_currencies, amount=_amounts)
def test_canonical_form_shape(currency: str, amount: str) -> None:
    contract = Money(currency=currency)
    artifact = canonicalize(amount, contract)
    assert artifact.status is Status.CANONICALIZED
    assert artifact.value is not None
    assert artifact.value.startswith(f"{currency}:")
    # The amount part is a valid Decimal (exact, never float / scientific).
    decimal_part = artifact.value.split(":", 1)[1]
    Decimal(decimal_part)  # does not raise


@pytest.mark.property
@settings(derandomize=True)
@given(currency=_currencies, amount=_amounts)
def test_identity_stable(currency: str, amount: str) -> None:
    contract = Money(currency=currency)
    r1 = canonicalize(amount, contract)
    r2 = canonicalize(amount, contract)
    # Identity: canonicalize only rewrites; same known input -> same output.
    assert r1.value == r2.value
