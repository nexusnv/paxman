"""Tests for the CanonicalMoneyContract value object and factory."""

from __future__ import annotations

import pytest

from paxman import CanonicalMoneyContract, Money, parse_contract
from paxman._errors import ContractError


def test_defaults() -> None:
    c = Money(currency="MYR")
    assert c.currency == "MYR"
    assert c.allow_symbol is True
    assert c.allow_code is True
    assert c.strip_spaces is True
    assert c.kind == "canonical_money"
    assert c.version == 1


def test_factory_requires_currency() -> None:
    with pytest.raises(TypeError):
        Money()  # type: ignore[call-arg]


def test_factory_defaults_match_contract() -> None:
    assert Money(currency="MYR") == CanonicalMoneyContract(currency="MYR")


def test_factory_overrides() -> None:
    c = Money(currency="USD", allow_symbol=False, allow_code=False, strip_spaces=False)
    assert c.allow_symbol is False
    assert c.allow_code is False
    assert c.strip_spaces is False


def test_as_dict_round_trip() -> None:
    c = Money(currency="MYR", allow_symbol=False)
    spec = c.as_dict()
    assert spec == {
        "kind": "canonical_money",
        "currency": "MYR",
        "allow_symbol": False,
        "allow_code": True,
        "strip_spaces": True,
        "version": 1,
        "version_field": 1,
    }
    assert parse_contract(spec) == c


def test_parse_contract_short_circuits_value_object() -> None:
    c = Money(currency="USD")
    assert parse_contract(c) is c


def test_parse_contract_dict_builds_contract() -> None:
    c = parse_contract({"kind": "canonical_money", "currency": "USD", "allow_code": False})
    assert isinstance(c, CanonicalMoneyContract)
    assert c.currency == "USD"
    assert c.allow_code is False


def test_parse_contract_missing_currency_raises() -> None:
    with pytest.raises(ContractError):
        parse_contract({"kind": "canonical_money"})


def test_parse_contract_bad_currency_raises() -> None:
    with pytest.raises(ContractError):
        parse_contract({"kind": "canonical_money", "currency": "XYZ"})


def test_parse_contract_lowercase_currency_normalized() -> None:
    c = parse_contract({"kind": "canonical_money", "currency": "myr"})
    assert c.currency == "MYR"


def test_unsupported_version_raises_contract_error() -> None:
    with pytest.raises(ContractError):
        parse_contract({"kind": "canonical_money", "currency": "USD", "version": 2})


def test_unsupported_version_field_raises_contract_error() -> None:
    with pytest.raises(ContractError):
        parse_contract({"kind": "canonical_money", "currency": "USD", "version_field": 5})
