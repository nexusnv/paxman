"""MONEY arithmetic and CurrencyPolicy enforcement for the Reconciler.

First-class per `ADR-0004`. This module is the **only** module in
``paxman.reconciler`` (and the only place in paxman.normalization
beyond the contract layer) that imports :mod:`decimal` and performs
monetary arithmetic.

Rounding and precision
----------------------

- **Rounding:** :data:`decimal.ROUND_HALF_EVEN` (banker's rounding).
  This is the V1 default per the Sprint 5 prerequisite.
- **Precision:** Python's default Decimal context (28 significant
  digits). Adjusting this is a per-call concern via
  :func:`decimal.localcontext`.

CurrencyPolicy semantics
------------------------

- **STRICT_MATCH:** Cross-currency candidates are rejected with
  :class:`CurrencyMismatchError`. Same-currency candidates are
  combined as-is.
- **ALLOW_FX:** Cross-currency candidates are converted using an
  explicit ``fx_rate`` (source → target). The ``fx_rate`` MUST be
  provided as a :class:`decimal.Decimal` (floats are rejected).
  Without ``fx_rate``, raises :class:`MissingFxRateError`.
- **REJECT_WITHOUT_RATE:** Cross-currency candidates are rejected
  with :class:`MissingFxRateError` when no ``fx_rate`` is provided.
  Same behavior as ALLOW_FX when ``fx_rate`` IS provided.

All arithmetic operations return a NEW ``MoneyValue`` — they never
mutate their inputs. ``MoneyValue`` is frozen, so this is also
enforced structurally.
"""

from __future__ import annotations

import decimal
import typing

import attrs

from paxman.budget import CurrencyPolicy
from paxman.contract.canonical import MoneyValue
from paxman.errors import ReconciliationError

__all__ = [
    "CurrencyMismatchError",
    "InvalidFxRateError",
    "MissingFxRateError",
    "add_money",
    "compare_money",
    "convert_currency",
    "multiply_money",
    "resolve_money_candidates",
    "subtract_money",
]


#: Rounding mode for all monetary arithmetic in this module.
#: Banker's rounding (``ROUND_HALF_EVEN``) is the V1 default per
#: the Sprint 5 prerequisite.
_ROUNDING: typing.Final[str] = decimal.ROUND_HALF_EVEN


# ---------------------------------------------------------------------------
# Errors (specific to MONEY)
# ---------------------------------------------------------------------------


@attrs.frozen(slots=True)
class CurrencyMismatchError(ReconciliationError):
    """Raised when CurrencyPolicy.STRICT_MATCH rejects a cross-currency op.

    Carries the two currency codes that were involved in the offending
    operation, in addition to the standard Paxman error context.

    Attributes:
        message: Human-readable description.
        error_code: Always ``"CURRENCY_MISMATCH"``.
        context: Standard structured details.
        currency_a: The first currency code (e.g., ``"USD"``).
        currency_b: The second currency code (e.g., ``"EUR"``).
    """

    currency_a: str = "?"
    currency_b: str = "?"

    def __attrs_post_init__(self) -> None:
        # Standard PaxmanError fields first.
        object.__setattr__(self, "error_code", "CURRENCY_MISMATCH")
        if not isinstance(self.currency_a, str):
            raise TypeError(f"currency_a must be a str, got {type(self.currency_a).__name__}")
        if not isinstance(self.currency_b, str):
            raise TypeError(f"currency_b must be a str, got {type(self.currency_b).__name__}")
        if not self.message:
            object.__setattr__(
                self,
                "message",
                f"cross-currency operation rejected by STRICT_MATCH: "
                f"{self.currency_a} vs {self.currency_b}",
            )
        # Ensure context has structured fields for logging.
        ctx = dict(self.context)
        ctx.setdefault("currency_a", self.currency_a)
        ctx.setdefault("currency_b", self.currency_b)
        object.__setattr__(self, "context", ctx)


@attrs.frozen(slots=True)
class MissingFxRateError(ReconciliationError):
    """Raised when CurrencyPolicy requires an fx_rate but none is provided.

    Raised by ALLOW_FX (no fx_rate) and REJECT_WITHOUT_RATE (no fx_rate).
    """

    def __attrs_post_init__(self) -> None:
        object.__setattr__(self, "error_code", "MISSING_FX_RATE")
        if not self.message:
            object.__setattr__(
                self,
                "message",
                "cross-currency operation requires an explicit fx_rate",
            )


