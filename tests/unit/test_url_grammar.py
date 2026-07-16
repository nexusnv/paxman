from paxman._capabilities.url.contract import URL
from paxman._capabilities.url.grammar import GRAMMARS, recognize

# Mandate laws touched (Law 1 determinism — recognition is a pure function of
# (value, contract); Law 3 never-guess — recognition assigns shape only, never
# meaning; Law 14 provenance — every grammar cites RFC 3986 §3). These tests
# evidence deterministic shape-only recognition and grammar disjointness.


def test_three_disjoint_grammars():
    assert len(GRAMMARS) == 3
    assert {g.id for g in GRAMMARS} == {"absolute", "authority_relative", "path_relative"}


def test_absolute_matches_scheme():
    reps = recognize("https://Example.COM/a", URL())
    assert len(reps) == 1
    assert reps[0].grammar_id == "absolute"
    assert reps[0].captures["scheme"] == "https"
    assert reps[0].captures["authority"] == "Example.COM"
    assert reps[0].captures["pathqf"] == "/a"


def test_authority_relative():
    reps = recognize("//host.example/path", URL())
    assert len(reps) == 1
    assert reps[0].grammar_id == "authority_relative"


def test_path_relative():
    reps = recognize("/a/b/c", URL())
    assert len(reps) == 1
    assert reps[0].grammar_id == "path_relative"


def test_recognize_assigns_no_meaning():
    reps = recognize("https://Example.COM/A", URL())
    assert reps[0].captures["authority"] == "Example.COM"


def test_recognize_returns_empty_for_non_url_contract():
    # recognize() must guard on contract type and return [] for any contract
    # that is not a CanonicalURLContract.
    class _Other:
        pass

    assert recognize("https://Example.COM/A", _Other()) == []


def test_no_double_match():
    reps = recognize("/a/b", URL())
    assert [r.grammar_id for r in reps] == ["path_relative"]


def test_letter_string_recognized_as_path_relative():
    reps = recognize("not a uri at all !!", URL())
    assert isinstance(reps, list)
    assert reps[0].grammar_id == "path_relative"


def test_trailing_newline_rejected():
    # fullmatch must reject an unconsumed tail; a trailing newline must not
    # be silently accepted as a partially consumed match.
    assert recognize("https://Example.COM/a\n", URL()) == []
    assert recognize("//host.example/path\n", URL()) == []
    assert recognize("/a/b\n", URL()) == []
