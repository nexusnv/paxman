"""Tests for the geolocation recognition (Layer 1) grammar."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

import pytest

from paxman._capabilities.geolocation.contract import CanonicalGeolocationContract
from paxman._capabilities.geolocation.grammar import (
    GRAMMARS,
    RecognizedRep,
    _parse_number,
    _split_sign,
    recognize,
)
from paxman._capabilities.uuid.contract import CanonicalUUIDContract


def test_recognize_guard_rejects_other_contract() -> None:
    # The standard seam guard: a non-geolocation contract yields no reps.
    assert recognize("40.7128, -74.0060", CanonicalUUIDContract()) == []


def test_recognize_unknown_returns_empty_list() -> None:
    # Aligned return type: unrecognised input is [] (NOT None).
    assert recognize("abc", CanonicalGeolocationContract()) == []


def test_recognize_decimal_pair_returns_single_rep() -> None:
    reps = recognize("40.7128, -74.0060", CanonicalGeolocationContract())
    assert isinstance(reps, list)
    assert len(reps) == 1
    rep = reps[0]
    assert isinstance(rep, RecognizedRep)
    assert rep.grammar_id == "geo_decimal_pair"
    assert rep.shape == "geo_decimal_pair"
    assert rep.source != ""


def test_recognize_decimal_pair_shape() -> None:
    reps = recognize("40.7128, -74.0060", CanonicalGeolocationContract())
    assert len(reps) == 1
    assert reps[0].shape == "geo_decimal_pair"


def test_recognize_decimal_hemisphere_shape() -> None:
    reps = recognize("40.7128N 74.0060W", CanonicalGeolocationContract())
    assert len(reps) == 1
    assert reps[0].shape == "geo_decimal_hemi"


def test_recognize_dms_shape() -> None:
    reps = recognize("40°42'46\"N 74°0'21\"W", CanonicalGeolocationContract())
    assert len(reps) == 1
    assert reps[0].shape == "geo_dms"


def test_recognize_dms_signed_shape() -> None:
    reps = recognize("40 42 46, -74 0 21", CanonicalGeolocationContract())
    assert len(reps) == 1
    assert reps[0].shape == "geo_dms_signed"


def test_recognize_unknown_returns_none() -> None:
    assert recognize("abc", CanonicalGeolocationContract()) == []


def test_grammars_have_provenance_source() -> None:
    for g in GRAMMARS:
        assert g.source != ""


def test_split_sign_plain_positive() -> None:
    assert _split_sign("40.7128") == ("+", "40.7128")


def test_split_sign_explicit_minus() -> None:
    assert _split_sign("-74.0060") == ("-", "74.0060")


def test_split_sign_explicit_plus() -> None:
    assert _split_sign("+74.0060") == ("+", "74.0060")


def test_split_sign_parentheses_negative() -> None:
    assert _split_sign("(40.7128)") == ("-", "40.7128")


def test_parse_number_exact_decimal() -> None:
    assert _parse_number("40.7128") == Decimal("40.7128")


def test_parse_number_non_finite_rejected() -> None:
    with pytest.raises(ValueError):
        _parse_number("inf")


def test_parse_number_garbage_rejected() -> None:
    with pytest.raises(InvalidOperation):
        _parse_number("abc")
