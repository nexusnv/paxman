# tests/unit/test_phone_capability.py
from paxman import canonicalize
from paxman._capabilities.phone.canonicalizer import PhoneCapability
from paxman._capabilities.phone.contract import CanonicalPhoneContract, Phone
from paxman._core.status import Status


def test_can_handle():
    cap = PhoneCapability()
    assert cap.can_handle(CanonicalPhoneContract(), "6502530000")
    assert not cap.can_handle(CanonicalPhoneContract(), 6502530000)
    assert not cap.can_handle(object(), "6502530000")


def test_e164_passthrough():
    cap = PhoneCapability()
    res = cap.canonicalize("+16502530000", CanonicalPhoneContract())
    assert res.status is Status.CANONICALIZED
    assert res.value == "+16502530000"
    assert res.evidence[0].rule == "no_transformation_needed"


def test_us_national_expands():
    cap = PhoneCapability()
    res = cap.canonicalize("(650) 253-0000", Phone(country="US"))
    assert res.status is Status.CANONICALIZED
    assert res.value == "+16502530000"
    assert res.evidence[0].rule == "cc_prepended"
    assert res.evidence[0].provenance  # non-empty Law 14 citation


def test_gb_digits_only_expands():
    cap = PhoneCapability()
    res = cap.canonicalize("2079460000", Phone(country="GB"))
    assert res.status is Status.CANONICALIZED
    assert res.value == "+442079460000"
    assert res.evidence[0].rule == "cc_prepended"
    assert res.evidence[0].provenance  # non-empty Law 14 citation


def test_00_prefix_rejected():
    cap = PhoneCapability()
    res = cap.canonicalize("0016502530000", Phone(country="US"))
    assert res.status is Status.INVALID
    assert res.evidence[0].rule == "unrecognized_format"


def test_too_long_rejected():
    cap = PhoneCapability()
    res = cap.canonicalize("+165025300000000000", Phone(country="US"))
    assert res.status is Status.INVALID
    assert res.evidence[0].rule == "grammar_rejected"


def test_letters_rejected():
    cap = PhoneCapability()
    res = cap.canonicalize("call-me-now", Phone(country="US"))
    assert res.status is Status.INVALID
    assert res.evidence[0].rule == "unrecognized_format"


def test_leading_zero_cc_rejected():
    cap = PhoneCapability()
    res = cap.canonicalize("+06502530000", Phone(country="US"))
    assert res.status is Status.INVALID
    assert res.evidence[0].rule == "grammar_rejected"


def test_non_string_value():
    cap = PhoneCapability()
    res = cap.canonicalize(6502530000, CanonicalPhoneContract())
    assert res.status is Status.INVALID
    assert res.evidence[0].rule == "not_a_string_value"


def test_bare_national_with_country_policy():
    cap = PhoneCapability()
    res = cap.canonicalize("6502530000", CanonicalPhoneContract(country="US"))
    assert res.status is Status.CANONICALIZED
    assert res.value == "+16502530000"


def test_end_to_end_canonicalize():
    art = canonicalize("(650) 253-0000", Phone(country="US"))
    assert art.status is Status.CANONICALIZED
    assert art.value == "+16502530000"


def test_non_phone_contract_defensive():
    # Law 1 totality: capability must not crash on a wrong contract.
    cap = PhoneCapability()
    res = cap.canonicalize("+16502530000", object())
    assert res.status is Status.INVALID
    assert res.evidence[0].rule == "not_a_phone_contract"


def test_classify_surfaces_ambiguity():
    # Law 4: classifier must surface >1 distinct survivor as AMBIGUOUS.
    from paxman._capabilities.phone.canonicalizer import _Survivor, classify

    survivors = [
        _Survivor("+16502530000", "e164", "src", ()),
        _Survivor("+16502530001", "e164", "src", ()),
    ]
    status, value, _evidence, candidates = classify([object()], survivors, [])
    assert status is Status.AMBIGUOUS
    assert value is None
    assert set(candidates) == {"+16502530000", "+16502530001"}


def test_classify_collapses_identical_survivors():
    # Identical canonical strings are not ambiguous.
    from paxman._capabilities.phone.canonicalizer import _Survivor, classify

    survivors = [
        _Survivor("+16502530000", "e164", "src", ()),
        _Survivor("+16502530000", "national", "src", ()),
    ]
    status, value, _evidence, candidates = classify([object()], survivors, [])
    assert status is Status.CANONICALIZED
    assert value == "+16502530000"
    assert candidates is None
