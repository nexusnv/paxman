"""Tests for engine-pinned authority editions (Concern 3 — IoC).

Paxman is pre-release: it bundles exactly the latest edition of each
multi-edition registry (ISO 3166-1:2024, ISO 4217:2015). Pinning a known
bundled edition records it in evidence and replays deterministically; pinning
an edition Paxman does not bundle (e.g. "2020") raises UnknownAuthorityEdition.
"""

from __future__ import annotations

import pytest

from paxman import Country, Email, Money, canonicalize, replay
from paxman._core.engine_env import Engine, canonicalize_with
from paxman._errors import UnknownAuthorityEdition
from paxman._provenance.authority import Authority
from paxman._provenance.selection import Edition


def _edition(authorities: tuple, name: str) -> str | None:
    for a in authorities:
        if a.name == name:
            return a.edition
    return None


def test_country_default_records_latest_iso3166() -> None:
    r = canonicalize("malaysia", Country(allow_name=True))
    assert _edition(r.authorities, "ISO 3166-1") == "2024"


def test_country_pinned_iso3166_edition_recorded() -> None:
    eng = Engine.with_authorities({"ISO 3166-1": Edition("2024")})
    r = canonicalize_with("malaysia", Country(allow_name=True), eng)
    assert r.status.value == "canonicalized"
    assert _edition(r.authorities, "ISO 3166-1") == "2024"
    # The evidence authority cites the pinned edition, not the latest.
    for ev in r.evidence:
        if ev.rule in {"canonicalized_country", "recognized_name"}:
            assert ev.authority is not None
            assert ev.authority.edition == "2024"


def test_country_pinned_replay_is_deterministic() -> None:
    eng = Engine.with_authorities({"ISO 3166-1": Edition("2024")})
    r = canonicalize_with("United States", Country(), eng)
    r2 = replay(r, Country())
    assert r2 == r
    assert _edition(r2.authorities, "ISO 3166-1") == "2024"


def test_country_pin_unknown_edition_rejected() -> None:
    # Paxman only bundles the latest edition (2024); older editions it has
    # never shipped (e.g. 2020) are unknown and must be rejected.
    with pytest.raises(UnknownAuthorityEdition):
        Engine.with_authorities({"ISO 3166-1": Edition("2020")})


def test_money_default_records_latest_iso4217() -> None:
    r = canonicalize("MYR 12.50", Money(currency="MYR", allow_code=True))
    assert _edition(r.authorities, "ISO 4217") == "iso4217:2015"


def test_money_pinned_iso4217_edition_recorded() -> None:
    eng = Engine.with_authorities({"ISO 4217": Edition("iso4217:2015")})
    r = canonicalize_with("MYR 12.50", Money(currency="MYR", allow_code=True), eng)
    assert r.status.value == "canonicalized"
    assert _edition(r.authorities, "ISO 4217") == "iso4217:2015"
    for ev in r.evidence:
        if ev.rule == "code_validated":
            assert ev.authority is not None
            assert ev.authority.edition == "iso4217:2015"


def test_money_pinned_replay_is_deterministic() -> None:
    eng = Engine.with_authorities({"ISO 4217": Edition("iso4217:2015")})
    r = canonicalize_with("MYR 12.50", Money(currency="MYR", allow_code=True), eng)
    r2 = replay(r, Money(currency="MYR", allow_code=True))
    assert r2 == r
    assert _edition(r2.authorities, "ISO 4217") == "iso4217:2015"


def test_contract_authority_override_pins_iso3166_for_single_call() -> None:
    # Escape hatch A: a contract can pin an edition for one canonicalize call
    # without constructing an explicit Engine.
    c = Country(allow_name=True, authority_override={"ISO 3166-1": "2024"})
    r = canonicalize("malaysia", c)
    assert _edition(r.authorities, "ISO 3166-1") == "2024"
    # The same pin must survive replay (artifact records the edition).
    r2 = replay(r, c)
    assert r2 == r
    assert _edition(r2.authorities, "ISO 3166-1") == "2024"


def test_contract_authority_override_pinned_replay_is_deterministic() -> None:
    c = Money(currency="MYR", allow_code=True, authority_override={"ISO 4217": "iso4217:2015"})
    r = canonicalize("MYR 12.50", c)
    assert _edition(r.authorities, "ISO 4217") == "iso4217:2015"
    r2 = replay(r, c)
    assert r2 == r


def test_contract_authority_override_dict_dsl_path() -> None:
    c = {
        "kind": "canonical_country",
        "allow_name": True,
        "authority_override": {"ISO 3166-1": "2024"},
    }
    r = canonicalize("malaysia", c)
    assert _edition(r.authorities, "ISO 3166-1") == "2024"


def test_contract_authority_override_rejects_grammar_edition() -> None:
    # Grammars carry a single edition; a non-default pin must be rejected.
    with pytest.raises(UnknownAuthorityEdition):
        canonicalize("A@B.COM", Email(authority_override={"RFC 5321": "2008"}))


def test_default_contract_records_latest_without_override() -> None:
    r = canonicalize("malaysia", Country(allow_name=True))
    assert _edition(r.authorities, "ISO 3166-1") == "2024"


def test_from_artifact_merges_over_default_roster() -> None:
    # An artifact that fired only grammar rules records no registry authority.
    # from_artifact must still seed the full active roster so a later registry
    # lookup resolves to the active edition rather than silently falling back.
    partial = (Authority(name="RFC 5321", edition="5321", kind="grammar"),)
    eng = Engine.from_artifact(partial)
    # registry authority present and bound to its active edition
    assert eng.authority("ISO 3166-1").edition == "2024"
    # the recorded grammar authority is preserved verbatim
    assert eng.authority("RFC 5321").edition == "5321"
    # unknown name still raises
    with pytest.raises(UnknownAuthorityEdition):
        eng.authority("nope")


def test_compliance_profile_builds_pinned_engine() -> None:
    # ComplianceProfile.engine() delegates to Engine.with_authorities,
    # pinning the adopted edition over the active roster.
    from paxman._core.engine_env import ComplianceProfile

    profile = ComplianceProfile({"ISO 3166-1": Edition("2024")})
    eng = profile.engine()
    assert isinstance(eng, Engine)
    assert eng.authority("ISO 3166-1").edition == "2024"
    # unpinned authorities still resolve to their active edition
    assert eng.authority("ISO 4217").edition == "iso4217:2015"
