"""Tests for the DateCapability (see spec 2026-07-15-date-canonicalization-design)."""

from __future__ import annotations

from paxman import Status
from paxman._capabilities.date import _RULE_PROVENANCE, DateCapability
from paxman._capabilities.date.contract import CanonicalDateContract
from paxman._core.contracts import Contract


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

    def test_numeric_under_iso_locale_is_ambiguous(self) -> None:
        # Spec §3.3 / Flag A: ISO now enumerates BOTH MM/DD and DD/MM orderings,
        # so 03/04/2025 admits two distinct calendar days -> AMBIGUOUS.
        r = _cap().canonicalize("03/04/2025", _contract("ISO"))
        assert r.status is Status.AMBIGUOUS
        assert r.evidence[0].rule == "ambiguous_ordering"

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

    def test_rfc2822_date_only(self) -> None:
        r = _cap().canonicalize("1 Jan 2025", _contract())
        assert r.status is Status.CANONICALIZED
        assert r.value == "2025-01-01"
        assert r.evidence[0].rule == "parsed_rfc2822"

    def test_rfc2822_date_only_with_day_of_week(self) -> None:
        r = _cap().canonicalize("Tue, 01 Jan 2025", _contract())
        assert r.status is Status.CANONICALIZED
        assert r.value == "2025-01-01"
        assert r.evidence[0].rule == "parsed_rfc2822"

    def test_rfc2822_datetime_with_zone(self) -> None:
        r = _cap().canonicalize("Tue, 01 Jan 2025 12:00:00 +0000", _contract())
        assert r.status is Status.CANONICALIZED
        assert r.value == "2025-01-01T12:00:00Z"
        assert r.evidence[-1].rule == "normalized_to_utc"

    def test_rfc2822_datetime_with_named_zone(self) -> None:
        r = _cap().canonicalize("01 Jan 2025 07:00:00 EST", _contract())
        assert r.status is Status.CANONICALIZED
        assert r.value == "2025-01-01T12:00:00Z"

    def test_rfc2822_datetime_without_zone_is_ambiguous(self) -> None:
        r = _cap().canonicalize("01 Jan 2025 12:00:00", _contract())
        assert r.status is Status.AMBIGUOUS
        assert r.evidence[0].rule == "ambiguous_naive_datetime"

    def test_unix_timestamp_integer(self) -> None:
        r = _cap().canonicalize("1609459200", _contract())
        assert r.status is Status.CANONICALIZED
        assert r.value == "2021-01-01T00:00:00Z"
        assert r.evidence[0].rule == "parsed_unix_timestamp"

    def test_unix_timestamp_fractional(self) -> None:
        r = _cap().canonicalize("1609459200.5", _contract())
        assert r.value == "2021-01-01T00:00:00.500000Z"

    def test_unix_timestamp_negative(self) -> None:
        r = _cap().canonicalize("-2208988800", _contract())
        assert r.status is Status.CANONICALIZED
        assert r.value == "1900-01-01T00:00:00Z"

    def test_compact_integer_is_not_a_timestamp(self) -> None:
        # A compact integer that is not a recognised date shape is claimed but
        # not recognised -> INVALID (Decision A), not UNSUPPORTED.
        r = _cap().canonicalize("20250101", _contract())
        assert r.status is Status.INVALID
        assert r.evidence[0].rule == "unrecognized_format"

    def test_unrecognized_format_is_invalid(self) -> None:
        # A string with no recognised date shape is claimed but not recognised
        # -> INVALID (Decision A), not UNSUPPORTED.
        r = _cap().canonicalize("tomorrow", _contract())
        assert r.status is Status.INVALID
        assert r.evidence[0].rule == "unrecognized_format"

    def test_empty_value_is_missing(self) -> None:
        r = _cap().canonicalize("", _contract())
        assert r.status is Status.MISSING
        assert r.evidence[0].rule == "empty_value"

    def test_whitespace_only_is_missing(self) -> None:
        r = _cap().canonicalize("   ", _contract())
        assert r.status is Status.MISSING

    def test_non_iso_slash_under_iso_is_invalid(self) -> None:
        # A slash form that names no calendar day is still INVALID under ISO
        # (both MD and DM orderings are impossible). Note: a *year-first* slash
        # such as "2025/01/01" is now a recognised grammar (numeric_slash_ymd)
        # and canonicalizes; only slash forms with no valid reading stay INVALID.
        r = _cap().canonicalize("32/01/2025", _contract("ISO"))
        assert r.status is Status.INVALID

    def test_invalid_iso_date_is_invalid(self) -> None:
        r = _cap().canonicalize("2025-13-01", _contract())
        assert r.status is Status.INVALID
        assert r.evidence[0].rule == "invalid_calendar_date"

    def test_rfc2822_date_only_calendar_invalid_is_invalid(self) -> None:
        r = _cap().canonicalize("32 Jan 2025", _contract())
        assert r.status is Status.INVALID
        assert r.evidence[0].rule == "invalid_calendar_date"

    def test_rfc2822_datetime_calendar_invalid_is_invalid(self) -> None:
        r = _cap().canonicalize("Tue, 32 Jan 2025 12:00:00 +0000", _contract())
        assert r.status is Status.INVALID
        assert r.evidence[0].rule == "invalid_calendar_date"

    def test_unix_timestamp_out_of_range_is_invalid(self) -> None:
        r = _cap().canonicalize("999999999999999999999", _contract())
        assert r.status is Status.INVALID
        assert r.evidence[0].rule == "invalid_epoch_value"


