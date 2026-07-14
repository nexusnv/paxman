"""Tests for the DateCapability (spec: .superpowers/specs/2026-07-15-...)."""

from __future__ import annotations

from paxman import Status
from paxman._capabilities.builtins.date import DateCapability
from paxman._contracts.contract import CanonicalDateContract


def _cap() -> DateCapability:
    return DateCapability()


def _contract(locale: str = "ISO") -> CanonicalDateContract:
    return CanonicalDateContract(locale=locale)


class TestDateCapability:
    def test_name_is_date_canonicalization(self) -> None:
        assert _cap().name == "date_canonicalization"

    def test_can_handle_accepts_date_contract_and_string(self) -> None:
        assert _cap().can_handle(_contract(), "2025-01-01") is True

    def test_can_handle_rejects_non_date_contract(self) -> None:
        assert _cap().can_handle("not a contract", "2025-01-01") is False  # type: ignore[arg-type]

    def test_can_handle_rejects_non_string_value(self) -> None:
        assert _cap().can_handle(_contract(), 12345) is False  # type: ignore[arg-type]

    def test_iso_date_canonicalizes(self) -> None:
        r = _cap().canonicalize("2025-01-01", _contract())
        assert r.status is Status.CANONICALIZED
        assert r.value == "2025-01-01"
        assert r.evidence[0].rule == "parsed_iso_date"

    def test_iso_datetime_with_z_canonicalizes_to_utc_z(self) -> None:
        r = _cap().canonicalize("2025-01-01T12:00:00Z", _contract())
        assert r.status is Status.CANONICALIZED
        assert r.value == "2025-01-01T12:00:00Z"
        assert r.evidence[-1].rule == "no_transformation_needed"

    def test_iso_datetime_with_offset_normalized_to_utc_z(self) -> None:
        r = _cap().canonicalize("2025-01-01T07:00:00-05:00", _contract())
        assert r.status is Status.CANONICALIZED
        assert r.value == "2025-01-01T12:00:00Z"

    def test_iso_datetime_with_fractional_seconds(self) -> None:
        r = _cap().canonicalize("2025-01-01T12:00:00.5Z", _contract())
        assert r.value == "2025-01-01T12:00:00.500000Z"

    def test_iso_datetime_without_zone_is_ambiguous(self) -> None:
        r = _cap().canonicalize("2025-01-01T12:00:00", _contract())
        assert r.status is Status.AMBIGUOUS
        assert r.evidence[0].rule == "ambiguous_naive_datetime"

    def test_us_numeric_mm_dd_yyyy(self) -> None:
        r = _cap().canonicalize("03/04/2025", _contract("US"))
        assert r.status is Status.CANONICALIZED
        assert r.value == "2025-03-04"
        assert r.evidence[0].rule == "parsed_us_numeric"

    def test_eu_numeric_dd_mm_yyyy(self) -> None:
        r = _cap().canonicalize("03/04/2025", _contract("EU"))
        assert r.status is Status.CANONICALIZED
        assert r.value == "2025-04-03"
        assert r.evidence[0].rule == "parsed_eu_numeric"

    def test_numeric_under_iso_locale_is_invalid(self) -> None:
        r = _cap().canonicalize("03/04/2025", _contract("ISO"))
        assert r.status is Status.INVALID
        assert r.evidence[0].rule == "numeric_format_requires_us_or_eu_locale"

    def test_us_numeric_invalid_month_is_invalid(self) -> None:
        r = _cap().canonicalize("13/04/2025", _contract("US"))
        assert r.status is Status.INVALID
        assert r.evidence[0].rule == "invalid_calendar_date"

    def test_eu_numeric_invalid_month_is_invalid(self) -> None:
        r = _cap().canonicalize("04/13/2025", _contract("EU"))
        assert r.status is Status.INVALID
        assert r.evidence[0].rule == "invalid_calendar_date"

    def test_two_digit_year_is_ambiguous(self) -> None:
        r = _cap().canonicalize("03/04/25", _contract("US"))
        assert r.status is Status.AMBIGUOUS
        assert r.evidence[0].rule == "ambiguous_two_digit_year"
