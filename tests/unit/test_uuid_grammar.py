"""Tests for the uuid grammar recognition layer (Layer 1).

These tests pin the uuid grammars: each grammar must match its intended
inputs and yield the correct RAW string captures (no semantic meaning is
assigned at this layer), and unrecognised inputs must yield ``[]``.
"""

from __future__ import annotations

from paxman._capabilities.uuid.contract import CanonicalUUIDContract
from paxman._capabilities.uuid.grammar import (
    GRAMMARS,
    RecognizedRep,
    recognize,
)


def _contract() -> CanonicalUUIDContract:
    return CanonicalUUIDContract()


def _rep_by_id(reps: list[RecognizedRep], grammar_id: str) -> RecognizedRep | None:
    for rep in reps:
        if rep.grammar_id == grammar_id:
            return rep
    return None


class TestUUIDGrammar:
    """The GRAMMARS catalogue is well-formed and complete (spec §0)."""

    def test_grammar_count(self) -> None:
        assert isinstance(GRAMMARS, tuple)
        assert len(GRAMMARS) == 1

    def test_grammar_ids_are_unique(self) -> None:
        ids = [g.id for g in GRAMMARS]
        assert len(ids) == len(set(ids))

    def test_every_grammar_records_provenance_source(self) -> None:
        # Law 14: every grammar carries a citation-backed source (an
        # authoritative spec section, a documented provider behavior, or an
        # explicit Paxman policy reference) — not a bare description.
        for grammar in GRAMMARS:
            assert grammar.source
            assert any(token in grammar.source for token in ("RFC", "Paxman", "spec", "§"))


class TestCanonicalUUIDGrammar:
    def test_canonical_uuid_matches_and_yields_raw_captures(self) -> None:
        reps = recognize("550e8400-e29b-41d4-a716-446655440000", _contract())
        rep = _rep_by_id(reps, "canonical_uuid")
        assert rep is not None
        assert rep.source == (
            "RFC 4122 §3 (the canonical form is 36 chars; 8-4-4-4-12 grouping; lowercase hex)"
        )
        assert rep.captures == {"value": "550e8400-e29b-41d4-a716-446655440000"}

    def test_canonical_uuid_rejects_32_hex(self) -> None:
        reps = recognize("550e8400e29b41d4a716446655440000", _contract())
        assert _rep_by_id(reps, "canonical_uuid") is None

    def test_wrong_contract_yields_empty(self) -> None:
        assert recognize("550e8400-e29b-41d4-a716-446655440000", object()) == []