class TestSub1000YearCanonicalization:
    """Years below AD 1000 must render with a 4-digit, zero-padded year.

    glibc's strftime("%Y") drops zero-padding for years < 1000, which would
    yield "1-01-01" instead of "0001-01-01" and break the YYYY-MM-DD form
    and idempotence. Surfaced by the 100-input experiment (idempotence probe).
    """

    def test_sub_1000_year_is_zero_padded_date(self) -> None:
        r = _cap().canonicalize("0001-01-01", _contract())
        assert r.status is Status.CANONICALIZED
        assert r.value == "0001-01-01"

    def test_sub_1000_year_is_zero_padded_datetime(self) -> None:
        r = _cap().canonicalize("0999-06-15T00:00:00Z", _contract())
        assert r.status is Status.CANONICALIZED
        assert r.value == "0999-06-15T00:00:00Z"

    def test_year_999_is_zero_padded(self) -> None:
        r = _cap().canonicalize("0999-12-31", _contract())
        assert r.status is Status.CANONICALIZED
        assert r.value == "0999-12-31"

    def test_sub_1000_year_round_trips_idempotently(self) -> None:
        r = _cap().canonicalize("0001-01-01", _contract())
        assert r.status is Status.CANONICALIZED
        r2 = _cap().canonicalize(r.value, _contract())
        assert r2.status is Status.CANONICALIZED
        assert r2.value == r.value


class TestLaw14ProvenanceManifest:
    """Audit ``_RULE_PROVENANCE`` against the capability source (MANDATE §10.2)."""

    _DISPATCH_INVARIANTS = frozenset(
        {"not_a_date_contract", "not_a_string_value", "empty_value", "unrecognized_format"}
    )

    def test_every_manifest_entry_beyond_dispatch_has_provenance(self) -> None:
        for rule_name, provenance in _RULE_PROVENANCE.items():
            if rule_name in self._DISPATCH_INVARIANTS:
                continue
            assert provenance != "", f"Law 14 violation: {rule_name!r} has empty provenance"

    def test_dispatch_invariants_allow_listed_empty(self) -> None:
        for invariant in self._DISPATCH_INVARIANTS:
            assert invariant in _RULE_PROVENANCE, f"{invariant!r} missing from manifest"
            assert _RULE_PROVENANCE[invariant] == "", f"{invariant!r} should be empty"

    def test_manifest_keys_cover_every_fired_rule(self) -> None:
        c = _cap()
        inputs: list[tuple[object, Contract]] = [
            ("2025-01-01", _contract()),
            ("2025-01-01T12:00:00Z", _contract()),
            ("2025-01-01T07:00:00-05:00", _contract()),
            ("2025-01-01T12:00:00", _contract()),
            ("03/04/2025", _contract("US")),
            ("03/04/2025", _contract("EU")),
            ("03/04/2025", _contract("ISO")),
            ("03/04/25", _contract("US")),
            ("1 Jan 2025", _contract()),
            ("Tue, 01 Jan 2025 12:00:00 +0000", _contract()),
            ("01 Jan 2025 12:00:00", _contract()),
            ("1700000000", _contract()),
            ("20250101", _contract()),
            ("tomorrow", _contract()),
            ("", _contract()),
            ("  ", _contract()),
            ("2025/01/01", _contract("ISO")),
            ("2025-13-01", _contract()),
        ]
        fired: set[str] = set()
        for value, contract in inputs:
            r = c.canonicalize(value, contract)
            for ev in r.evidence:
                fired.add(ev.rule)
        # Exercise the two non-str dispatch paths directly.
        r1 = c.canonicalize("2025-01-01", "not a contract")  # type: ignore[arg-type]
        r2 = c.canonicalize(12345, _contract())  # type: ignore[arg-type]
        for ev in r1.evidence + r2.evidence:
            fired.add(ev.rule)
        for rule in fired:
            assert rule in _RULE_PROVENANCE, f"fired rule {rule!r} missing from manifest"
