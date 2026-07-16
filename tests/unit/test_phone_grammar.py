# tests/unit/test_phone_grammar.py
from paxman._capabilities.phone.contract import CanonicalPhoneContract
from paxman._capabilities.phone.grammar import recognize

# NOTE: this test imports contract.py which does not exist yet; it will
# fail until Task 3 lands. To run Task 2 in isolation, temporarily inline:
#
#   class _StubContract:  # minimal stand-in
#       kind = "canonical_phone"
#       version = 1
#       version_field = 1
#       country = "US"
#       def as_dict(self): return {"kind": "canonical_phone"}
#
# and pass _StubContract() to recognize. Remove the stub once Task 3 lands.


def test_e164_grammar():
    reps = recognize("+16502530000", CanonicalPhoneContract())
    assert len(reps) == 1
    assert reps[0].grammar_id == "e164"
    assert reps[0].captures["cc_first"] == "1"
    assert reps[0].captures["national"] == "6502530000"
    assert reps[0].source  # Law 14 provenance present


def test_national_grammar_requires_separator():
    reps = recognize("(650) 253-0000", CanonicalPhoneContract())
    assert any(r.grammar_id == "national" for r in reps)
    # digits-only string must NOT match national (needs a separator)
    assert not any(
        r.grammar_id == "national" for r in recognize("6502530000", CanonicalPhoneContract())
    )


def test_digits_only_grammar():
    reps = recognize("6502530000", CanonicalPhoneContract())
    assert len(reps) == 1
    assert reps[0].grammar_id == "digits_only"
    assert reps[0].captures["national"] == "6502530000"


def test_letter_string_rejected():
    assert recognize("call-me", CanonicalPhoneContract()) == []


def test_recognize_assigns_no_meaning():
    reps = recognize("+16502530000", CanonicalPhoneContract())
    assert set(reps[0].captures.keys()) == {"cc_first", "national"}
