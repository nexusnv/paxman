"""Tests for engine-pinned authority editions (Concern 3 — IoC).

The authority-edition SELECTION surface (`Engine.with_authorities`,
`Edition`, `canonicalize_with`, `ComplianceProfile`) was removed from the
public API. This file now exercises the internal carrier paths that remain:
the per-contract `authority_override` escape hatch (recorded on the artifact
and replay-deterministic) and `Engine.from_artifact` (which replay uses).
"""

from __future__ import annotations

import pytest

from paxman import Country, Email, Money, canonicalize, replay
from paxman._core.engine_env import Engine
from paxman._errors import UnknownAuthorityEdition
from paxman._provenance.authority import Authority


def _edition(authorities: tuple, name: str) -> str | None:
    for a in authorities:
        if a.name == name:
            return a.edition
    return None


def test_country_default_records_latest_iso3166() -> None:
    r = canonicalize("malaysia", Country(allow_name=True))
    assert _edition(r.authorities, "ISO 3166-1") == "2024"


def test_money_default_records_latest_iso4217() -> None:
    r = canonicalize("MYR 12.50", Money(currency="MYR", allow_code=True))
    assert _edition(r.authorities, "ISO 4217") == "iso4217:2015"


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


def test_engine_reads_authority_override_statically_with_override() -> None:
    # The engine must read authority_override as a typed attribute (not via
    # getattr), so a contract carrying a pin hits the override path and the
    # pinned edition is recorded rather than silently dropped.
    c = Country(allow_name=True, authority_override={"ISO 3166-1": "2024"})
    assert c.authority_override == {"ISO 3166-1": "2024"}
    r = canonicalize("malaysia", c)
    assert _edition(r.authorities, "ISO 3166-1") == "2024"


def test_engine_reads_authority_override_statically_without_override() -> None:
    # A contract with no pin exposes authority_override as None; the engine's
    # override block must be skipped and the default (latest) edition recorded.
    c = Country(allow_name=True)
    assert c.authority_override is None
    r = canonicalize("malaysia", c)
    assert _edition(r.authorities, "ISO 3166-1") == "2024"
