"""Tests for the GeolocationCapability (four-stage canonicalization)."""

from __future__ import annotations

from typing import cast

import attrs
import pytest

from paxman._capabilities.geolocation.canonicalizer import GeolocationCapability
from paxman._capabilities.geolocation.contract import CanonicalGeolocationContract, Geolocation
from paxman._core.contracts import Contract
from paxman._core.status import Status


def _cap() -> GeolocationCapability:
    return GeolocationCapability()


def _contract(**kw: object) -> CanonicalGeolocationContract:
    return Geolocation(**kw)  # type: ignore[arg-type]


class TestGeolocationCapability:
    def test_capability_metadata(self) -> None:
        assert _cap().name == "geolocation_canonicalization"

    def test_can_handle_matches_geolocation_contract(self) -> None:
        assert _cap().can_handle(_contract(), "40.7128, -74.0060") is True

    def test_can_handle_accepts_none_and_str(self) -> None:
        assert _cap().can_handle(_contract(), None) is True
        assert _cap().can_handle(_contract(), "40.7128, -74.0060") is True

    def test_can_handle_rejects_non_str_non_none(self) -> None:
        assert _cap().can_handle(_contract(), 1) is False

    def test_can_handle_rejects_non_geolocation_contract(self) -> None:
        assert _cap().can_handle(cast(Contract, "nope"), "40.7128, -74.0060") is False

    def test_decimal_pair_unsigned_is_ambiguous(self) -> None:
        # Default contract requires a hemisphere; an unsigned decimal pair is
        # ambiguous (Law 4 — never guess the sign).
        r = _cap().canonicalize("40.7128, -74.0060", _contract())
        assert r.status is Status.AMBIGUOUS
        assert r.value is None
        assert "ambiguous_hemisphere" in {e.rule for e in r.evidence}

    def test_decimal_hemisphere_letter_canonicalized(self) -> None:
        r = _cap().canonicalize("40.7128N 74.0060W", _contract())
        assert r.status is Status.CANONICALIZED
        assert r.value == "40.712800,-74.006000"
        rules = {e.rule for e in r.evidence}
        assert "canonicalized_geolocation" in rules
        assert "axis_order_applied" in rules
        assert "hemisphere_resolved" in rules
        assert "precision_applied" in rules

    def test_dms_exact_conversion(self) -> None:
        # Spec §7 matrix value is a bug; the implementation follows §4.1's
        # exact Decimal algorithm: 40°42'46" = 40.7127778° -> 40.712778.
        r = _cap().canonicalize("40°42'46\"N 74°0'21\"W", _contract())
        assert r.status is Status.CANONICALIZED
        assert r.value == "40.712778,-74.005833"
        rules = {e.rule for e in r.evidence}
        assert "dms_to_decimal" in rules
        assert "canonicalized_geolocation" in rules
        assert "hemisphere_resolved" in rules

    def test_idempotent_re_feed_of_canonical_form(self) -> None:
        # Under require_hemisphere=False the canonical decimal form re-feeds
        # deterministically (the canonical output is itself a valid input).
        once = _cap().canonicalize("40.7128, 74.0060", _contract(require_hemisphere=False))
        assert once.status is Status.CANONICALIZED
        twice = _cap().canonicalize(once.value, _contract(require_hemisphere=False))
        assert twice.status is Status.CANONICALIZED
        assert twice.value == once.value

    def test_coordinate_order_lon_lat(self) -> None:
        r = _cap().canonicalize("40.7128N 74.0060W", _contract(coordinate_order="lon_lat"))
        assert r.status is Status.CANONICALIZED
        assert r.value == "-74.006000,40.712800"
        assert "axis_order_applied" in {e.rule for e in r.evidence}

    def test_unsigned_pair_ambiguous_under_default(self) -> None:
        r = _cap().canonicalize("40.7128, 74.0060", _contract())
        assert r.status is Status.AMBIGUOUS
        assert r.value is None
        assert "ambiguous_hemisphere" in {e.rule for e in r.evidence}

    def test_unsigned_pair_canonicalized_when_hemisphere_not_required(self) -> None:
        r = _cap().canonicalize("40.7128, 74.0060", _contract(require_hemisphere=False))
        assert r.status is Status.CANONICALIZED
        assert r.value == "40.712800,74.006000"
        rules = {e.rule for e in r.evidence}
        assert "hemisphere_defaulted" in rules
        assert "canonicalized_geolocation" in rules

    def test_out_of_range_is_invalid(self) -> None:
        r = _cap().canonicalize("91.0, 0.0", _contract())
        assert r.status is Status.INVALID
        assert "out_of_range" in {e.rule for e in r.evidence}

    def test_empty_string_is_missing(self) -> None:
        r = _cap().canonicalize("", _contract())
        assert r.status is Status.MISSING
        assert "missing_value" in {e.rule for e in r.evidence}

    def test_none_is_missing(self) -> None:
        r = _cap().canonicalize(None, _contract())
        assert r.status is Status.MISSING
        assert "missing_value" in {e.rule for e in r.evidence}

    def test_unparseable_is_invalid(self) -> None:
        r = _cap().canonicalize("abc", _contract())
        assert r.status is Status.INVALID
        assert "unrecognized_format" in {e.rule for e in r.evidence}

    def test_whitespace_is_trimmed(self) -> None:
        r = _cap().canonicalize("  40.7128N 74.0060W  ", _contract())
        assert r.status is Status.CANONICALIZED
        assert r.value == "40.712800,-74.006000"
        assert "trimmed_whitespace" in {e.rule for e in r.evidence}

    def test_not_a_geolocation_contract_is_invalid(self) -> None:
        not_contract = cast(Contract, "not_a_contract")
        r = _cap().canonicalize("40.7128N 74.0060W", not_contract)
        assert r.status is Status.INVALID
        assert "not_a_geolocation_contract" in {e.rule for e in r.evidence}

    def test_not_a_string_value_is_invalid(self) -> None:
        r = _cap().canonicalize(cast(object, 1234), _contract())
        assert r.status is Status.INVALID
        assert "not_a_string_value" in {e.rule for e in r.evidence}

    def test_artifact_is_immutable(self) -> None:
        # CapabilityResult is a frozen attrs class; mutating evidence/value
        # must raise FrozenInstanceError (mirrors money/ip immutability checks).
        r = _cap().canonicalize("40.7128N 74.0060W", _contract())
        with pytest.raises(attrs.exceptions.FrozenInstanceError):
            r.value = "mutated"  # type: ignore[misc]


