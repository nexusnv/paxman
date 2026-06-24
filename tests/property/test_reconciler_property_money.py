"""Property tests: MONEY arithmetic properties (D5.15).

Tests algebraic and structural invariants of the monetary arithmetic
functions in ``paxman.reconciler.money`` using Hypothesis.

Properties tested:
  1. add_money commutativity:  a + b == b + a  (same currency/precision)
  2. add_money associativity:  (a + b) + c == a + (b + c)  (same currency/precision)
  3. subtract_money inverse:   (a + b) - b == a  (same currency/precision)
  4. multiply_money distributes:  a * (f1 * f2) == (a * f1) * f2  (integer factors)
  5. resolve_money_candidates preserves total  (same currency/precision)
  6. Decimal precision preserved (never float)
  7. quantize with banker's rounding (ROUND_HALF_EVEN)
  8. cross-currency ALLOW_FX:  convert + add == direct add with fx_rate
"""

from __future__ import annotations

import decimal

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from paxman.budget import CurrencyPolicy
from paxman.contract.canonical import MoneyValue
from paxman.reconciler.money import (
    add_money,
    convert_currency,
    multiply_money,
    resolve_money_candidates,
    subtract_money,
)

pytestmark = [pytest.mark.property]

# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Common ISO-4217 currency codes
_CURRENCIES = st.sampled_from(["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "MXN"])


@st.composite
def amounts(
    draw: st.DrawFn,
    *,
    min_val: str = "-10000",
    max_val: str = "10000",
    places: int = 2,
) -> decimal.Decimal:
    """Generate a Decimal amount with fixed *places* decimal digits.

    Values are constructed via ``st.decimals(places=…)`` so they never
    carry unexpected trailing digits — essential for exact quantize
    comparisons.
    """
    return draw(
        st.decimals(
            min_value=decimal.Decimal(min_val),
            max_value=decimal.Decimal(max_val),
            places=places,
        )
    )


@st.composite
def money_value(draw: st.DrawFn) -> MoneyValue:
    """Generate a random MoneyValue (any currency, any precision)."""
    currency = draw(_CURRENCIES)
    precision = draw(st.sampled_from([0, 2, 3, None]))
    # When precision is None, places=2 is a fallback for the generator
    # (the actual Decimal will keep its full precision since _quantize
    # is a no-op for None-precision values).
    p = precision if precision is not None else 2
    amt = draw(amounts(places=p))
    return MoneyValue(amount=amt, currency=currency, precision=precision)


@st.composite
def same_currency_pair(draw: st.DrawFn) -> tuple[MoneyValue, MoneyValue]:
    """Generate two MoneyValues with the same currency and precision.

    Both ``a`` and ``b`` carry Decimals already quantized to
    *precision* decimal places, so ``add_money`` / ``subtract_money``
    are exact (no intermediate rounding).
    """
    currency = draw(_CURRENCIES)
    precision = draw(st.sampled_from([0, 2, 3]))
    a = MoneyValue(
        amount=draw(amounts(places=precision)),
        currency=currency,
        precision=precision,
    )
    b = MoneyValue(
        amount=draw(amounts(places=precision)),
        currency=currency,
        precision=precision,
    )
    return a, b


@st.composite
def same_currency_triple(draw: st.DrawFn) -> tuple[MoneyValue, MoneyValue, MoneyValue]:
    """Generate three MoneyValues with identical currency and precision."""
    currency = draw(_CURRENCIES)
    precision = draw(st.sampled_from([0, 2, 3]))
    a = MoneyValue(
        amount=draw(amounts(places=precision)),
        currency=currency,
        precision=precision,
    )
    b = MoneyValue(
        amount=draw(amounts(places=precision)),
        currency=currency,
        precision=precision,
    )
    c = MoneyValue(
        amount=draw(amounts(places=precision)),
        currency=currency,
        precision=precision,
    )
    return a, b, c


@st.composite
def same_currency_list(
    draw: st.DrawFn, min_size: int = 1, max_size: int = 5
) -> tuple[MoneyValue, ...]:
    """Generate a tuple of same-currency same-precision MoneyValues."""
    currency = draw(_CURRENCIES)
    precision = draw(st.sampled_from([0, 2, 3]))
    n = draw(st.integers(min_value=min_size, max_value=max_size))
    return tuple(
        MoneyValue(
            amount=draw(amounts(places=precision)),
            currency=currency,
            precision=precision,
        )
        for _ in range(n)
    )


@st.composite
def rounding_value(draw: st.DrawFn) -> MoneyValue:
    """Generate a MoneyValue whose amount needs rounding at its precision.

    The amount is generated with *(precision + 1)* decimal places so
    that ``_quantize`` must apply ``ROUND_HALF_EVEN``.
    """
    precision = draw(st.sampled_from([0, 1, 2, 3]))
    currency = draw(_CURRENCIES)
    extra_places = precision + 1
    amt = draw(
        st.decimals(
            min_value=decimal.Decimal("-1000"),
            max_value=decimal.Decimal("1000"),
            places=extra_places,
        )
    )
    return MoneyValue(amount=amt, currency=currency, precision=precision)


# ---------------------------------------------------------------------------
# Property 1: add_money commutativity
# ---------------------------------------------------------------------------


@settings(max_examples=100, derandomize=True)
@given(pair=same_currency_pair())
def test_add_money_commutativity(pair: tuple[MoneyValue, MoneyValue]) -> None:
    """add_money(a, b) == add_money(b, a) for same-currency values."""
    a, b = pair
    left = add_money(a, b)
    right = add_money(b, a)
    assert left == right, f"a={a}, b={b}, left={left}, right={right}"


# ---------------------------------------------------------------------------
# Property 2: add_money associativity
# ---------------------------------------------------------------------------


@settings(max_examples=100, derandomize=True)
@given(triple=same_currency_triple())
def test_add_money_associativity(
    triple: tuple[MoneyValue, MoneyValue, MoneyValue],
) -> None:
    """(a + b) + c == a + (b + c) for same-currency same-precision values.

    Because operands share currency and precision, the sum is exact
    and Decimal arithmetic is associative.
    """
    a, b, c = triple
    left = add_money(add_money(a, b), c)
    right = add_money(a, add_money(b, c))
    assert left == right, f"a={a}, b={b}, c={c}, left={left}, right={right}"


# ---------------------------------------------------------------------------
# Property 3: subtract_money inverse
# ---------------------------------------------------------------------------


@settings(max_examples=100, derandomize=True)
@given(pair=same_currency_pair())
def test_subtract_money_inverse(pair: tuple[MoneyValue, MoneyValue]) -> None:
    """subtract_money(add_money(a, b), b) == a for same-currency values.

    Because both operands share the same precision and carry
    already-quantized Decimals, the sum-then-difference round-trip
    is exact.
    """
    a, b = pair
    added = add_money(a, b)
    result = subtract_money(added, b)
    assert result.amount == a.amount, (
        f"expected {a.amount}, got {result.amount}, a={a}, b={b}, added={added}"
    )
    assert result.currency == a.currency


# ---------------------------------------------------------------------------
# Property 4: multiply_money distributes over factor composition
# ---------------------------------------------------------------------------


@settings(max_examples=100, derandomize=True)
@given(mv=money_value())
def test_multiply_money_distributes(mv: MoneyValue) -> None:
    """multiply_money(a, f1 * f2) == multiply_money(multiply_money(a, f1), f2).

    Integer factors are used to guarantee exact Decimal arithmetic
    through the double-quantize chain.
    """
    f1 = decimal.Decimal("2")
    f2 = decimal.Decimal("3")
    combined = multiply_money(mv, f1 * f2)
    chained = multiply_money(multiply_money(mv, f1), f2)
    assert combined == chained, f"combined={combined}, chained={chained}, mv={mv}, f1={f1}, f2={f2}"


# ---------------------------------------------------------------------------
# Property 5: resolve_money_candidates preserves total (same currency)
# ---------------------------------------------------------------------------


@settings(max_examples=100, derandomize=True)
@given(values=same_currency_list(min_size=1, max_size=5))
def test_resolve_money_candidates_preserves_total(
    values: tuple[MoneyValue, ...],
) -> None:
    """For same-currency same-precision candidates, the resolved amount
    equals the arithmetic sum of all individual amounts.
    """
    result = resolve_money_candidates(values)
    assert result is not None, "resolve_money_candidates returned None for non-empty input"
    expected_total = sum(v.amount for v in values)
    assert result.amount == expected_total, (
        f"expected {expected_total}, got {result.amount}, values={values}"
    )
    assert result.currency == values[0].currency


# ---------------------------------------------------------------------------
# Property 6: Decimal precision preserved (never float)
# ---------------------------------------------------------------------------


@settings(max_examples=100, derandomize=True)
@given(pair=same_currency_pair())
def test_decimal_precision_preserved(pair: tuple[MoneyValue, MoneyValue]) -> None:
    """All MONEY operations return ``decimal.Decimal`` amounts — never float."""
    a, b = pair

    add_r = add_money(a, b)
    assert isinstance(add_r.amount, decimal.Decimal)

    sub_r = subtract_money(a, b)
    assert isinstance(sub_r.amount, decimal.Decimal)

    mul_r = multiply_money(a, decimal.Decimal("2"))
    assert isinstance(mul_r.amount, decimal.Decimal)

    converted = convert_currency(a, "EUR", decimal.Decimal("1.25"))
    assert isinstance(converted.amount, decimal.Decimal)

    resolved = resolve_money_candidates((a, b))
    assert resolved is None or isinstance(resolved.amount, decimal.Decimal)


# ---------------------------------------------------------------------------
# Property 7: quantize uses banker's rounding (ROUND_HALF_EVEN)
# ---------------------------------------------------------------------------


@settings(max_examples=100, derandomize=True)
@given(mv=rounding_value())
def test_quantize_bankers_rounding(mv: MoneyValue) -> None:
    """The quantize step after arithmetic uses ``ROUND_HALF_EVEN``.

    We force a quantize by adding a zero of the same currency/precision,
    then compare the result against ``ROUND_HALF_EVEN`` applied directly
    to the amount.
    """
    assume(mv.precision is not None)

    zero = MoneyValue(
        amount=decimal.Decimal("0"),
        currency=mv.currency,
        precision=mv.precision,
    )
    # Trigger _quantize through a same-currency add.
    result = add_money(mv, zero)

    # Expected: run the raw amount through explicit ROUND_HALF_EVEN.
    quant_unit = decimal.Decimal("1").scaleb(-mv.precision)
    expected = mv.amount.quantize(quant_unit, rounding=decimal.ROUND_HALF_EVEN)
    assert result.amount == expected, (
        f"amount={mv.amount}, precision={mv.precision}, got={result.amount}, expected={expected}"
    )


# ---------------------------------------------------------------------------
# Property 8: cross-currency ALLOW_FX — convert + add
# ---------------------------------------------------------------------------


@settings(max_examples=100, derandomize=True)
@given(mv=money_value())
def test_cross_currency_allow_fx(mv: MoneyValue) -> None:
    """Cross-currency add via ALLOW_FX produces the same result as
    an explicit ``convert_currency`` followed by same-currency add.

    Both paths should end up with: ``target_amount = mv.amount * fx_rate``
    quantized to *mv.precision*.
    """
    target_currency = _pick_different_currency(mv.currency)
    fx_rate = decimal.Decimal("1.25")  # fixed deterministic rate

    # Path 1: convert then same-currency add.
    converted = convert_currency(mv, target_currency, fx_rate)
    zero_in_target = MoneyValue(
        amount=decimal.Decimal("0"),
        currency=target_currency,
        precision=mv.precision,
    )
    via_convert = add_money(converted, zero_in_target)

    # Path 2: direct cross-currency add via ALLOW_FX.
    direct = add_money(
        zero_in_target,
        mv,
        policy=CurrencyPolicy.ALLOW_FX,
        fx_rate=fx_rate,
    )

    assert via_convert.amount == direct.amount, (
        f"via_convert={via_convert.amount}, direct={direct.amount}, "
        f"mv={mv}, rate={fx_rate}, target={target_currency}"
    )
    assert via_convert.currency == direct.currency == target_currency


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pick_different_currency(current: str) -> str:
    """Return an ISO-4217 code different from *current*."""
    others = [c for c in ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "MXN"] if c != current]
    # Deterministic choice (alphabetically first different currency).
    return sorted(others)[0]
