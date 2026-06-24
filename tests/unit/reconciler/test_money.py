"""Tests for paxman.reconciler.money — MONEY arithmetic and CurrencyPolicy enforcement."""

from __future__ import annotations

from decimal import Decimal

import pytest

from paxman.budget import CurrencyPolicy
from paxman.contract.canonical import MoneyValue
from paxman.errors import ReconciliationError
from paxman.reconciler.money import (
    CurrencyMismatchError,
    InvalidFxRateError,
    MissingFxRateError,
    add_money,
    compare_money,
    convert_currency,
    multiply_money,
    resolve_money_candidates,
    subtract_money,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USD = "USD"
EUR = "EUR"
JPY = "JPY"


def usd(amount: str, precision: int | None = 2) -> MoneyValue:
    return MoneyValue(amount=Decimal(amount), currency=USD, precision=precision)


def eur(amount: str, precision: int | None = 2) -> MoneyValue:
    return MoneyValue(amount=Decimal(amount), currency=EUR, precision=precision)


def jpy(amount: str, precision: int | None = 0) -> MoneyValue:
    return MoneyValue(amount=Decimal(amount), currency=JPY, precision=precision)


# ---------------------------------------------------------------------------
# Error types
# ---------------------------------------------------------------------------


class TestMoneyErrors:
    def test_currency_mismatch_error_is_reconciliation_error(self) -> None:
        err = CurrencyMismatchError(
            "USD vs EUR",
            context={},
            currency_a="USD",
            currency_b="EUR",
        )
        assert isinstance(err, ReconciliationError)
        assert err.error_code == "CURRENCY_MISMATCH"
        assert "USD" in str(err)
        assert "EUR" in str(err)

    def test_currency_mismatch_error_default_message(self) -> None:
        err = CurrencyMismatchError(
            "cross-currency violation",
            context={},
            currency_a="USD",
            currency_b="EUR",
        )
        assert err.message == "cross-currency violation"
        assert err.currency_a == "USD"
        assert err.currency_b == "EUR"
        assert err.error_code == "CURRENCY_MISMATCH"

    def test_currency_mismatch_error_explicit_message(self) -> None:
        err = CurrencyMismatchError(
            "custom message",
            context={},
            currency_a="USD",
            currency_b="EUR",
        )
        assert err.message == "custom message"

    def test_currency_mismatch_error_type_error_currency_a(self) -> None:
        with pytest.raises(TypeError, match="currency_a must be a str"):
            CurrencyMismatchError(
                "test",
                context={},
                currency_a=123,  # type: ignore[arg-type]
            )

    def test_currency_mismatch_error_type_error_currency_b(self) -> None:
        with pytest.raises(TypeError, match="currency_b must be a str"):
            CurrencyMismatchError(
                "test",
                context={},
                currency_b=456,  # type: ignore[arg-type]
            )

    def test_missing_fx_rate_error(self) -> None:
        err = MissingFxRateError("fx_rate required", context={})
        assert err.error_code == "MISSING_FX_RATE"
        assert isinstance(err, ReconciliationError)
        assert "fx_rate" in err.message

    def test_invalid_fx_rate_error(self) -> None:
        err = InvalidFxRateError("fx_rate must be positive Decimal", context={})
        assert err.error_code == "INVALID_FX_RATE"
        assert isinstance(err, ReconciliationError)
        assert "positive" in err.message


# ---------------------------------------------------------------------------
# add_money — type errors
# ---------------------------------------------------------------------------


class TestAddMoneyTypeErrors:
    def test_a_not_money_value(self) -> None:
        with pytest.raises(TypeError, match="a must be a MoneyValue"):
            add_money("not-money", usd("10.00"))  # type: ignore[arg-type]

    def test_b_not_money_value(self) -> None:
        with pytest.raises(TypeError, match="b must be a MoneyValue"):
            add_money(usd("10.00"), "not-money")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# add_money — same currency
# ---------------------------------------------------------------------------


class TestAddMoneySameCurrency:
    def test_add_two_values(self) -> None:
        result = add_money(usd("10.00"), usd("20.00"))
        assert result.amount == Decimal("30.00")
        assert result.currency == USD
        assert result.precision == 2

    def test_add_negative(self) -> None:
        result = add_money(usd("50.00"), usd("-20.00"))
        assert result.amount == Decimal("30.00")

    def test_add_zero(self) -> None:
        result = add_money(usd("10.00"), usd("0.00"))
        assert result.amount == Decimal("10.00")

    def test_add_with_no_precision(self) -> None:
        mv1 = MoneyValue(amount=Decimal("1000"), currency=JPY, precision=None)
        mv2 = MoneyValue(amount=Decimal("500"), currency=JPY, precision=None)
        result = add_money(mv1, mv2)
        assert result.amount == Decimal("1500")
        assert result.precision is None

    def test_add_keeps_precision_of_first_operand(self) -> None:
        result = add_money(usd("10.00", precision=2), usd("20.000", precision=3))
        # Result uses a.precision
        assert result.precision == 2

    def test_add_quantizes_result(self) -> None:
        # 1/3 * 3 should round to 1.00 with precision=2
        result = add_money(usd("0.334"), usd("0.666"))
        assert result.amount == Decimal("1.000")


# ---------------------------------------------------------------------------
# add_money — cross-currency
# ---------------------------------------------------------------------------


class TestAddMoneyCrossCurrency:
    def test_strict_match_raises(self) -> None:
        with pytest.raises(CurrencyMismatchError) as exc:
            add_money(usd("10.00"), eur("20.00"))
        assert exc.value.currency_a == USD
        assert exc.value.currency_b == EUR

    def test_allow_fx_with_rate(self) -> None:
        result = add_money(
            usd("10.00"),
            eur("10.00"),
            policy=CurrencyPolicy.ALLOW_FX,
            fx_rate=Decimal("1.10"),
        )
        # EUR 10.00 @ 1.10 = USD 11.00
        # Total: USD 10.00 + USD 11.00 = USD 21.00
        assert result.amount == Decimal("21.00")
        assert result.currency == USD

    def test_allow_fx_without_rate_raises(self) -> None:
        with pytest.raises(MissingFxRateError):
            add_money(
                usd("10.00"),
                eur("10.00"),
                policy=CurrencyPolicy.ALLOW_FX,
            )

    def test_reject_without_rate_without_rate_raises(self) -> None:
        with pytest.raises(MissingFxRateError):
            add_money(
                usd("10.00"),
                eur("10.00"),
                policy=CurrencyPolicy.REJECT_WITHOUT_RATE,
            )

    def test_reject_without_rate_with_rate_succeeds(self) -> None:
        result = add_money(
            usd("10.00"),
            eur("10.00"),
            policy=CurrencyPolicy.REJECT_WITHOUT_RATE,
            fx_rate=Decimal("0.90"),
        )
        # EUR 10 @ 0.90 = USD 9.00
        # Total: USD 10.00 + USD 9.00 = USD 19.00
        assert result.amount == Decimal("19.00")
        assert result.currency == USD

    def test_invalid_fx_rate_raises(self) -> None:
        with pytest.raises(InvalidFxRateError, match="must be positive"):
            add_money(
                usd("10.00"),
                eur("10.00"),
                policy=CurrencyPolicy.ALLOW_FX,
                fx_rate=Decimal("-1.0"),
            )

    def test_fx_rate_zero_raises(self) -> None:
        with pytest.raises(InvalidFxRateError, match="must be positive"):
            add_money(
                usd("10.00"),
                eur("10.00"),
                policy=CurrencyPolicy.ALLOW_FX,
                fx_rate=Decimal("0"),
            )

    def test_fx_rate_must_be_decimal(self) -> None:
        with pytest.raises(InvalidFxRateError, match=r"must be a decimal\.Decimal"):
            add_money(
                usd("10.00"),
                eur("10.00"),
                policy=CurrencyPolicy.ALLOW_FX,
                fx_rate=1.10,  # type: ignore[arg-type]
            )

    def test_fx_rate_bool_raises(self) -> None:
        with pytest.raises(InvalidFxRateError, match=r"must be a decimal\.Decimal"):
            add_money(
                usd("10.00"),
                eur("10.00"),
                policy=CurrencyPolicy.ALLOW_FX,
                fx_rate=True,  # type: ignore[arg-type]
            )


# ---------------------------------------------------------------------------
# subtract_money
# ---------------------------------------------------------------------------


class TestSubtractMoney:
    def test_same_currency(self) -> None:
        result = subtract_money(usd("50.00"), usd("20.00"))
        assert result.amount == Decimal("30.00")
        assert result.currency == USD

    def test_same_currency_negative_result(self) -> None:
        result = subtract_money(usd("10.00"), usd("20.00"))
        assert result.amount == Decimal("-10.00")

    def test_cross_currency_strict_match_raises(self) -> None:
        with pytest.raises(CurrencyMismatchError):
            subtract_money(usd("50.00"), eur("20.00"))

    def test_allow_fx_with_rate(self) -> None:
        result = subtract_money(
            usd("50.00"),
            eur("10.00"),
            policy=CurrencyPolicy.ALLOW_FX,
            fx_rate=Decimal("1.20"),
        )
        # EUR 10.00 @ 1.20 = USD 12.00
        # USD 50.00 - USD 12.00 = USD 38.00
        assert result.amount == Decimal("38.00")

    def test_type_error_a(self) -> None:
        with pytest.raises(TypeError, match="a must be a MoneyValue"):
            subtract_money("x", usd("10.00"))  # type: ignore[arg-type]

    def test_type_error_b(self) -> None:
        with pytest.raises(TypeError, match="b must be a MoneyValue"):
            subtract_money(usd("10.00"), "x")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# multiply_money
# ---------------------------------------------------------------------------


class TestMultiplyMoney:
    def test_multiply_by_decimal(self) -> None:
        result = multiply_money(usd("10.00"), Decimal("3"))
        assert result.amount == Decimal("30.00")
        assert result.currency == USD

    def test_multiply_by_fraction(self) -> None:
        result = multiply_money(usd("10.00"), Decimal("0.5"))
        assert result.amount == Decimal("5.00")

    def test_multiply_by_zero(self) -> None:
        result = multiply_money(usd("10.00"), Decimal("0"))
        assert result.amount == Decimal("0.00")

    def test_type_error_m_not_money(self) -> None:
        with pytest.raises(TypeError, match="m must be a MoneyValue"):
            multiply_money("not-money", Decimal("2"))  # type: ignore[arg-type]

    def test_type_error_factor_float(self) -> None:
        with pytest.raises(TypeError, match=r"factor must be a decimal\.Decimal"):
            multiply_money(usd("10.00"), 2.0)  # type: ignore[arg-type]

    def test_type_error_factor_int(self) -> None:
        with pytest.raises(TypeError, match=r"factor must be a decimal\.Decimal"):
            multiply_money(usd("10.00"), 2)  # type: ignore[arg-type]

    def test_type_error_factor_str(self) -> None:
        with pytest.raises(TypeError, match=r"factor must be a decimal\.Decimal"):
            multiply_money(usd("10.00"), "2")  # type: ignore[arg-type]

    def test_type_error_factor_bool(self) -> None:
        with pytest.raises(TypeError, match=r"factor must be a decimal\.Decimal"):
            multiply_money(usd("10.00"), True)  # type: ignore[arg-type]

    def test_quantizes_result(self) -> None:
        result = multiply_money(usd("10.00"), Decimal("0.333"))
        assert result.precision == 2

    def test_preserves_no_precision(self) -> None:
        mv = MoneyValue(amount=Decimal("100"), currency=JPY, precision=None)
        result = multiply_money(mv, Decimal("3"))
        assert result.precision is None
        assert result.amount == Decimal("300")

    def test_zero_precision(self) -> None:
        result = multiply_money(jpy("100"), Decimal("3"))
        assert result.amount == Decimal("300")
        assert result.precision == 0


# ---------------------------------------------------------------------------
# compare_money
# ---------------------------------------------------------------------------


class TestCompareMoney:
    def test_equal(self) -> None:
        assert compare_money(usd("10.00"), usd("10.00")) == 0

    def test_a_less_than_b(self) -> None:
        assert compare_money(usd("5.00"), usd("10.00")) == -1

    def test_a_greater_than_b(self) -> None:
        assert compare_money(usd("10.00"), usd("5.00")) == 1

    def test_cross_currency_strict_match_raises(self) -> None:
        with pytest.raises(CurrencyMismatchError):
            compare_money(usd("10.00"), eur("10.00"))

    def test_allow_fx(self) -> None:
        # EUR 10 @ 1.0 = USD 10, so equal
        result = compare_money(
            usd("10.00"),
            eur("10.00"),
            policy=CurrencyPolicy.ALLOW_FX,
            fx_rate=Decimal("1.00"),
        )
        assert result == 0

    def test_allow_fx_a_less(self) -> None:
        # EUR 10 @ 2.0 = USD 20, so USD 10 < USD 20
        result = compare_money(
            usd("10.00"),
            eur("10.00"),
            policy=CurrencyPolicy.ALLOW_FX,
            fx_rate=Decimal("2.00"),
        )
        assert result == -1

    def test_allow_fx_a_greater(self) -> None:
        # EUR 10 @ 0.5 = USD 5, so USD 10 > USD 5
        result = compare_money(
            usd("10.00"),
            eur("10.00"),
            policy=CurrencyPolicy.ALLOW_FX,
            fx_rate=Decimal("0.50"),
        )
        assert result == 1

    def test_type_error_a(self) -> None:
        with pytest.raises(TypeError, match="a must be a MoneyValue"):
            compare_money("x", usd("10.00"))  # type: ignore[arg-type]

    def test_type_error_b(self) -> None:
        with pytest.raises(TypeError, match="b must be a MoneyValue"):
            compare_money(usd("10.00"), "x")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# convert_currency
# ---------------------------------------------------------------------------


class TestConvertCurrency:
    def test_same_currency_returns_original(self) -> None:
        mv = usd("10.00")
        result = convert_currency(mv, USD, Decimal("1.0"))
        # Same currency: returns the original (not a copy)
        assert result is mv

    def test_different_currency(self) -> None:
        result = convert_currency(usd("10.00"), EUR, Decimal("0.85"))
        assert result.amount == Decimal("8.50")
        assert result.currency == EUR

    def test_type_error_m_not_money(self) -> None:
        with pytest.raises(TypeError, match="m must be a MoneyValue"):
            convert_currency("not-money", EUR, Decimal("1.0"))  # type: ignore[arg-type]

    def test_value_error_target_currency_not_string(self) -> None:
        with pytest.raises(ValueError, match="ISO-4217"):
            convert_currency(usd("10.00"), 123, Decimal("1.0"))  # type: ignore[arg-type]

    def test_value_error_target_currency_wrong_length(self) -> None:
        with pytest.raises(ValueError, match="ISO-4217"):
            convert_currency(usd("10.00"), "US", Decimal("1.0"))

    def test_value_error_target_currency_lowercase(self) -> None:
        with pytest.raises(ValueError, match="uppercase"):
            convert_currency(usd("10.00"), "eur", Decimal("1.0"))

    def test_value_error_target_currency_non_alpha(self) -> None:
        with pytest.raises(ValueError, match="uppercase"):
            convert_currency(usd("10.00"), "US1", Decimal("1.0"))

    def test_invalid_fx_rate(self) -> None:
        with pytest.raises(InvalidFxRateError):
            convert_currency(usd("10.00"), EUR, Decimal("0"))

    def test_fx_rate_negative(self) -> None:
        with pytest.raises(InvalidFxRateError):
            convert_currency(usd("10.00"), EUR, Decimal("-0.5"))

    def test_quantizes_result(self) -> None:
        mv = MoneyValue(amount=Decimal("10.123"), currency="USD", precision=2)
        result = convert_currency(mv, EUR, Decimal("0.85"))
        assert result.precision == 2


# ---------------------------------------------------------------------------
# resolve_money_candidates
# ---------------------------------------------------------------------------


class TestResolveMoneyCandidates:
    def test_empty_candidates_returns_none(self) -> None:
        result = resolve_money_candidates(())
        assert result is None

    def test_single_candidate(self) -> None:
        result = resolve_money_candidates((usd("10.00"),))
        assert result is not None
        assert result.amount == Decimal("10.00")

    def test_same_currency_sum(self) -> None:
        result = resolve_money_candidates((usd("10.00"), usd("20.00"), usd("30.00")))
        assert result is not None
        assert result.amount == Decimal("60.00")
        assert result.currency == USD

    def test_same_currency_all_none_precision(self) -> None:
        mv1 = MoneyValue(amount=Decimal("100"), currency=JPY, precision=None)
        mv2 = MoneyValue(amount=Decimal("200"), currency=JPY, precision=None)
        result = resolve_money_candidates((mv1, mv2))
        assert result is not None
        assert result.amount == Decimal("300")
        assert result.precision is None

    def test_cross_currency_strict_match_returns_none(self) -> None:
        result = resolve_money_candidates((usd("10.00"), eur("20.00")))
        assert result is None

    def test_cross_currency_allow_fx_with_rate(self) -> None:
        result = resolve_money_candidates(
            (usd("10.00"), eur("20.00"), usd("5.00")),
            policy=CurrencyPolicy.ALLOW_FX,
            fx_rate=Decimal("1.10"),
        )
        assert result is not None
        # USD 10.00 + (EUR 20.00 @ 1.10 = USD 22.00) + USD 5.00 = USD 37.00
        assert result.amount == Decimal("37.00")
        assert result.currency == USD

    def test_cross_currency_allow_fx_missing_rate_raises(self) -> None:
        with pytest.raises(MissingFxRateError):
            resolve_money_candidates(
                (usd("10.00"), eur("20.00")),
                policy=CurrencyPolicy.ALLOW_FX,
            )

    def test_cross_currency_reject_without_rate_raises(self) -> None:
        with pytest.raises(MissingFxRateError):
            resolve_money_candidates(
                (usd("10.00"), eur("20.00")),
                policy=CurrencyPolicy.REJECT_WITHOUT_RATE,
            )

    def test_type_error_non_money_value(self) -> None:
        with pytest.raises(TypeError, match="all candidates must be MoneyValue"):
            resolve_money_candidates((usd("10.00"), "not-money"))  # type: ignore[arg-type]

    def test_cross_currency_allow_fx_same_currency_mixed(self) -> None:
        """When some candidates share the base currency, they are not converted."""
        result = resolve_money_candidates(
            (usd("10.00"), eur("20.00"), usd("5.00")),
            policy=CurrencyPolicy.ALLOW_FX,
            fx_rate=Decimal("1.10"),
        )
        # USD 10 + EUR 20*1.10 + USD 5 = 10 + 22 + 5 = 37
        assert result is not None
        assert result.amount == Decimal("37.00")

    def test_cross_currency_quantizes(self) -> None:
        result = resolve_money_candidates(
            (usd("10.123"), eur("5.00")),
            policy=CurrencyPolicy.ALLOW_FX,
            fx_rate=Decimal("1.00"),
        )
        # EUR 5.00 @ 1.00 = USD 5.00
        # USD 10.123 + USD 5.00 = USD 15.123, quantized to precision=2
        assert result is not None
        assert result.amount == Decimal("15.12")  # ROUND_HALF_EVEN


# ---------------------------------------------------------------------------
# _quantize edge cases (tested through public functions)
# ---------------------------------------------------------------------------


class TestQuantize:
    def test_precision_none_returns_unchanged(self) -> None:
        """When precision is None, _quantize returns the value unchanged."""
        mv = MoneyValue(amount=Decimal("10.123"), currency=USD, precision=None)
        result = add_money(mv, MoneyValue(amount=Decimal("5.00"), currency=USD, precision=None))
        # No quantization since precision is None
        assert result.amount == Decimal("15.123")

    def test_precision_0_rounds_to_integer(self) -> None:
        result = add_money(
            MoneyValue(amount=Decimal("10.50"), currency=JPY, precision=0),
            MoneyValue(amount=Decimal("5.25"), currency=JPY, precision=0),
        )
        # 10.50 + 5.25 = 15.75, quantized to precision=0 -> 16 (ROUND_HALF_EVEN)
        assert result.amount == Decimal("16")

    def test_precision_3(self) -> None:
        result = add_money(
            MoneyValue(amount=Decimal("10.1234"), currency=USD, precision=3),
            MoneyValue(amount=Decimal("5.0000"), currency=USD, precision=3),
        )
        assert result.amount == Decimal("15.123")
