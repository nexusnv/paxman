"""Tests for the date grammar recognition layer (Layer 1).

These tests pin the bracket-notation grammars: each grammar must match its
intended inputs and yield the correct RAW string captures (no semantic
meaning is assigned at this layer), and unrecognised inputs must yield ``[]``.
"""

from __future__ import annotations

import pytest

from paxman._capabilities.date.contract import CanonicalDateContract
from paxman._capabilities.date.grammar import (
    GRAMMARS,
    Grammar,
    RecognizedRep,
    compile_grammar,
    recognize,
)


def _contract(language: str = "en", locale: str = "ISO") -> CanonicalDateContract:
    return CanonicalDateContract(locale=locale, language=language)


def _rep_by_id(reps: list[RecognizedRep], grammar_id: str) -> RecognizedRep | None:
    for rep in reps:
        if rep.grammar_id == grammar_id:
            return rep
    return None


class TestGrammarCatalogue:
    """The GRAMMARS catalogue is well-formed and complete (spec §0)."""

    def test_grammars_is_non_empty_tuple_of_grammar(self) -> None:
        assert isinstance(GRAMMARS, tuple)
        assert len(GRAMMARS) == 16
        for grammar in GRAMMARS:
            assert isinstance(grammar, Grammar)
            assert grammar.id
            assert grammar.source
            assert grammar.pattern
            assert grammar.compiled is not None
            assert grammar.field_roles

    def test_grammar_ids_are_unique(self) -> None:
        ids = [g.id for g in GRAMMARS]
        assert len(ids) == len(set(ids))

    def test_numeric_slash_carries_numeric_triple_shape(self) -> None:
        grammar = next(g for g in GRAMMARS if g.id == "numeric_slash")
        assert grammar.shape == "numeric_triple"
        assert grammar.field_roles == {"N1": "n1", "N2": "n2", "N3": "n3"}

    def test_every_grammar_records_provenance_source(self) -> None:
        # Law 14: every grammar carries a non-empty source.
        for grammar in GRAMMARS:
            assert grammar.source


class TestIsoDateGrammar:
    def test_iso_date_matches_and_yields_raw_captures(self) -> None:
        reps = recognize("2026-07-16", _contract())
        rep = _rep_by_id(reps, "iso_date")
        assert rep is not None
        assert rep.source == "ISO 8601"
        assert rep.captures == {"year": "2026", "month": "07", "day": "16"}


class TestTextMonthGrammars:
    def test_text_month_dmy_space(self) -> None:
        reps = recognize("16 July 2026", _contract())
        rep = _rep_by_id(reps, "text_month_dmy")
        assert rep is not None
        assert rep.captures == {"day": "16", "month": "July", "year": "2026"}

    def test_text_month_dmy_dot_german(self) -> None:
        reps = recognize("16. Juli 2026", _contract(language="de"))
        rep = _rep_by_id(reps, "text_month_dmy_dot")
        assert rep is not None
        assert rep.captures == {"day": "16", "month": "Juli", "year": "2026"}

    def test_text_month_cm_comma(self) -> None:
        reps = recognize("July, 16 2026", _contract())
        rep = _rep_by_id(reps, "text_month_cm")
        assert rep is not None
        assert rep.captures == {"month": "July", "day": "16", "year": "2026"}

    def test_text_month_dash(self) -> None:
        reps = recognize("16-Jul-2026", _contract())
        rep = _rep_by_id(reps, "text_month_dash")
        assert rep is not None
        assert rep.captures == {"day": "16", "month": "Jul", "year": "2026"}

    def test_two_digit_year_captured_as_raw_string(self) -> None:
        # The grammar captures the 2-digit year verbatim; meaning is assigned
        # later by the resolver (day/year swap enumeration).
        reps = recognize("25 July 26", _contract())
        rep = _rep_by_id(reps, "text_month_dmy")
        assert rep is not None
        assert rep.captures["year"] == "26"


class TestNumericSlashGrammar:
    def test_numeric_slash_yields_n1_n2_n3(self) -> None:
        reps = recognize("16/07/26", _contract())
        rep = _rep_by_id(reps, "numeric_slash")
        assert rep is not None
        assert rep.captures == {"n1": "16", "n2": "07", "n3": "26"}

    def test_numeric_slash_four_digit_year(self) -> None:
        reps = recognize("01/02/2026", _contract())
        rep = _rep_by_id(reps, "numeric_slash")
        assert rep is not None
        assert rep.captures == {"n1": "01", "n2": "02", "n3": "2026"}


