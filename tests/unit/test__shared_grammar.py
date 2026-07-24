from __future__ import annotations

import re

from paxman._capabilities._shared.grammar import (
    Grammar,
    Provenance,
    RecognizedRep,
    make_grammar,
    recognize_grammars,
)


def _fake_grammars() -> tuple[Grammar, ...]:
    return (
        make_grammar(
            "canonical_x",
            Provenance(name="Fake spec §1 (36-char canonical form)"),
            r"^(?P<value>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$",
        ),
    )


def test_make_grammar_compiles_and_anchors():
    g = make_grammar("id", Provenance(name="src"), r"^abc$")
    assert g.recognize_fn("abc") is not None
    assert g.recognize_fn("Xabc") is None


def test_recognize_grammars_returns_rep_with_raw_captures():
    reps = recognize_grammars(
        _fake_grammars(), "abcd1234-abcd-1234-abcd-1234567890ab"
    )
    assert len(reps) == 1
    rep = reps[0]
    assert isinstance(rep, RecognizedRep)
    assert rep.grammar_id == "canonical_x"
    assert rep.raw == "abcd1234-abcd-1234-abcd-1234567890ab"
    assert rep.captures == {"value": "abcd1234-abcd-1234-abcd-1234567890ab"}


def test_recognize_grammars_no_match_returns_empty():
    assert recognize_grammars(_fake_grammars(), "not-a-uuid") == []


def test_recognize_grammars_strip_true_trims_input():
    g = make_grammar("ws", Provenance(name="Fake spec §2 (whitespace tolerated)"), r"^(?P<value>abc)$")
    assert recognize_grammars((g,), "  abc  ") == []
    reps = recognize_grammars((g,), "  abc  ", strip=True)
    assert len(reps) == 1
    assert reps[0].raw == "abc"


def test_recognize_grammars_strip_charset_is_narrow():
    # A narrow ASCII charset must NOT strip a non-breaking space (\u00a0),
    # preserving country's determinism (full str.strip() WOULD remove it).
    g = make_grammar("ws", Provenance(name="Fake spec §2 (whitespace tolerated)"), r"^(?P<value>abc)$")
    # ASCII spaces are stripped by the narrow charset → matches.
    reps = recognize_grammars((g,), "  abc  ", strip=" \t\r\n\f\v")
    assert len(reps) == 1
    assert reps[0].raw == "abc"
    # A non-breaking space is NOT in the narrow charset → preserved → no match.
    assert (
        recognize_grammars((g,), "abc\u00a0", strip=" \t\r\n\f\v")
        == []
    )
