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


# --- Expansion tiers (T1 numeric, T2 expanded aliases, T3 CLDR, T4 historical) ---


def test_numeric_padded() -> None:
    r = canonicalize("840", Country())
    assert r.status == Status.CANONICALIZED
    assert r.value == "US"


def test_numeric_unpadded() -> None:
    r = canonicalize("4", Country())
    assert r.status == Status.CANONICALIZED
    assert r.value == "AF"


def test_numeric_disabled() -> None:
    r = canonicalize("840", Country(allow_numeric=False))
    assert r.status == Status.INVALID


def test_numeric_unknown() -> None:
    # A 3-digit number that is not an ISO 3166-1 code.
    r = canonicalize("123", Country())
    assert r.status == Status.INVALID


def test_full_alpha3() -> None:
    # Spot-check codes across the expanded 249-entry table.
    for a3, a2 in (("DEU", "DE"), ("ZWE", "ZW"), ("CZE", "CZ"), ("MMR", "MM")):
        r = canonicalize(a3, Country())
        assert r.status == Status.CANONICALIZED
        assert r.value == a2


def test_expanded_synonym() -> None:
    r = canonicalize("Republic of Korea", Country())
    assert r.status == Status.CANONICALIZED
    assert r.value == "KR"
    r = canonicalize("Russian Federation", Country())
    assert r.status == Status.CANONICALIZED
    assert r.value == "RU"


def test_localized_names_opt_in() -> None:
    # Off by default -> native-script token is not recognized.
    r = canonicalize("日本", Country())
    assert r.status == Status.INVALID
    r = canonicalize("日本", Country(localized_names=True))
    assert r.status == Status.CANONICALIZED
    assert r.value == "JP"
    r = canonicalize("ماليزيا", Country(localized_names=True))
    assert r.status == Status.CANONICALIZED
    assert r.value == "MY"


def test_historical_names_opt_in() -> None:
    r = canonicalize("Burma", Country())
    assert r.status == Status.INVALID
    r = canonicalize("Burma", Country(historical_names=True))
    assert r.status == Status.CANONICALIZED
    assert r.value == "MM"
    r = canonicalize("Swaziland", Country(historical_names=True))
    assert r.status == Status.CANONICALIZED
    assert r.value == "SZ"


def test_evidence_has_provenance_expanded() -> None:
    for val, ctor in (
        ("840", Country()),
        ("日本", Country(localized_names=True)),
        ("Burma", Country(historical_names=True)),
    ):
        r = canonicalize(val, ctor)
        for ev in r.evidence:
            assert ev.provenance, f"rule {ev.rule!r} missing provenance"


# --- Law 15: cited named-entity source (ISO 3166-1:2020) adopted in full ---


def test_full_iso3166_name_coverage() -> None:
    # Every officially assigned alpha-2 code's ISO 3166-1:2020 short name
    # must canonicalize (Law 15 — the cited enumeration is adopted in full).
    from paxman._capabilities.country.contract import (
        _ALPHA2_CODES,
        _NAME_TO_ALPHA2,
    )

    # The table maps every assigned code to its alpha-2 (some codes appear
    # under multiple keys, e.g. prior convenience aliases; the value set is
    # what must cover the assigned codes).
    covered = set(_NAME_TO_ALPHA2.values())
    assert covered >= _ALPHA2_CODES
    for code in sorted(_ALPHA2_CODES):
        # Find the official-name key for this code (first match).
        official = next(k for k, v in _NAME_TO_ALPHA2.items() if v == code)
        r = canonicalize(official.title(), Country())
        assert r.status == Status.CANONICALIZED, f"{official} -> {r.status}"
        assert r.value == code


def test_iso3166_long_official_forms() -> None:
    # Long/constitutional official names that a curated subset would omit.
    cases = {
        "United Kingdom of Great Britain and Northern Ireland": "GB",
        "Iran (Islamic Republic of)": "IR",
        "Bolivia (Plurinational State of)": "BO",
        "Venezuela (Bolivarian Republic of)": "VE",
        "Korea (Democratic People's Republic of)": "KP",
        "Lao People's Democratic Republic": "LA",
        "United States of America": "US",
        "Côte d'Ivoire": "CI",
        "Réunion": "RE",
        "Åland Islands": "AX",
        "Curaçao": "CW",
        "Sint Maarten (Dutch part)": "SX",
    }
    for name, code in cases.items():
        r = canonicalize(name, Country())
        assert r.status == Status.CANONICALIZED, f"{name} -> {r.status}"
        assert r.value == code


def test_prior_convenience_aliases_retained() -> None:
    # Backward-compatible short aliases kept alongside the full enumeration.
    for name, code in (
        ("United States", "US"),
        ("South Korea", "KR"),
        ("Russia", "RU"),
        ("Great Britain", "GB"),
        ("Czech Republic", "CZ"),
    ):
        r = canonicalize(name, Country())
        assert r.status == Status.CANONICALIZED
        assert r.value == code
