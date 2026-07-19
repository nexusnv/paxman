from __future__ import annotations

from paxman._capabilities._shared.evidence import make_evidence, make_evidence_for
from paxman._provenance import Authority
from paxman._provenance import registries as R


def _stub_engine(authority_name: str, section_version: str) -> object:
    class _StubAuthority:
        def section(self, version: str) -> Authority:
            return Authority(name=authority_name, edition="2024", version=version)

    class _StubEngine:
        def authority(self, name: str) -> _StubAuthority:
            assert name == authority_name
            return _StubAuthority()

    return _StubEngine()


def test_make_evidence_resolves_from_manifest():
    manifest = {"ok_rule": R.RFC_4122.section("§3"), "none_rule": None}
    ev = make_evidence(manifest)
    e = ev("ok_rule")
    assert e.rule == "ok_rule"
    assert e.authority == R.RFC_4122.section("§3")
    # dispatch-invariant allow-list
    e2 = ev("none_rule")
    assert e2.authority is None


def test_make_evidence_missing_rule_raises_keyerror():
    ev = make_evidence({"ok_rule": R.RFC_4122.section("§3")})
    try:
        ev("unknown_rule")
    except KeyError:
        pass
    else:
        raise AssertionError("expected KeyError for unmanifested rule")


def test_make_evidence_for_reresolves_registry_rules_via_engine():
    authority_name = "ISO 3166-1"
    registry_rules = frozenset({"recognized_alpha2", "unrecognized_format"})
    base = R.ISO_3166.section("alpha-2 shape")
    manifest = {
        "recognized_alpha2": base,
        "unrecognized_format": R.ISO_3166.section("input not recognized"),
    }
    ev = make_evidence_for(manifest, authority_name, registry_rules)
    engine = _stub_engine(authority_name, "alpha-2 shape")
    # Without engine, uses the manifest authority verbatim.
    assert ev("recognized_alpha2").authority == base
    # With engine, the registry rule re-resolves against the engine edition.
    resolved = ev("recognized_alpha2", engine=engine)
    assert resolved.authority.name == authority_name
    assert resolved.authority.version == "alpha-2 shape"
    # A non-registry rule is untouched even when an engine is passed.
    assert ev("unrecognized_format", engine=engine).authority.name == "ISO 3166-1"


def test_make_evidence_for_unrecognized_format_resolves_via_engine():
    authority_name = "ISO 3166-1"
    registry_rules = frozenset({"unrecognized_format"})
    manifest = {"unrecognized_format": R.ISO_3166.section("input not recognized")}
    ev = make_evidence_for(manifest, authority_name, registry_rules)
    engine = _stub_engine(authority_name, "input not recognized")
    resolved = ev("unrecognized_format", engine=engine)
    # The unrecognized_format narrative is re-resolved against the engine edition.
    assert resolved.authority.name == authority_name
    assert resolved.authority.version == "input not recognized"


def test_make_evidence_for_default_registry_rules_is_noop_with_engine():
    authority_name = "ISO 3166-1"
    manifest = {"recognized_alpha2": R.ISO_3166.section("alpha-2 shape")}
    # registry_rules defaults to None → empty frozenset → engine is a no-op.
    ev = make_evidence_for(manifest, authority_name)
    engine = _stub_engine(authority_name, "alpha-2 shape")
    assert ev("recognized_alpha2", engine=engine).authority == manifest["recognized_alpha2"]
