"""Tests for the CanonicalGeolocationContract value object and factory."""

from __future__ import annotations

import pytest

from paxman._capabilities.geolocation.contract import (
    CanonicalGeolocationContract,
    Geolocation,
)
from paxman._dsl.parser import parse_contract
from paxman._errors import ContractError


def test_defaults() -> None:
    c = Geolocation()
    assert c.datum == "WGS84"
    assert c.coordinate_order == "lat_lon"
    assert c.require_hemisphere is True
    assert c.output_format == "decimal"
    assert c.precision == 6
    assert c.kind == "canonical_geolocation"
    assert c.version == 1
    assert c.version_field == 1


def test_factory_defaults_match_contract() -> None:
    assert Geolocation() == CanonicalGeolocationContract()


def test_factory_overrides() -> None:
    c = Geolocation(
        datum="WGS84",
        coordinate_order="lon_lat",
        require_hemisphere=False,
        output_format="decimal",
        precision=3,
    )
    assert c.coordinate_order == "lon_lat"
    assert c.require_hemisphere is False
    assert c.precision == 3


def test_as_dict_round_trip() -> None:
    c = Geolocation(coordinate_order="lon_lat", require_hemisphere=False, precision=3)
    spec = c.as_dict()
    assert spec == {
        "kind": "canonical_geolocation",
        "datum": "WGS84",
        "coordinate_order": "lon_lat",
        "require_hemisphere": False,
        "output_format": "decimal",
        "precision": 3,
        "version": 1,
        "version_field": 1,
    }
    assert parse_contract(spec) == c


def test_parse_contract_dict_builds_contract() -> None:
    c = parse_contract({"kind": "canonical_geolocation", "coordinate_order": "lon_lat"})
    assert isinstance(c, CanonicalGeolocationContract)
    assert c.coordinate_order == "lon_lat"
    assert c.require_hemisphere is True


def test_parse_contract_short_circuits_value_object() -> None:
    c = Geolocation()
    assert parse_contract(c) is c


def test_unsupported_version_raises_contract_error() -> None:
    with pytest.raises(ContractError):
        parse_contract({"kind": "canonical_geolocation", "version": 2})


def test_unsupported_version_field_raises_contract_error() -> None:
    with pytest.raises(ContractError):
        parse_contract({"kind": "canonical_geolocation", "version_field": 5})


def test_non_int_version_raises_contract_error() -> None:
    with pytest.raises(ContractError):
        parse_contract({"kind": "canonical_geolocation", "version": "1"})


def test_bad_datum_raises_contract_error() -> None:
    with pytest.raises(ContractError):
        Geolocation(datum="BOGUS")


def test_bad_coordinate_order_raises_contract_error() -> None:
    with pytest.raises(ContractError):
        Geolocation(coordinate_order="bogus")


def test_bad_output_format_raises_contract_error() -> None:
    with pytest.raises(ContractError):
        Geolocation(output_format="bogus")


def test_precision_out_of_range_raises_contract_error() -> None:
    with pytest.raises(ContractError):
        Geolocation(precision=99)


def test_precision_non_int_raises_contract_error() -> None:
    with pytest.raises(ContractError):
        Geolocation(precision=3.5)  # type: ignore[arg-type]


def test_require_hemisphere_non_bool_raises_contract_error() -> None:
    with pytest.raises(ContractError):
        Geolocation(require_hemisphere=1)  # type: ignore[arg-type]


def test_unknown_kind_raises_contract_error() -> None:
    with pytest.raises(ContractError):
        parse_contract({"kind": "canonical_bogus"})


def test_direct_construction_bad_datum_raises() -> None:
    with pytest.raises(ContractError):
        CanonicalGeolocationContract(datum="BOGUS")


def test_direct_construction_bad_coordinate_order_raises() -> None:
    with pytest.raises(ContractError):
        CanonicalGeolocationContract(coordinate_order="bogus")


def test_direct_construction_bad_output_format_raises() -> None:
    with pytest.raises(ContractError):
        CanonicalGeolocationContract(output_format="bogus")


def test_direct_construction_bad_precision_raises() -> None:
    with pytest.raises(ContractError):
        CanonicalGeolocationContract(precision=99)


def test_direct_construction_bad_require_hemisphere_raises() -> None:
    with pytest.raises(ContractError):
        CanonicalGeolocationContract(require_hemisphere=1)  # type: ignore[arg-type]


def test_direct_construction_bad_version_raises() -> None:
    with pytest.raises(ContractError):
        CanonicalGeolocationContract(version=2)
