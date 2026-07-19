"""Tests for the CanonicalIPContract value object and factory."""

from __future__ import annotations

import pytest

from paxman import IP, CanonicalIPContract, parse_contract
from paxman._errors import ContractError


def test_defaults() -> None:
    c = CanonicalIPContract()
    assert c.allow_ipv4 is True
    assert c.allow_ipv6 is True
    assert c.preserve_zone_id is True
    assert c.kind == "canonical_ip"
    assert c.version == 1


def test_factory_defaults_match_contract() -> None:
    assert IP() == CanonicalIPContract()


def test_factory_overrides() -> None:
    c = IP(allow_ipv4=False, allow_ipv6=False, preserve_zone_id=False)
    assert c.allow_ipv4 is False
    assert c.allow_ipv6 is False
    assert c.preserve_zone_id is False


def test_as_dict_round_trip() -> None:
    c = IP(allow_ipv4=False)
    spec = c.as_dict()
    assert spec == {
        "kind": "canonical_ip",
        "allow_ipv4": False,
        "allow_ipv6": True,
        "preserve_zone_id": True,
        "version": 1,
        "version_field": 1,
    }
    assert parse_contract(spec) == c


def test_parse_contract_short_circuits_value_object() -> None:
    c = IP()
    assert parse_contract(c) is c


def test_parse_contract_dict_builds_contract() -> None:
    c = parse_contract({"kind": "canonical_ip", "allow_ipv6": False})
    assert isinstance(c, CanonicalIPContract)
    assert c.allow_ipv6 is False
    assert c.allow_ipv4 is True


def test_invalid_bool_field_raises_contract_error() -> None:
    with pytest.raises(ContractError):
        parse_contract({"kind": "canonical_ip", "allow_ipv4": 1})


def test_unsupported_version_raises_contract_error() -> None:
    with pytest.raises(ContractError):
        parse_contract({"kind": "canonical_ip", "version": 2})


def test_unsupported_version_field_raises_contract_error() -> None:
    with pytest.raises(ContractError):
        parse_contract({"kind": "canonical_ip", "version_field": 5})


def test_non_int_version_raises_contract_error() -> None:
    with pytest.raises(ContractError):
        parse_contract({"kind": "canonical_ip", "version": "1"})


def test_unknown_kind_raises_contract_error() -> None:
    with pytest.raises(ContractError):
        parse_contract({"kind": "canonical_bogus"})


def test_dsl_authority_override_is_not_dropped() -> None:
    result = parse_contract({"kind": "canonical_ip", "authority_override": "OVERRIDE_X"})
    assert isinstance(result, CanonicalIPContract)
    assert result.authority_override == "OVERRIDE_X"


def test_factory_authority_override_round_trips() -> None:
    c = IP(authority_override="Y")
    assert c.authority_override == "Y"
