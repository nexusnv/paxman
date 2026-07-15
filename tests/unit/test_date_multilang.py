"""TDD coverage for date multi-language canonicalization (spec 2026-07-16).

Exercises the enumerate -> validate -> classify algorithm for full / non-English
month-name dates and the ambiguity/validity edge cases from spec §1 and §8.
"""

from __future__ import annotations

import pytest

from paxman import Date, Status
from paxman._capabilities.date import DateCapability
from paxman._capabilities.date.contract import CanonicalDateContract
from paxman._dsl.parser import parse_contract
from paxman._errors import ContractError


def _cap() -> DateCapability:
    return DateCapability()


class TestMultilingualTextMonthCanonicalization:
    """Spec §1: full / non-English month names deterministically name a day."""

    @pytest.mark.parametrize(
        ("value", "language"),
        [
            ("16 July 2026", "en"),
            ("July, 16 2026", "en"),
            ("16-Jul-2026", "en"),
            ("16. Juli 2026", "de"),
            ("16 Julai 2026", "ms"),
        ],
    )
    def test_canonicalizes_to_2026_07_16(self, value: str, language: str) -> None:
        r = _cap().canonicalize(value, Date(locale="ISO", language=language))
        assert r.status is Status.CANONICALIZED
        assert r.value == "2026-07-16"
        assert r.evidence[0].rule == "parsed_text_month_date"

    def test_wrong_language_is_invalid(self) -> None:
        # "Juli" is a German month name; under language="en" the grammar layer
        # finds no shape match (the month alternation excludes "Juli"), so the
        # value was claimed but not recognised -> INVALID (Decision A), not
        # UNSUPPORTED. No cross-language guess is made (Law 7).
        r = _cap().canonicalize("16. Juli 2026", Date(locale="ISO", language="en"))
        assert r.status is Status.INVALID
        assert r.evidence[0].rule == "unrecognized_format"

    def test_german_month_under_english_is_invalid(self) -> None:
        r = _cap().canonicalize("16. Juli 2026", Date(locale="ISO", language="en"))
        assert r.status is Status.INVALID

    def test_malay_month_under_english_is_invalid(self) -> None:
        r = _cap().canonicalize("16 Julai 2026", Date(locale="ISO", language="en"))
        assert r.status is Status.INVALID


class TestNumericAmbiguityAndValidity:
    """Spec §8: slash-form ambiguity/validity under each locale policy."""

    def test_iso_two_digit_year_is_ambiguous(self) -> None:
        r = _cap().canonicalize("16/07/26", Date(locale="ISO"))
        assert r.status is Status.AMBIGUOUS
        assert r.evidence[0].rule == "ambiguous_two_digit_year"

    def test_eu_two_digit_year_is_ambiguous(self) -> None:
        r = _cap().canonicalize("16/07/26", Date(locale="EU"))
        assert r.status is Status.AMBIGUOUS
        assert r.evidence[0].rule == "ambiguous_two_digit_year"

    def test_us_two_digit_year_with_impossible_month_is_invalid(self) -> None:
        # MM/DD -> month 16 is impossible -> 0 calendar survivors -> INVALID.
        r = _cap().canonicalize("16/07/26", Date(locale="US"))
        assert r.status is Status.INVALID
        assert r.evidence[0].rule == "invalid_calendar_date"

    def test_iso_seven_six_two_six_is_ambiguous(self) -> None:
        # DD/MM invalid (month 16); MM/DD valid but 2-digit year -> AMBIGUOUS.
        r = _cap().canonicalize("07/16/26", Date(locale="ISO"))
        assert r.status is Status.AMBIGUOUS
        assert r.evidence[0].rule == "ambiguous_two_digit_year"

    def test_iso_ordering_ambiguous_four_digit(self) -> None:
        r = _cap().canonicalize("01/02/2026", Date(locale="ISO"))
        assert r.status is Status.AMBIGUOUS
        assert r.evidence[0].rule == "ambiguous_ordering"

    def test_iso_invalid_calendar_is_invalid(self) -> None:
        r = _cap().canonicalize("32/07/2026", Date(locale="ISO"))
        assert r.status is Status.INVALID
        assert r.evidence[0].rule == "invalid_calendar_date"


class TestProvenanceAndIdempotence:
    """Law 14 (non-empty provenance) and Law 2 (idempotence)."""

    def test_canonicalized_result_carries_non_empty_provenance(self) -> None:
        r = _cap().canonicalize("16 July 2026", Date(locale="ISO", language="en"))
        assert r.status is Status.CANONICALIZED
        assert all(e.provenance != "" for e in r.evidence)

    def test_rfc2822_weekday_prefix_canonicalizes(self) -> None:
        # Bonus fix: a weekday-prefixed RFC 2822 form must canonicalize, not
        # be rejected as unrecognized.
        r = _cap().canonicalize("Thursday, 16 July 2026", Date(locale="ISO", language="en"))
        assert r.status is Status.CANONICALIZED
        assert r.value == "2026-07-16"

    @pytest.mark.parametrize(
        ("value", "language"),
        [
            ("16 July 2026", "en"),
            ("July, 16 2026", "en"),
            ("16-Jul-2026", "en"),
            ("16. Juli 2026", "de"),
            ("16 Julai 2026", "ms"),
        ],
    )
    def test_five_canonicalized_forms_are_idempotent(
        self, value: str, language: str
    ) -> None:
        first = _cap().canonicalize(value, Date(locale="ISO", language=language))
        assert first.status is Status.CANONICALIZED
        second = _cap().canonicalize(first.value, Date(locale="ISO", language=language))
        assert second.status is Status.CANONICALIZED
        assert second.value == first.value