class TestRfc2822Grammar:
    def test_rfc2822_with_weekday(self) -> None:
        reps = recognize("Thursday, 16 July 2026", _contract())
        # Only rfc2822_date matches (the value has a leading weekday token, so
        # the day-first text_month_dmy grammar cannot match).
        assert len(reps) == 1
        rep = reps[0]
        assert rep.grammar_id == "rfc2822_date"
        assert rep.source == "RFC 2822 §3.3"
        assert rep.captures == {
            "weekday": "Thursday",
            "day": "16",
            "month": "July",
            "year": "2026",
        }

    def test_rfc2822_without_weekday_also_matches(self) -> None:
        # "16 July 2026" matches both text_month_dmy and rfc2822_date (the
        # weekday prefix is optional). Recognition is non-exclusive.
        reps = recognize("16 July 2026", _contract())
        assert _rep_by_id(reps, "rfc2822_date") is not None
        assert _rep_by_id(reps, "text_month_dmy") is not None


class TestOrdinalGrammar:
    def test_ordinal_of_month_with_weekday(self) -> None:
        reps = recognize("Thursday, the 3rd of July, 2026", _contract())
        rep = _rep_by_id(reps, "ordinal_of_month")
        assert rep is not None
        assert rep.source == "paxman spec/date (ordinal day form, natural language)"
        assert rep.captures == {
            "weekday": "Thursday",
            "ordinal": "3rd",
            "month": "July",
            "year": "2026",
        }

    def test_ordinal_word_form(self) -> None:
        # The grammar requires a leading ", the" (after an optional weekday),
        # so the natural-language form carries a weekday prefix.
        reps = recognize("Thursday, the twelfth of December, 2026", _contract())
        rep = _rep_by_id(reps, "ordinal_of_month")
        assert rep is not None
        assert rep.captures["ordinal"] == "twelfth"
        assert rep.captures["month"] == "December"


class TestLanguageScoping:
    """Law 7: the month-name reading language comes only from contract.language."""

    def test_german_month_unrecognised_under_english(self) -> None:
        # "Juli" is not in the English month table, so the grammar layer finds
        # no shape match under language="en" -> [] (no cross-language guess).
        reps = recognize("16. Juli 2026", _contract(language="en"))
        assert reps == []

    def test_german_month_recognised_under_german(self) -> None:
        reps = recognize("16. Juli 2026", _contract(language="de"))
        assert _rep_by_id(reps, "text_month_dmy_dot") is not None

    def test_malay_month_recognised_under_malay(self) -> None:
        reps = recognize("16 Julai 2026", _contract(language="ms"))
        assert _rep_by_id(reps, "text_month_dmy") is not None


class TestUnrecognized:
    def test_nonsense_yields_empty(self) -> None:
        assert recognize("tomorrow", _contract()) == []

    def test_compact_integer_yields_empty(self) -> None:
        # No grammar shape matches a bare compact integer.
        assert recognize("20250101", _contract()) == []

    def test_empty_string_yields_empty(self) -> None:
        assert recognize("", _contract()) == []


class TestCompileGrammar:
    def test_unsupported_language_raises(self) -> None:
        with pytest.raises(ValueError):
            compile_grammar("[DAY] [MONTH(lang)] [YEAR]", "fr")

    def test_compiled_regex_fullmatches_intended_input(self) -> None:
        rx = compile_grammar("[DAY] [MONTH(lang)] [YEAR]", "en")
        assert rx.fullmatch("16 July 2026") is not None
        assert rx.fullmatch("16-Jul-2026") is None

    def test_case_insensitive_month_names(self) -> None:
        reps = recognize("16 JULY 2026", _contract())
        assert _rep_by_id(reps, "text_month_dmy") is not None


class TestTextMonthMdyCommaGrammar:
    def test_matches_and_yields_raw_captures(self) -> None:
        reps = recognize("July 16, 2026", _contract())
        rep = _rep_by_id(reps, "text_month_mdy_comma")
        assert rep is not None
        assert rep.source == "CLDR month names"
        assert rep.captures == {"month": "July", "day": "16", "year": "2026"}

    def test_does_not_match_day_month_order(self) -> None:
        # "16 July 2026" is dmy, not mdy-comma; the comma grammar must not fire.
        reps = recognize("16 July 2026", _contract())
        assert _rep_by_id(reps, "text_month_mdy_comma") is None


