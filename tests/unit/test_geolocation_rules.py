"""Law 14 rule→provenance manifest audit for the geolocation capability."""

from __future__ import annotations

from paxman._capabilities.geolocation.canonicalizer import GeolocationCapability
from paxman._capabilities.geolocation.contract import Geolocation
from paxman._capabilities.geolocation.rules import _RULE_PROVENANCE, _evidence
from paxman._core.provenance import Evidence

_DISPATCH_INVARIANTS = frozenset({"not_a_geolocation_contract", "not_a_string_value"})


def test_every_manifest_entry_beyond_dispatch_has_provenance() -> None:
    for rule_name, provenance in _RULE_PROVENANCE.items():
        if rule_name in _DISPATCH_INVARIANTS:
            continue
        assert provenance != "", f"Law 14 violation: {rule_name!r} empty provenance"


def test_dispatch_invariants_allow_listed_with_empty_provenance() -> None:
    for invariant in _DISPATCH_INVARIANTS:
        assert invariant in _RULE_PROVENANCE
        assert _RULE_PROVENANCE[invariant] == ""


def test_evidence_provenance_matches_manifest() -> None:
    ev = _evidence("canonicalized_geolocation", "40.7128N 74.0060W -> 40.712800,-74.006000")
    assert isinstance(ev, Evidence)
    assert ev.rule == "canonicalized_geolocation"
    assert ev.provenance == _RULE_PROVENANCE["canonicalized_geolocation"]
    assert ev.provenance != ""


def test_manifest_keys_cover_every_fired_rule() -> None:
    c = GeolocationCapability()
    contract = Geolocation()
    inputs = [
        ("40.7128N 74.0060W", contract),
        ("40°42'46\"N 74°0'21\"W", contract),
        ("40.7128, -74.0060", contract),
        ("40.7128, 74.0060", contract),
        ("40.7128, 74.0060", Geolocation(require_hemisphere=False)),
        ("91.0, 0.0", contract),
        ("abc", contract),
        ("", contract),
        (None, contract),
        ("40.7128N 74.0060W", Geolocation(coordinate_order="lon_lat")),
    ]
    fired: set[str] = set()
    for value, contract in inputs:
        r = c.canonicalize(value, contract)
        for ev in r.evidence:
            fired.add(ev.rule)
    not_contract = "not_a_contract"
    r1 = c.canonicalize("40.7128N 74.0060W", not_contract)  # type: ignore[arg-type]
    for ev in r1.evidence:
        fired.add(ev.rule)
    for rule in fired:
        assert rule in _RULE_PROVENANCE, f"fired rule {rule!r} missing from manifest"
