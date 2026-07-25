"""Tests for the boolean recognition (Layer 1) grammar."""

from __future__ import annotations

from paxman._capabilities.boolean.contract import CanonicalBooleanContract
from paxman._capabilities.boolean.grammar import GRAMMARS, recognize


def _contract(
    *,
    accept_numeric: bool = True,
    accept_words: bool = True,
    case_sensitive: bool = False,
) -> CanonicalBooleanContract:
    return CanonicalBooleanContract(
        accept_numeric=accept_numeric,
        accept_words=accept_words,
        case_sensitive=case_sensitive,
    )


def test_recognize_true_default_case_insensitive() -> None:
    reps = recognize("Yes", _contract())
    assert len(reps) == 1
    assert reps[0].captures["token"] == "yes"


def test_recognize_numeric() -> None:
    reps = recognize("0", _contract())
    assert reps[0].captures["token"] == "0"


def test_recognize_truthy_case_insensitive() -> None:
    reps = recognize("TRUE", _contract())
    assert reps[0].captures["token"] == "true"


def test_recognize_case_sensitive_rejects_upper() -> None:
    reps = recognize("TRUE", _contract(case_sensitive=True))
    assert reps == []


def test_recognize_case_sensitive_accepts_lower() -> None:
    reps = recognize("true", _contract(case_sensitive=True))
    assert reps[0].captures["token"] == "true"


def test_recognize_unknown_returns_empty() -> None:
    assert recognize("maybe", _contract()) == []


def test_recognize_rejects_non_boolean_contract() -> None:
    assert recognize("true", object()) == []


def test_grammars_have_provenance() -> None:
    for g in GRAMMARS:
        assert g.provenance.name != ""
