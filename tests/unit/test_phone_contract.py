# tests/unit/test_phone_contract.py
import pytest

from paxman import parse_contract
from paxman._capabilities.phone.contract import CanonicalPhoneContract, Phone
from paxman._errors import ContractError


def test_factory_default():
    c = Phone()
    assert isinstance(c, CanonicalPhoneContract)
    assert c.country == "US"
    assert c.kind == "canonical_phone"
    assert c.version == 1


def test_factory_explicit_country():
    c = Phone(country="GB")
    assert c.country == "GB"


def test_as_dict_roundtrip():
    c = Phone(country="DE")
    d = c.as_dict()
    assert d == {"kind": "canonical_phone", "country": "DE", "output_format": "e164", "version": 1}


def test_build_unknown_country_raises():
    from paxman._capabilities.phone.contract import _build_phone

    with pytest.raises(ContractError):
        _build_phone({"kind": "canonical_phone", "country": "ZZ"})


def test_build_missing_country_defaults_us():
    from paxman._capabilities.phone.contract import _build_phone

    c = _build_phone({"kind": "canonical_phone"})
    assert c.country == "US"


def test_dsl_authority_override_is_not_dropped():
    result = parse_contract(
        {"kind": "canonical_phone", "country": "US", "authority_override": "OVERRIDE_X"}
    )
    assert isinstance(result, CanonicalPhoneContract)
    assert result.authority_override == "OVERRIDE_X"


def test_factory_authority_override_round_trips():
    c = Phone(authority_override="Y")
    assert c.authority_override == "Y"
