"""Tests for the email grammar recognition layer (Layer 1).

These tests pin the email grammars: each grammar must match its intended
inputs and yield the correct RAW string captures (no semantic meaning is
assigned at this layer), and unrecognised inputs must yield ``[]``.
"""

from __future__ import annotations

from paxman._capabilities.email.contract import CanonicalEmailContract
from paxman._capabilities.email.grammar import (
    GRAMMARS,
    Grammar,
    RecognizedRep,
    recognize,
)


def _contract() -> CanonicalEmailContract:
    return CanonicalEmailContract()


def _rep_by_id(reps: list[RecognizedRep], grammar_id: str) -> RecognizedRep | None:
    for rep in reps:
        if rep.grammar_id == grammar_id:
            return rep
    return None


class TestGrammarCatalogue:
    """The GRAMMARS catalogue is well-formed and complete (spec §0)."""

    def test_grammars_is_non_empty_tuple_of_grammar(self) -> None:
        assert isinstance(GRAMMARS, tuple)
        assert len(GRAMMARS) == 4
        for grammar in GRAMMARS:
            assert isinstance(grammar, Grammar)
            assert grammar.id
            assert grammar.provenance.name
            assert grammar.recognize_fn is not None

    def test_grammar_ids_are_unique(self) -> None:
        ids = [g.id for g in GRAMMARS]
        assert len(ids) == len(set(ids))

    def test_every_grammar_records_provenance(self) -> None:
        for grammar in GRAMMARS:
            assert grammar.provenance.name
            assert any(token in grammar.provenance.name for token in ("RFC", "Paxman", "spec", "§"))


class TestAddrSpecGrammar:
    def test_addr_spec_matches_and_yields_raw_captures(self) -> None:
        reps = recognize("John.Doe@Example.COM", _contract())
        rep = _rep_by_id(reps, "addr_spec")
        assert rep is not None
        assert rep.provenance.name == "RFC 5322 §3.4.1"
        assert rep.captures == {"local": "John.Doe", "domain": "Example.COM"}

    def test_addr_spec_rejects_internal_whitespace(self) -> None:
        # "user @example.com" has a space, so addr_spec (no internal
        # whitespace) must not match.
        reps = recognize("user @example.com", _contract())
        assert _rep_by_id(reps, "addr_spec") is None

    def test_addr_spec_rejects_non_email(self) -> None:
        assert recognize("not-an-email", _contract()) == []


class TestWsPaddedAddrSpecGrammar:
    def test_ws_padded_matches_and_yields_raw_captures(self) -> None:
        reps = recognize("azahari @ gmail.com", _contract())
        rep = _rep_by_id(reps, "ws_padded_addr_spec")
        assert rep is not None
        assert rep.provenance.name == "RFC 5322 §3.4.1 + §1.3/§3.2.2"
        assert rep.captures == {"local": "azahari ", "domain": " gmail.com"}

    def test_ws_padded_also_matches_clean_addr_spec(self) -> None:
        reps = recognize("azahari@gmail.com", _contract())
        assert _rep_by_id(reps, "ws_padded_addr_spec") is not None

    def test_ws_padded_captures_trailing_space_in_local(self) -> None:
        reps = recognize("user @example.com", _contract())
        rep = _rep_by_id(reps, "ws_padded_addr_spec")
        assert rep is not None
        assert rep.captures == {"local": "user ", "domain": "example.com"}


class TestVerbalAtDotAddrSpecGrammar:
    def test_verbal_at_dot_matches_and_yields_raw_captures(self) -> None:
        reps = recognize("azahari at gmail dot com", _contract())
        rep = _rep_by_id(reps, "verbal_at_dot_addr_spec")
        assert rep is not None
        assert rep.provenance.name == "RFC 5322 §3.4.1"
        assert rep.captures == {"local": "azahari", "mid": "gmail", "tld": "com"}

    def test_verbal_at_dot_does_not_match_clean_addr_spec(self) -> None:
        reps = recognize("azahari@gmail.com", _contract())
        assert _rep_by_id(reps, "verbal_at_dot_addr_spec") is None


class TestQuotedLocalAddrSpecGrammar:
    def test_quoted_local_matches_and_yields_raw_captures(self) -> None:
        reps = recognize('"x y"@z.com', _contract())
        rep = _rep_by_id(reps, "quoted_local_addr_spec")
        assert rep is not None
        assert rep.provenance.name == "RFC 5322 §3.2.4"
        assert rep.captures == {"local": '"x y"', "domain": "z.com"}

    def test_quoted_local_does_not_match_clean_addr_spec(self) -> None:
        reps = recognize("xy@z.com", _contract())
        assert _rep_by_id(reps, "quoted_local_addr_spec") is None


class TestUnrecognized:
    def test_nonsense_yields_empty(self) -> None:
        assert recognize("tomorrow", _contract()) == []

    def test_empty_string_yields_empty(self) -> None:
        assert recognize("", _contract()) == []

    def test_wrong_contract_yields_empty(self) -> None:
        assert recognize("a@b.c", object()) == []
