"""Tests for the CanonicalCountryContract value object and factory."""

from __future__ import annotations

import pytest

from paxman import CanonicalCountryContract, Country, parse_contract
from paxman._errors import ContractError


def test_defaults() -> None:
    c = CanonicalCountryContract()
    assert c.allow_alpha3 is True
    assert c.allow_name is True
    assert c.allow_synonym is True
    assert c.extra_synonyms == {}
    assert c.kind == "canonical_country"
    assert c.version == 1
    assert c.version_field == 1


def test_factory_defaults_match_contract() -> None:
    assert Country() == CanonicalCountryContract()


def test_factory_overrides() -> None:
    c = Country(allow_alpha3=False, allow_name=False, allow_synonym=False)
    assert c.allow_alpha3 is False
    assert c.allow_name is False
    assert c.allow_synonym is False


def test_extra_synonyms_validation_accepts_valid() -> None:
    c = Country(extra_synonyms={"freedonia": "US"})
    assert c.extra_synonyms == {"freedonia": "US"}


def test_extra_synonyms_validation_rejects_bad_target() -> None:
    with pytest.raises(ContractError):
        Country(extra_synonyms={"freedonia": "XYZ"})  # not a 2-letter code


def test_as_dict_round_trip() -> None:
    c = Country(allow_alpha3=False)
    spec = c.as_dict()
    assert spec == {
        "kind": "canonical_country",
        "allow_alpha3": False,
        "allow_name": True,
        "allow_synonym": True,
        "extra_synonyms": {},
        "version": 1,
        "version_field": 1,
    }
    assert parse_contract(spec) == c


def test_parse_contract_kind() -> None:
    assert parse_contract({"kind": "canonical_country"}) == CanonicalCountryContract()


def test_build_country_extra_synonyms_round_trip() -> None:
    spec = {
        "kind": "canonical_country",
        "extra_synonyms": {"freedonia": "US"},
    }
    c = parse_contract(spec)
    assert c.extra_synonyms == {"freedonia": "US"}


def test_build_country_rejects_bad_extra_synonym_target() -> None:
    with pytest.raises(ContractError):
        parse_contract({"kind": "canonical_country", "extra_synonyms": {"x": "ZZ"}})


def test_build_country_rejects_non_bool_flag() -> None:
    with pytest.raises(ContractError):
        parse_contract({"kind": "canonical_country", "allow_alpha3": "yes"})


def test_build_country_rejects_non_v1_version_field() -> None:
    with pytest.raises(ContractError):
        parse_contract({"kind": "canonical_country", "version_field": 2})
