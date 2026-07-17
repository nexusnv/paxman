"""Tests for the money canonicalizer (core canonicalize path)."""

from __future__ import annotations

from paxman import Money, canonicalize
from paxman._capabilities.money.canonicalizer import MoneyCapability
from paxman._capabilities.money.contract import CanonicalMoneyContract


def _cap() -> MoneyCapability:
    return MoneyCapability()


def _contract(**kw: object) -> CanonicalMoneyContract:
    return Money(currency="MYR", **kw)  # type: ignore[arg-type]


def test_can_handle_true_for_money_contract() -> None:
    assert _cap().can_handle(_contract(), "RM 10.00") is True


def test_can_handle_false_for_other_contract() -> None:
    from paxman import IP

    assert _cap().can_handle(IP(), "RM 10.00") is False


def test_canonicalize_symbol_myr() -> None:
    res = _cap().canonicalize("RM 12.50", _contract())
    assert res.status.name == "CANONICALIZED"
    assert res.value == "MYR:12.50"
    rules = {e.rule for e in res.evidence}
    assert "currency_from_contract" in rules
    assert "canonical_form" in rules


def test_canonicalize_plain_amount() -> None:
    res = _cap().canonicalize("78.90", _contract())
    assert res.value == "MYR:78.90"


def test_canonicalize_negative_minus() -> None:
    res = _cap().canonicalize("-5.00", _contract())
    assert res.value == "MYR:-5.00"


def test_canonicalize_negative_parentheses() -> None:
    res = _cap().canonicalize("(5.00)", _contract())
    assert res.value == "MYR:-5.00"


def test_canonicalize_eur_comma_decimal() -> None:
    res = _cap().canonicalize("1.234,56", Money(currency="EUR"))
    assert res.value == "EUR:1234.56"


def test_canonicalize_usd_comma_thousands() -> None:
    res = _cap().canonicalize("USD 1,234.56", Money(currency="USD"))
    assert res.value == "USD:1234.56"


def test_canonicalize_scientific() -> None:
    res = _cap().canonicalize("1.25E+2", Money(currency="MYR"))
    assert res.value == "MYR:125"


def test_canonicalize_strips_spaces() -> None:
    res = _cap().canonicalize("  12.50  ", _contract())
    assert res.value == "MYR:12.50"


def test_canonicalize_rejects_unknown_symbol() -> None:
    res = _cap().canonicalize("€ 10.00", _contract())
    assert res.status.name == "INVALID"


def test_canonicalize_rejects_symbol_mismatch() -> None:
    res = _cap().canonicalize("RM 10.00", Money(currency="USD"))
    assert res.status.name == "INVALID"


def test_canonicalize_rejects_empty() -> None:
    res = _cap().canonicalize("   ", _contract())
    assert res.status.name == "INVALID"


def test_canonicalize_non_string_value() -> None:
    res = _cap().canonicalize(1234, _contract())  # type: ignore[arg-type]
    assert res.status.name == "INVALID"


def test_canonicalize_not_a_money_contract() -> None:
    res = _cap().canonicalize("RM 10.00", "not-a-contract")  # type: ignore[arg-type]
    assert res.status.name == "INVALID"


def test_canonicalize_via_public_api() -> None:
    res = canonicalize("RM 12.50", Money(currency="MYR"))
    assert res.status.name == "CANONICALIZED"
    assert res.value == "MYR:12.50"


def test_canonicalize_invalid_raises_no_exception_public_api() -> None:
    # Public API returns INVALID status, does not raise, for malformed input.
    res = canonicalize("€ 10.00", Money(currency="MYR"))
    assert res.status.name == "INVALID"