@attrs.frozen(slots=True)
class InvalidFxRateError(ReconciliationError):
    """Raised when an fx_rate is malformed (not Decimal, zero, or negative)."""

    def __attrs_post_init__(self) -> None:
        object.__setattr__(self, "error_code", "INVALID_FX_RATE")
        if not self.message:
            object.__setattr__(
                self,
                "message",
                "fx_rate must be a positive decimal.Decimal",
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@typing.overload
def _validate_fx_rate(
    fx_rate: object,
    *,
    allow_none: typing.Literal[True],
) -> decimal.Decimal | None: ...


@typing.overload
def _validate_fx_rate(
    fx_rate: object,
    *,
    allow_none: typing.Literal[False],
) -> decimal.Decimal: ...


def _validate_fx_rate(
    fx_rate: object,
    *,
    allow_none: bool,
) -> decimal.Decimal | None:
    """Validate and return an fx_rate as a Decimal.

    When ``allow_none`` is ``False`` the return type is guaranteed to be
    a :class:`decimal.Decimal` (the helper raises instead of returning
    ``None``). The :func:`overload` signatures make that narrowing
    visible to type-checkers.

    Args:
        fx_rate: The value to validate.
        allow_none: If ``True``, ``None`` is accepted and returned as ``None``.

    Returns:
        The validated Decimal, or ``None`` if ``allow_none=True`` and
        ``fx_rate`` is ``None``.

    Raises:
        MissingFxRateError: If ``allow_none=False`` and ``fx_rate`` is ``None``.
        InvalidFxRateError: If ``fx_rate`` is not a Decimal, or is <= 0.
    """
    if fx_rate is None:
        if allow_none:
            return None
        raise MissingFxRateError(
            "cross-currency operation requires an explicit fx_rate",
            context={},
        )
    # STRICT type check: bool is a subclass of int, Decimal is NOT.
    if isinstance(fx_rate, bool) or not isinstance(fx_rate, decimal.Decimal):
        raise InvalidFxRateError(
            f"fx_rate must be a decimal.Decimal, got {type(fx_rate).__name__}",
            context={},
        )
    if fx_rate <= decimal.Decimal("0"):
        raise InvalidFxRateError(
            f"fx_rate must be positive, got {fx_rate}",
            context={"fx_rate": str(fx_rate)},
        )
    return fx_rate


def _quantize(mv: MoneyValue) -> MoneyValue:
    """Quantize a MoneyValue to its precision using banker's rounding.

    If ``precision`` is ``None``, returns the value unchanged.
    """
    if mv.precision is None:
        return mv
    quant = decimal.Decimal("1").scaleb(-mv.precision)  # 10^-precision
    new_amount = mv.amount.quantize(quant, rounding=decimal.ROUND_HALF_EVEN)
    return MoneyValue(amount=new_amount, currency=mv.currency, precision=mv.precision)


# ---------------------------------------------------------------------------
# Arithmetic
# ---------------------------------------------------------------------------


def add_money(
    a: MoneyValue,
    b: MoneyValue,
    *,
    policy: CurrencyPolicy = CurrencyPolicy.STRICT_MATCH,
    fx_rate: decimal.Decimal | None = None,
) -> MoneyValue:
    """Add two MoneyValues respecting CurrencyPolicy.

    Args:
        a: First operand. The result is in ``a``'s currency.
        b: Second operand. Converted to ``a``'s currency if ALLOW_FX.
        policy: CurrencyPolicy to enforce. Defaults to STRICT_MATCH.
        fx_rate: Explicit FX rate (b → a). Required for ALLOW_FX across
            different currencies. Must be a positive Decimal.

    Returns:
        A new MoneyValue in ``a``'s currency with the sum.

    Raises:
        TypeError: If inputs are not MoneyValue.
        CurrencyMismatchError: STRICT_MATCH and currencies differ.
        MissingFxRateError: ALLOW_FX or REJECT_WITHOUT_RATE without fx_rate.
        InvalidFxRateError: fx_rate is not a positive Decimal.
    """
    if not isinstance(a, MoneyValue):
        raise TypeError(f"a must be a MoneyValue, got {type(a).__name__}")
    if not isinstance(b, MoneyValue):
        raise TypeError(f"b must be a MoneyValue, got {type(b).__name__}")
    if a.currency == b.currency:
        new_amount = a.amount + b.amount
        return _quantize(MoneyValue(amount=new_amount, currency=a.currency, precision=a.precision))
    # Cross-currency.
    if policy is CurrencyPolicy.STRICT_MATCH:
        raise CurrencyMismatchError(
            f"cross-currency add rejected by STRICT_MATCH: {a.currency} + {b.currency}",
            context={"a_currency": a.currency, "b_currency": b.currency},
            currency_a=a.currency,
            currency_b=b.currency,
        )
    # ALLOW_FX or REJECT_WITHOUT_RATE: require fx_rate.
    rate = _validate_fx_rate(fx_rate, allow_none=False)
    converted_b_amount = b.amount * rate
    new_amount = a.amount + converted_b_amount
    return _quantize(MoneyValue(amount=new_amount, currency=a.currency, precision=a.precision))


def subtract_money(
    a: MoneyValue,
    b: MoneyValue,
    *,
    policy: CurrencyPolicy = CurrencyPolicy.STRICT_MATCH,
    fx_rate: decimal.Decimal | None = None,
) -> MoneyValue:
    """Subtract b from a respecting CurrencyPolicy.

    Same rules as :func:`add_money`. The result is in ``a``'s currency.

    Args:
        a: First operand (minuend). The result is in ``a``'s currency.
        b: Second operand (subtrahend).
        policy: CurrencyPolicy to enforce. Defaults to STRICT_MATCH.
        fx_rate: Explicit FX rate (b → a). Required for ALLOW_FX across
            different currencies.

    Returns:
        A new MoneyValue in ``a``'s currency with the difference.

    Raises:
        TypeError: If inputs are not MoneyValue.
        CurrencyMismatchError: STRICT_MATCH and currencies differ.
        MissingFxRateError: ALLOW_FX or REJECT_WITHOUT_RATE without fx_rate.
        InvalidFxRateError: fx_rate is not a positive Decimal.
    """
    if not isinstance(a, MoneyValue):
        raise TypeError(f"a must be a MoneyValue, got {type(a).__name__}")
    if not isinstance(b, MoneyValue):
        raise TypeError(f"b must be a MoneyValue, got {type(b).__name__}")
    if a.currency == b.currency:
        new_amount = a.amount - b.amount
        return _quantize(MoneyValue(amount=new_amount, currency=a.currency, precision=a.precision))
    if policy is CurrencyPolicy.STRICT_MATCH:
        raise CurrencyMismatchError(
            f"cross-currency subtract rejected by STRICT_MATCH: {a.currency} - {b.currency}",
            context={"a_currency": a.currency, "b_currency": b.currency},
            currency_a=a.currency,
            currency_b=b.currency,
        )
    rate = _validate_fx_rate(fx_rate, allow_none=False)
    converted_b_amount = b.amount * rate
    new_amount = a.amount - converted_b_amount
    return _quantize(MoneyValue(amount=new_amount, currency=a.currency, precision=a.precision))


def multiply_money(
    m: MoneyValue,
    factor: decimal.Decimal,
) -> MoneyValue:
    """Multiply a MoneyValue by a Decimal factor.

    No currency policy is needed — multiplication does not combine
    different currencies. The result is in ``m``'s currency.

    Args:
        m: The money value.
        factor: Must be a :class:`decimal.Decimal`. Floats are rejected.

    Returns:
        A new MoneyValue with ``m.amount * factor``, same currency.

    Raises:
        TypeError: If ``m`` is not a MoneyValue, or ``factor`` is not a Decimal.

    Examples:
        >>> from decimal import Decimal
        >>> usd = MoneyValue(Decimal("10.00"), "USD")
        >>> multiply_money(usd, Decimal("3"))
        MoneyValue(amount=Decimal('30.00'), currency='USD', precision=2)
    """
    if not isinstance(m, MoneyValue):
        raise TypeError(f"m must be a MoneyValue, got {type(m).__name__}")
    if isinstance(factor, bool) or not isinstance(factor, decimal.Decimal):
        raise TypeError(
            f"factor must be a decimal.Decimal, got {type(factor).__name__}: {factor!r}"
        )
    new_amount = m.amount * factor
    return _quantize(MoneyValue(amount=new_amount, currency=m.currency, precision=m.precision))


def compare_money(
    a: MoneyValue,
    b: MoneyValue,
    *,
    policy: CurrencyPolicy = CurrencyPolicy.STRICT_MATCH,
    fx_rate: decimal.Decimal | None = None,
) -> int:
    """Compare two MoneyValues. Returns -1, 0, or 1.

    Same currency policy enforcement as :func:`add_money`. Returns:

    - ``-1`` if a < b
    - ``0`` if a == b
    - ``1`` if a > b

    For cross-currency comparison: ``a`` is the base; ``b`` is
    converted to ``a``'s currency using ``fx_rate`` (when allowed),
    then compared.

    Args:
        a: First operand.
        b: Second operand.
        policy: CurrencyPolicy to enforce.
        fx_rate: Explicit FX rate (b → a). Required for ALLOW_FX.

    Returns:
        ``-1``, ``0``, or ``1``.

    Raises:
        TypeError: If inputs are not MoneyValue.
        CurrencyMismatchError: STRICT_MATCH and currencies differ.
        MissingFxRateError: ALLOW_FX or REJECT_WITHOUT_RATE without fx_rate.
        InvalidFxRateError: fx_rate is not a positive Decimal.
    """
    if not isinstance(a, MoneyValue):
        raise TypeError(f"a must be a MoneyValue, got {type(a).__name__}")
    if not isinstance(b, MoneyValue):
        raise TypeError(f"b must be a MoneyValue, got {type(b).__name__}")
    if a.currency == b.currency:
        if a.amount < b.amount:
            return -1
        if a.amount > b.amount:
            return 1
        return 0
    if policy is CurrencyPolicy.STRICT_MATCH:
        raise CurrencyMismatchError(
            f"cross-currency compare rejected by STRICT_MATCH: {a.currency} vs {b.currency}",
            context={"a_currency": a.currency, "b_currency": b.currency},
            currency_a=a.currency,
            currency_b=b.currency,
        )
    rate = _validate_fx_rate(fx_rate, allow_none=False)
    converted_b = b.amount * rate
    if a.amount < converted_b:
        return -1
    if a.amount > converted_b:
        return 1
    return 0


def convert_currency(
    m: MoneyValue,
    target_currency: str,
    fx_rate: decimal.Decimal,
) -> MoneyValue:
    """Convert a MoneyValue to a different currency using an explicit FX rate.

    Args:
        m: The money value to convert.
        target_currency: ISO-4217 target currency code (3 uppercase letters).
        fx_rate: The exchange rate (m.currency → target_currency). Must
            be a positive Decimal.

    Returns:
        A new MoneyValue in ``target_currency`` with the converted amount.

    Raises:
        TypeError: If ``m`` is not a MoneyValue.
        ValueError: If ``target_currency`` is not a valid ISO-4217 code.
        InvalidFxRateError: If ``fx_rate`` is not a positive Decimal.
    """
    if not isinstance(m, MoneyValue):
        raise TypeError(f"m must be a MoneyValue, got {type(m).__name__}")
    if not isinstance(target_currency, str) or len(target_currency) != 3:
        raise ValueError(
            f"target_currency must be a 3-letter ISO-4217 code, got {target_currency!r}"
        )
    if (
        not target_currency.isascii()
        or not target_currency.isupper()
        or not target_currency.isalpha()
    ):
        raise ValueError(
            f"target_currency must be 3 uppercase ASCII letters, got {target_currency!r}"
        )
    if m.currency == target_currency:
        return m
    rate = _validate_fx_rate(fx_rate, allow_none=False)
    new_amount = m.amount * rate
    return _quantize(MoneyValue(amount=new_amount, currency=target_currency, precision=m.precision))


def resolve_money_candidates(
    candidates: tuple[MoneyValue, ...],
    *,
    policy: CurrencyPolicy = CurrencyPolicy.STRICT_MATCH,
    fx_rate: decimal.Decimal | None = None,
) -> MoneyValue | None:
    """Resolve multiple MONEY candidates into a single value.

    Applies CurrencyPolicy to determine compatibility:

    - STRICT_MATCH: only same-currency candidates are combined; if
      there are multiple currencies, the candidates are incompatible
      and this returns ``None``.
    - ALLOW_FX / REJECT_WITHOUT_RATE: all candidates are converted
      to the first candidate's currency using ``fx_rate``, then summed.

    Returns ``None`` if ``candidates`` is empty or if no compatible
    candidates can be combined.

    Args:
        candidates: Tuple of MoneyValue candidates. May be empty.
        policy: CurrencyPolicy to enforce.
        fx_rate: Explicit FX rate (b → a's currency). Required for
            ALLOW_FX / REJECT_WITHOUT_RATE in cross-currency cases.

    Returns:
        A single MoneyValue (the sum), or ``None`` if no candidates
        or no compatible combination.
    """
    if not candidates:
        return None
    # Validate types.
    for c in candidates:
        if not isinstance(c, MoneyValue):
            raise TypeError(f"all candidates must be MoneyValue, got {type(c).__name__}")
    # Fast path: all same currency.
    base = candidates[0]
    if all(c.currency == base.currency for c in candidates):
        total = base.amount
        for c in candidates[1:]:
            total = total + c.amount
        return _quantize(MoneyValue(amount=total, currency=base.currency, precision=base.precision))
    # Cross-currency path.
    if policy is CurrencyPolicy.STRICT_MATCH:
        return None
    rate = _validate_fx_rate(fx_rate, allow_none=False)
    total = base.amount
    for c in candidates[1:]:
        if c.currency != base.currency:
            total = total + (c.amount * rate)
        else:
            total = total + c.amount
    return _quantize(MoneyValue(amount=total, currency=base.currency, precision=base.precision))
