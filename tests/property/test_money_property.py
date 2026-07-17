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
# Currencies that use a COMMA as the decimal separator and a DOT as the
# thousands separator (Q1=A). All others use the dot-decimal convention.
_comma_decimal = frozenset(
    {
        "EUR",
        "DKK",
        "NOK",
        "SEK",
        "CHF",
        "BRL",
        "RUB",
        "TRY",
        "PLN",
        "HUF",
        "CZK",
        "RON",
        "ILS",
        "ISK",
    }
)


def _format_amount(currency: str, whole: str, frac: str) -> str:
    """Format a whole/fraction pair using the currency's separator convention.

    For comma-decimal currencies the decimal separator is a comma and the
    thousands separator is a dot (groups of 3). For dot-decimal currencies the
    roles are reversed. This keeps the generated input unambiguous so the
    canonicalizer accepts it (mandate: never guess an ambiguous separator).
    """
    if currency in _comma_decimal:
        thousands_sep, decimal_sep = ".", ","
    else:
        thousands_sep, decimal_sep = ",", "."
    grouped = (
        thousands_sep.join([whole[max(0, i - 3) : i] for i in range(len(whole), 0, -3)][::-1])
        if whole
        else "0"
    )
    return f"{grouped}{decimal_sep}{frac}" if frac else grouped


@st.composite
def _amounts(draw: st.DrawFn) -> tuple[str, str]:
    """Generate a (currency, amount) pair with a currency-appropriate amount."""
    currency = draw(_currencies)
    whole = draw(st.integers(min_value=0, max_value=10**9)).__str__()
    frac = draw(st.integers(min_value=0, max_value=10**4)).__str__()
    amount = _format_amount(currency, whole, frac)
    return currency, amount


@pytest.mark.property
@settings(derandomize=True)
@given(pair=_amounts())
def test_determinism(pair: tuple[str, str]) -> None:
    currency, amount = pair
    contract = Money(currency=currency)
    r1 = canonicalize(amount, contract)
    r2 = canonicalize(amount, contract)
    assert r1.status == r2.status
    assert r1.value == r2.value
    assert r1.evidence == r2.evidence


@pytest.mark.property
@settings(derandomize=True)
@given(pair=_amounts())
def test_replay_byte_equal(pair: tuple[str, str]) -> None:
    currency, amount = pair
    contract = Money(currency=currency)
    artifact = canonicalize(amount, contract)
    if artifact.status is not Status.CANONICALIZED:
        return
    replayed = replay(artifact, contract)
    assert replayed == artifact
    assert replayed.canonical_bytes() == artifact.canonical_bytes()


@pytest.mark.property
@settings(derandomize=True)
@given(pair=_amounts())
def test_canonical_form_shape(pair: tuple[str, str]) -> None:
    currency, amount = pair
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
@given(pair=_amounts())
def test_identity_stable(pair: tuple[str, str]) -> None:
    currency, amount = pair
    contract = Money(currency=currency)
    r1 = canonicalize(amount, contract)
    r2 = canonicalize(amount, contract)
    # Identity: canonicalize only rewrites; same known input -> same output.
    assert r1.value == r2.value
