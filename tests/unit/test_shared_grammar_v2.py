"""Tests for the refactored shared grammar scaffold (Provenance + pure recognize)."""

from paxman._capabilities._shared.grammar import (
    Grammar,  # noqa: F401 — verify export is importable
    Provenance,
    RecognizedRep,  # noqa: F401 — verify export is importable
    make_grammar,
    parser_grammar,
    recognize_grammars,
)


def test_make_grammar_carries_provenance():
    p = Provenance(name="RFC 5322", version="§3.4.1")
    g = make_grammar("addr_spec", p, r"^(?P<local>.+)@(?P<domain>.+)$")
    assert isinstance(g.provenance, Provenance)
    assert g.provenance.name == "RFC 5322"


def test_recognize_grammars_is_pure():
    """recognize_grammars(grammars, value) is a pure function — no contract parameter."""
    p = Provenance(name="test")
    g = make_grammar("test", p, r"^(?P<value>.+)$")
    reps = recognize_grammars((g,), "hello")
    assert len(reps) == 1
    assert reps[0].provenance.name == "test"


def test_recognize_grammars_no_match():
    p = Provenance(name="test")
    g = make_grammar("test", p, r"^abc$")
    assert recognize_grammars((g,), "xyz") == []


def test_recognize_grammars_strip_true():
    p = Provenance(name="test")
    g = make_grammar("test", p, r"^(?P<v>abc)$")
    reps = recognize_grammars((g,), "  abc  ", strip=True)
    assert len(reps) == 1
    assert reps[0].captures == {"v": "abc"}


def test_parser_grammar_accepts_callable():
    def my_parser(value: str) -> dict[str, str] | None:
        if value.isdigit():
            return {"digit": value}
        return None

    p = Provenance(name="custom")
    g = parser_grammar("custom", p, my_parser)
    reps = recognize_grammars((g,), "123")
    assert len(reps) == 1
    assert reps[0].captures == {"digit": "123"}


def test_recognized_rep_carries_raw():
    p = Provenance(name="test")
    g = make_grammar("test", p, r"^(?P<v>.+)$")
    reps = recognize_grammars((g,), "  hello  ", strip=True)
    assert reps[0].raw == "hello"


def test_recognized_rep_shape():
    p = Provenance(name="test")
    g = make_grammar("test", p, r"^(?P<v>.+)$", shape="my_shape")
    reps = recognize_grammars((g,), "x")
    assert reps[0].shape == "my_shape"
