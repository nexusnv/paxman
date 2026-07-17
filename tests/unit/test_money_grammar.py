"""Tests for the money recognition grammar (input → structured parts)."""

from __future__ import annotations

import pytest

from paxman._capabilities.money.contract import Money
from paxman._capabilities.money.grammar import (
    parse_amount,
    recognize_money,
)
from paxman._errors import ContractError


def test_recognize_symbol_present() -> None:
    c = Money(currency="MYR")
    parts = recognize_money("RM 12.50", c)
    assert parts.currency == "MYR"
    assert parts.symbol == "RM"
    assert parts.amount == "12.50"


def test_recognize_code_present() -> None:
    c = Money(currency="USD")
    parts = recognize_money("USD 1,234.56", c)
    assert parts.currency == "USD"
    assert parts.code == "USD"
    assert parts.amount == "1,234.56"


def test_recognize_sign_minus() -> None:
    parts = recognize_money("-5.00", Money(currency="MYR"))
    assert parts.sign == "-"
    assert parts.amount == "5.00"


def test_recognize_sign_parentheses() -> None:
    parts = recognize_money("(5.00)", Money(currency="MYR"))
    assert parts.sign == "-"
    assert parts.amount == "5.00"


def test_recognize_no_symbol_no_code() -> None:
    parts = recognize_money("78.90", Money(currency="MYR"))
    assert parts.symbol is None
    assert parts.code is None
    assert parts.amount == "78.90"


def test_recognize_strip_spaces_true() -> None:
    parts = recognize_money("  12.50  ", Money(currency="MYR"))
    assert parts.amount == "12.50"


def test_recognize_strip_spaces_false() -> None:
    with pytest.raises(ContractError):
        recognize_money("  12.50  ", Money(currency="MYR", strip_spaces=False))


def test_recognize_disallow_symbol_rejected() -> None:
    with pytest.raises(ContractError):
        recognize_money("RM 12.50", Money(currency="MYR", allow_symbol=False))


def test_recognize_disallow_code_rejected() -> None:
    with pytest.raises(ContractError):
        recognize_money("USD 1.00", Money(currency="USD", allow_code=False))


def test_recognize_symbol_ok_when_code_disallowed() -> None:
    # Symbol is accepted even when codes are disallowed.
    parts = recognize_money("RM 10.00", Money(currency="MYR", allow_code=False))
    assert parts.symbol == "RM"
    assert parts.code is None
    assert parts.amount == "10.00"


def test_recognize_unknown_symbol_rejected() -> None:
    # € is not the contract currency's symbol
    with pytest.raises(ContractError):
        recognize_money("€ 10.00", Money(currency="MYR"))


def test_recognize_unknown_code_rejected() -> None:
    with pytest.raises(ContractError):
        recognize_money("EUR 10.00", Money(currency="MYR"))


def test_recognize_arbitrary_three_letter_word_rejected() -> None:
    # Any leading 3-letter token that is not the contract currency is rejected.
    with pytest.raises(ContractError):
        recognize_money("ABC 12.50", Money(currency="MYR"))


def test_recognize_symbol_mismatch_rejected() -> None:
    # contract currency is USD but symbol RM presented
    with pytest.raises(ContractError):
        recognize_money("RM 10.00", Money(currency="USD"))


def test_recognize_whitespace_only_rejected() -> None:
    with pytest.raises(ContractError):
        recognize_money("   ", Money(currency="MYR"))


def test_parse_amount_exact_decimal() -> None:
    assert parse_amount("12.50", "MYR") == "12.50"


def test_parse_amount_scientific_normalized() -> None:
    assert parse_amount("1.25E+2", "MYR") == "125"


def test_parse_amount_negative_preserved() -> None:
    assert parse_amount("-3.40", "MYR") == "-3.40"


def test_parse_amount_comma_thousands_stripped() -> None:
    assert parse_amount("1,234.56", "MYR") == "1234.56"


def test_parse_amount_eur_comma_decimal() -> None:
    # EUR uses comma as decimal separator (Q1=A): "1.234,56" → "1234.56"
    assert parse_amount("1.234,56", "EUR") == "1234.56"


def test_parse_amount_invalid_text_rejected() -> None:
    with pytest.raises(ContractError):
        parse_amount("abc", "MYR")


def test_parse_amount_multiple_decimals_rejected() -> None:
    with pytest.raises(ContractError):
        parse_amount("1.2.3", "MYR")