class TestGeolocationResolverEdgeCases:
    def test_dms_signed_canonicalized(self) -> None:
        # geo_dms_signed shape: "d m s, d m s" with optional signs. An unsigned
        # degree axis is ambiguous under require_hemisphere=True, so we use
        # require_hemisphere=False to exercise the signed-DMS resolver path.
        # Per spec §4.1 the components are summed literally: lon = -74 + 0 + 21/3600.
        r = _cap().canonicalize("40 42 46, -74 0 21", _contract(require_hemisphere=False))
        assert r.status is Status.CANONICALIZED
        assert r.value == "40.712778,-73.994167"
        assert "dms_to_decimal" in {e.rule for e in r.evidence}

    def test_dms_signed_both_axes_signed_resolved(self) -> None:
        # Both degree axes carry explicit signs, so hemisphere_resolved fires
        # and the form canonicalizes under the default (hemisphere-requiring)
        # contract. Components summed literally: lat = -40 + 46/60 + 46/3600.
        r = _cap().canonicalize("-40 42 46, -74 0 21", _contract())
        assert r.status is Status.CANONICALIZED
        assert r.value == "-39.287222,-73.994167"
        assert "hemisphere_resolved" in {e.rule for e in r.evidence}

    def test_dms_signed_negative_seconds(self) -> None:
        # A negative seconds component on the second axis flips its sign.
        r = _cap().canonicalize("40 0 0, -74 0 -21", _contract(require_hemisphere=False))
        assert r.status is Status.CANONICALIZED
        assert r.value == "40.000000,-74.005833"

    def test_dms_signed_negative_first_axis_seconds(self) -> None:
        # A negative seconds component on the first axis flips its sign.
        r = _cap().canonicalize("-40 0 -21, 74 0 0", _contract(require_hemisphere=False))
        assert r.status is Status.CANONICALIZED
        assert r.value == "-40.005833,74.000000"

    def test_dms_signed_negative_degree_positive_seconds(self) -> None:
        # Regression: degree sign and seconds sign disagree. Literal sum
        # lat = -40 + 0 + 21/3600 = -39.994167 (sign must NOT be double-applied).
        r = _cap().canonicalize("-40 0 21, 74 0 0", _contract(require_hemisphere=False))
        assert r.status is Status.CANONICALIZED
        assert r.value == "-39.994167,74.000000"

    def test_dms_signed_positive_degree_negative_seconds(self) -> None:
        # Regression: degree positive, seconds negative. Literal sum
        # lat = 40 + 0 - 21/3600 = 39.994167.
        r = _cap().canonicalize("40 0 -21, 74 0 0", _contract(require_hemisphere=False))
        assert r.status is Status.CANONICALIZED
        assert r.value == "39.994167,74.000000"

    def test_lon_lat_ambiguous_candidates(self) -> None:
        # An unsigned decimal pair under a hemisphere-requiring lon_lat contract
        # enumerates the four sign readings as AMBIGUOUS candidates.
        r = _cap().canonicalize("40.7128, -74.0060", _contract(coordinate_order="lon_lat"))
        assert r.status is Status.AMBIGUOUS
        assert r.candidates is not None
        assert "40.712800,74.006000" in r.candidates
        assert "-40.712800,-74.006000" in r.candidates

    def test_out_of_range_longitude_invalid(self) -> None:
        r = _cap().canonicalize("0.0, 200.0", _contract())
        assert r.status is Status.INVALID
        assert "out_of_range" in {e.rule for e in r.evidence}

    def test_out_of_range_longitude_via_dms_signed_invalid(self) -> None:
        r = _cap().canonicalize("0 0 0, 200 0 0", _contract(require_hemisphere=False))
        assert r.status is Status.INVALID
        assert "out_of_range" in {e.rule for e in r.evidence}

    def test_classify_unrecognized_format_direct(self) -> None:
        # Direct classify path when recognition returned no rep.
        from paxman._capabilities.geolocation.canonicalizer import classify
        from paxman._capabilities.geolocation.grammar import recognize

        status, value, evidence, _cands = classify(None, [], _contract())
        assert status is Status.INVALID
        assert value is None
        assert "unrecognized_format" in {e.rule for e in evidence}
        # recognize returns None for junk, exercising the same classify branch.
        assert recognize("abc") is None
