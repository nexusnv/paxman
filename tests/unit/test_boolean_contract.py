"""Tests for the CanonicalBooleanContract value object and factory."""

from __future__ import annotations

import pytest

from paxman import Boolean, CanonicalBooleanContract, parse_contract
from paxman._errors import ContractError


def test_defaults() -> None:
    c = CanonicalBooleanContract()
    assert c.accept_numeric is True
    assert c.accept_words is True
    assert c.case_sensitive is False
    assert c.kind == "canonical_boolean"
    assert c.version == 1


def test_factory_defaults_match_contract() -> None:
    assert Boolean() == CanonicalBooleanContract()


def test_factory_overrides() -> None:
    c = Boolean(accept_numeric=False, accept_words=False, case_sensitive=True)
    assert c.accept_numeric is False
    assert c.accept_words is False
    assert c.case_sensitive is True


def test_as_dict_round_trip() -> None:
    c = Boolean(accept_numeric=False)
    spec = c.as_dict()
    assert spec == {
        "kind": "canonical_boolean",
        "accept_numeric": False,
        "accept_words": True,
        "case_sensitive": False,
        "output_format": "truefalse",
        "include_grammar": (),
        "exclude_grammar": (),
        "version": 1,
    }
    assert parse_contract(spec) == c


def test_parse_contract_short_circuits_value_object() -> None:
    c = Boolean()
    assert parse_contract(c) is c


def test_parse_contract_dict_builds_contract() -> None:
    c = parse_contract({"kind": "canonical_boolean", "accept_words": False})
    assert isinstance(c, CanonicalBooleanContract)
    assert c.accept_words is False
    assert c.accept_numeric is True


def test_invalid_bool_field_raises_contract_error() -> None:
    with pytest.raises(ContractError):
        parse_contract({"kind": "canonical_boolean", "accept_numeric": 1})


def test_unknown_kind_raises_contract_error() -> None:
    with pytest.raises(ContractError):
        parse_contract({"kind": "canonical_bogus"})


def test_dsl_authority_override_is_not_dropped() -> None:
    result = parse_contract({"kind": "canonical_boolean", "authority_override": "OVERRIDE_X"})
    assert isinstance(result, CanonicalBooleanContract)
    assert result.authority_override == "OVERRIDE_X"


def test_factory_authority_override_round_trips() -> None:
    c = Boolean(authority_override="Y")
    assert c.authority_override == "Y"
