from __future__ import annotations

import re

from paxman._capabilities._shared.grammar import (
    Grammar,
    RecognizedRep,
    make_grammar,
    recognize_grammars,
)


class _FakeContract:
    pass


def _fake_grammars() -> tuple[Grammar, ...]:
    return (
        make_grammar(
            "canonical_x",
            "Fake spec §1 (36-char canonical form)",
            r"^(?P<value>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$",
        ),
    )


def test_make_grammar_compiles_and_anchors():
    g = make_grammar("id", "src", r"^abc$")
    assert isinstance(g.compiled, re.Pattern)
    assert g.compiled.fullmatch("abc") is not None
    assert g.compiled.fullmatch("Xabc") is None  # anchored


def test_recognize_grammars_returns_rep_with_raw_captures():
    reps = recognize_grammars(
        _fake_grammars(), "abcd1234-abcd-1234-abcd-1234567890ab", _FakeContract(), _FakeContract
    )
    assert len(reps) == 1
    rep = reps[0]
    assert isinstance(rep, RecognizedRep)
    assert rep.grammar_id == "canonical_x"
    assert rep.raw == "abcd1234-abcd-1234-abcd-1234567890ab"
    assert rep.captures == {"value": "abcd1234-abcd-1234-abcd-1234567890ab"}


def test_recognize_grammars_no_match_returns_empty():
    assert (
        recognize_grammars(_fake_grammars(), "not-a-uuid", _FakeContract(), _FakeContract) == []
    )


def test_recognize_grammars_ignores_non_matching_contract_type():
    class _OtherContract:
        pass

    # value matches the grammar shape, but the contract is the wrong type → no reps
    assert (
        recognize_grammars(
            _fake_grammars(),
            "abcd1234-abcd-1234-abcd-1234567890ab",
            _OtherContract(),
            _FakeContract,
        )
        == []
    )


def test_recognize_grammars_strip_true_trims_input():
    g = make_grammar("ws", "Fake spec §2 (whitespace tolerated)", r"^(?P<value>abc)$")
    assert recognize_grammars((g,), "  abc  ", _FakeContract(), _FakeContract) == []
    reps = recognize_grammars((g,), "  abc  ", _FakeContract(), _FakeContract, strip=True)
    assert len(reps) == 1
    assert reps[0].raw == "abc"