class TestTwoDigitYearPolicy:
    """Spec §3.2: the century policy resolves 2-digit years deterministically."""

    def test_reject_policy_drops_two_digit_year(self) -> None:
        r = _cap().canonicalize("03/04/25", Date(locale="US", two_digit_year="reject"))
        assert r.status is Status.INVALID
        assert r.evidence[0].rule == "rejected_two_digit_year"

    def test_pivot_policy_resolves_single_century(self) -> None:
        # Spec §3.2 corrected: year = (YYYY // 100) * 100 + YY. pivot:2000
        # -> base 2000, so 25 -> 2025.
        r = _cap().canonicalize(
            "03/04/25", Date(locale="US", two_digit_year="pivot:2000")
        )
        assert r.status is Status.CANONICALIZED
        assert r.value == "2025-03-04"

    def test_pivot_policy_resolves_upper_century(self) -> None:
        # pivot:2000 -> base 2000, so 70 -> 2070 (not the classic <70 split).
        r = _cap().canonicalize(
            "03/04/70", Date(locale="US", two_digit_year="pivot:2000")
        )
        assert r.status is Status.CANONICALIZED
        assert r.value == "2070-03-04"


class TestAmbiguousSurfacesCandidates:
    """Spec §2.4: an AMBIGUOUS result MUST surface its candidate set."""

    def test_text_month_two_digit_year_both_assignments(self) -> None:
        # Spec §5 + §8: "25 July 26" under pivot:2000 enumerates both
        # (day, year) assignments -> 2026-07-25 and 2025-07-26.
        r = _cap().canonicalize(
            "25 July 26", Date(locale="ISO", two_digit_year="pivot:2000")
        )
        assert r.status is Status.AMBIGUOUS
        assert r.value is None
        assert r.candidates == ("2025-07-26", "2026-07-25")

    def test_iso_two_digit_year_surfaces_century_expanded(self) -> None:
        r = _cap().canonicalize("16/07/26", Date(locale="ISO"))
        assert r.status is Status.AMBIGUOUS
        assert r.candidates is not None
        assert len(r.candidates) > 1
        assert r.candidates == tuple(sorted(r.candidates))

    def test_iso_ordering_ambiguous_surfaces_both_readings(self) -> None:
        r = _cap().canonicalize("01/02/2026", Date(locale="ISO"))
        assert r.status is Status.AMBIGUOUS
        assert r.candidates == ("2026-01-02", "2026-02-01")

    def test_iso_seven_six_two_six_surfaces_candidates(self) -> None:
        r = _cap().canonicalize("07/16/26", Date(locale="ISO"))
        assert r.status is Status.AMBIGUOUS
        assert r.candidates is not None
        assert len(r.candidates) > 1

    @pytest.mark.parametrize(
        ("value", "contract"),
        [
            ("16 July 2026", Date(locale="ISO", language="en")),
            ("16/07/26", Date(locale="US")),
            ("32/07/2026", Date(locale="ISO")),
            ("16. Juli 2026", Date(locale="ISO", language="en")),
        ],
    )
    def test_non_ambiguous_results_have_no_candidates(
        self, value: str, contract: object
    ) -> None:
        r = _cap().canonicalize(value, contract)  # type: ignore[arg-type]
        assert r.candidates is None


class TestNewGrammarCoverageClosures:
    """The 7 new grammar productions canonicalize deterministically (task)."""

    @pytest.mark.parametrize(
        ("value", "language", "expected"),
        [
            ("July 16, 2026", "en", "2026-07-16"),
            ("the 3rd of July, 2026", "en", "2026-07-03"),
            ("16th July 2026", "en", "2026-07-16"),
            ("16 July 2026 AD", "en", "2026-07-16"),
            ("July 16th, 2026", "en", "2026-07-16"),
            ("16-Jul 2026", "en", "2026-07-16"),
        ],
    )
    def test_text_month_closures_canonicalize(
        self, value: str, language: str, expected: str
    ) -> None:
        r = _cap().canonicalize(value, Date(locale="ISO", language=language))
        assert r.status is Status.CANONICALIZED
        assert r.value == expected
        assert r.evidence[0].rule == "parsed_text_month_date"

    def test_numeric_slash_ymd_canonicalizes(self) -> None:
        # Year-first slash is a fixed Y/M/D reading: no locale ordering
        # enumeration and no century ambiguity (year is exactly four digits).
        r = _cap().canonicalize("2026/07/16", Date(locale="ISO"))
        assert r.status is Status.CANONICALIZED
        assert r.value == "2026-07-16"
        assert r.evidence[0].rule == "parsed_text_month_date"


class TestContractValidation:
    """Spec §3: language validation and locale default in the contract.

    Validation lives in ``_build_date`` (the Dict DSL parser), so these cases
    are exercised via ``parse_contract`` rather than the constructor.
    """

    def test_language_defaults_to_en(self) -> None:
        c = CanonicalDateContract()
        assert c.language == "en"
        assert c.locale == "ISO"

    def test_unsupported_language_rejected(self) -> None:
        with pytest.raises(ContractError):
            parse_contract({"kind": "canonical_date", "language": "fr"})

    def test_invalid_two_digit_year_policy_rejected(self) -> None:
        with pytest.raises(ContractError):
            parse_contract({"kind": "canonical_date", "two_digit_year": "bogus"})

    def test_invalid_pivot_policy_rejected(self) -> None:
        with pytest.raises(ContractError):
            parse_contract({"kind": "canonical_date", "two_digit_year": "pivot:notanumber"})
