"""Tests for the CountryCapability canonicalizer."""

from __future__ import annotations

from paxman import Country, canonicalize
from paxman._core.status import Status


def test_alpha2_passthrough() -> None:
    r = canonicalize("US", Country())
    assert r.status == Status.CANONICALIZED
    assert r.value == "US"


def test_alpha2_case_fold() -> None:
    r = canonicalize("us", Country())
    assert r.status == Status.CANONICALIZED
    assert r.value == "US"


def test_alpha3_to_alpha2() -> None:
    r = canonicalize("USA", Country())
    assert r.status == Status.CANONICALIZED
    assert r.value == "US"


def test_name_to_alpha2() -> None:
    r = canonicalize("United States", Country())
    assert r.status == Status.CANONICALIZED
    assert r.value == "US"


def test_synonym_uk_to_gb() -> None:
    r = canonicalize("UK", Country())
    assert r.status == Status.CANONICALIZED
    assert r.value == "GB"


def test_synonym_america() -> None:
    r = canonicalize("America", Country())
    assert r.status == Status.CANONICALIZED
    assert r.value == "US"


def test_extra_synonyms_honored() -> None:
    r = canonicalize("Freedonia", Country(extra_synonyms={"freedonia": "US"}))
    assert r.status == Status.CANONICALIZED
    assert r.value == "US"


def test_policy_disabled_alpha3() -> None:
    r = canonicalize("USA", Country(allow_alpha3=False))
    assert r.status == Status.INVALID


def test_missing_empty() -> None:
    r = canonicalize("", Country())
    assert r.status == Status.MISSING


def test_invalid_unrecognized() -> None:
    r = canonicalize("Atlantis", Country())
    assert r.status == Status.INVALID


def test_idempotent() -> None:
    r1 = canonicalize("United States", Country())
    r2 = canonicalize(r1.value, Country())
    assert r2.value == r1.value


def test_evidence_has_provenance() -> None:
    r = canonicalize("United States", Country())
    for ev in r.evidence:
        if ev.rule in ("not_a_country_contract", "not_a_string_value"):
            continue
        assert ev.provenance, f"rule {ev.rule!r} missing provenance"


def test_policy_disabled_name() -> None:
    r = canonicalize("United States", Country(allow_name=False))
    assert r.status == Status.INVALID


def test_policy_disabled_synonym() -> None:
    r = canonicalize("UK", Country(allow_synonym=False))
    assert r.status == Status.INVALID


def test_dispatch_invariants_direct() -> None:
    from paxman._capabilities.country.canonicalizer import CountryCapability

    cap = CountryCapability()
    not_contract = cap.canonicalize("US", object())
    assert not_contract.status == Status.INVALID
    assert not_contract.evidence[0].rule == "not_a_country_contract"
    not_str = cap.canonicalize(123, Country())  # type: ignore[arg-type]
    assert not_str.status == Status.INVALID
    assert not_str.evidence[0].rule == "not_a_string_value"


def test_classify_no_candidates_is_invalid() -> None:
    from paxman._capabilities.country.canonicalizer import classify

    status, _value, evidence, _cands = classify([], [], [])
    assert status == Status.INVALID
    assert evidence[0].rule == "unrecognized_format"


def test_resolver_duplicate_value_collapsed() -> None:
    from paxman._capabilities.country.canonicalizer import generate_interpretations
    from paxman._capabilities.country.grammar import recognize

    # "USA" resolves via both alpha-3 and the bundled synonym -> same code.
    reps = recognize("USA", Country())
    cands = generate_interpretations(reps, Country())
    assert len(cands) == 1
    assert cands[0].value == "US"
