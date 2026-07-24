"""Tests for the country recognition grammar (Layer 1)."""

from __future__ import annotations

from paxman import CanonicalCountryContract, Country, parse_contract
from paxman._capabilities.country.grammar import GRAMMARS, recognize


def test_recognize_alpha2() -> None:
    reps = recognize("US", Country())
    assert len(reps) == 1
    assert reps[0].shape == "alpha2"


def test_recognize_alpha2_grammar_id() -> None:
    reps = recognize("US", Country())
    assert len(reps) == 1
    assert reps[0].grammar_id == "country_alpha2"


def test_recognize_narrow_ascii_strip_only() -> None:
    # Country's strip is ASCII-whitespace only (" \t\r\n\f\v"). A non-ASCII
    # whitespace (no-break space U+00A0) must NOT be trimmed, so the token
    # stays "\xa0US\xa0" and falls through to the name shape (never becomes a
    # trimmed "US" alpha2). This pins the narrow charset through the _shared
    # migration — a full Unicode strip would wrongly canonicalize it.
    reps = recognize("\xa0US\xa0", Country())
    assert len(reps) == 1
    assert reps[0].shape == "name"
    assert reps[0].raw == "\xa0US\xa0"


def test_authority_override_dsl_round_trip() -> None:
    override = {"ISO 3166-1": "2024"}
    spec = {
        "kind": "canonical_country",
        "authority_override": override,
    }
    c = parse_contract(spec)
    assert isinstance(c, CanonicalCountryContract)
    assert c.authority_override == override
    # The override is excluded from as_dict (does not affect identity/replay).
    assert "authority_override" not in c.as_dict()


def test_recognize_alpha3() -> None:
    reps = recognize("USA", Country())
    assert len(reps) == 1
    assert reps[0].shape == "alpha3"


def test_recognize_name() -> None:
    reps = recognize("United States", Country())
    assert len(reps) == 1
    assert reps[0].shape == "name"


def test_recognize_trims_whitespace() -> None:
    reps = recognize("  US  ", Country())
    assert len(reps) == 1
    assert reps[0].shape == "alpha2"


def test_recognize_none_returns_empty() -> None:
    assert recognize("", Country()) == []


def test_grammars_carry_provenance() -> None:
    for g in GRAMMARS:
        assert g.provenance.name