class TestOrdinalOfMonthNoWkdayGrammar:
    def test_matches_and_yields_raw_captures(self) -> None:
        reps = recognize("the 3rd of July, 2026", _contract())
        rep = _rep_by_id(reps, "ordinal_of_month_nowkday")
        assert rep is not None
        assert rep.source == "paxman spec/date (ordinal day form, natural language)"
        assert rep.captures == {"ordinal": "3rd", "month": "July", "year": "2026"}

    def test_does_not_match_without_leading_the(self) -> None:
        # The grammar requires a literal "the" before the ordinal.
        reps = recognize("3rd of July, 2026", _contract())
        assert _rep_by_id(reps, "ordinal_of_month_nowkday") is None


class TestTextMonthDmyOrdGrammar:
    def test_matches_and_yields_raw_captures(self) -> None:
        reps = recognize("16th July 2026", _contract())
        rep = _rep_by_id(reps, "text_month_dmy_ord")
        assert rep is not None
        assert rep.source == "CLDR month names"
        assert rep.captures == {"ordinal": "16th", "month": "July", "year": "2026"}

    def test_does_not_match_bare_day(self) -> None:
        # A bare numeric day (no ordinal suffix) must not match this grammar.
        reps = recognize("16 July 2026", _contract())
        assert _rep_by_id(reps, "text_month_dmy_ord") is None


class TestNumericSlashYmdGrammar:
    def test_matches_and_yields_raw_captures(self) -> None:
        reps = recognize("2026/07/16", _contract())
        rep = _rep_by_id(reps, "numeric_slash_ymd")
        assert rep is not None
        assert rep.source == "ISO 8601 (slash ordering)"
        assert rep.captures == {"year": "2026", "month": "07", "day": "16"}

    def test_does_not_match_two_digit_leading_group(self) -> None:
        # The YEAR4 token requires exactly four digits, so "16/07/26" (a
        # 2-digit leading group) must NOT match this grammar — the existing
        # 3-candidate AMBIGUOUS numeric_slash test must stay unchanged.
        reps = recognize("16/07/26", _contract())
        assert _rep_by_id(reps, "numeric_slash_ymd") is None
        assert _rep_by_id(reps, "numeric_slash") is not None


class TestTextMonthDmyEraGrammar:
    def test_matches_and_yields_raw_captures(self) -> None:
        reps = recognize("16 July 2026 AD", _contract())
        rep = _rep_by_id(reps, "text_month_dmy_era")
        assert rep is not None
        assert rep.source == "CLDR month names"
        assert rep.captures == {"day": "16", "month": "July", "year": "2026"}

    def test_does_not_match_without_era_suffix(self) -> None:
        # The trailing " AD" literal is required; without it the grammar must
        # not fire (the value still matches text_month_dmy instead).
        reps = recognize("16 July 2026", _contract())
        assert _rep_by_id(reps, "text_month_dmy_era") is None


class TestTextMonthMdyOrdGrammar:
    def test_matches_and_yields_raw_captures(self) -> None:
        reps = recognize("July 16th, 2026", _contract())
        rep = _rep_by_id(reps, "text_month_mdy_ord")
        assert rep is not None
        assert rep.source == "CLDR month names"
        assert rep.captures == {"month": "July", "ordinal": "16th", "year": "2026"}

    def test_does_not_match_bare_day(self) -> None:
        # A bare numeric day (no ordinal suffix) must not match this grammar.
        reps = recognize("July 16, 2026", _contract())
        assert _rep_by_id(reps, "text_month_mdy_ord") is None


class TestTextMonthDmyMixedsepGrammar:
    def test_matches_and_yields_raw_captures(self) -> None:
        reps = recognize("16-Jul 2026", _contract())
        rep = _rep_by_id(reps, "text_month_dmy_mixedsep")
        assert rep is not None
        assert rep.source == "CLDR month names"
        assert rep.captures == {"day": "16", "month": "Jul", "year": "2026"}

    def test_does_not_match_space_separator(self) -> None:
        # The dash between day and month is required; a space must not match.
        reps = recognize("16 Jul 2026", _contract())
        assert _rep_by_id(reps, "text_month_dmy_mixedsep") is None


class TestTextMonthMdySlashGrammar:
    def test_matches_and_yields_raw_captures(self) -> None:
        reps = recognize("July/16 2026", _contract())
        rep = _rep_by_id(reps, "text_month_mdy_slash")
        assert rep is not None
        assert rep.source == "CLDR month names"
        assert rep.captures == {"month": "July", "day": "16", "year": "2026"}

    def test_does_not_match_dash_separator(self) -> None:
        # The slash between month and day is required; a dash must not match.
        reps = recognize("July-16 2026", _contract())
        assert _rep_by_id(reps, "text_month_mdy_slash") is None
