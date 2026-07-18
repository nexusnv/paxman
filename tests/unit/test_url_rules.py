import pytest

from paxman._capabilities.url.rules import _RULE_AUTHORITIES, _evidence

# Mandate laws touched (Law 9 evidence-over-confidence; Law 14 provenance —
# every rule in the manifest must cite an authority). These tests pin the
# rule manifest (core + WHATWG) and that each cited rule carries a
# non-empty authority.


def test_manifest_has_core_rules():
    for rule in (
        "lowercase_scheme",
        "uppercase_pct_hex",
        "lowercase_host",
        "decode_unreserved_pct",
        "keep_reserved_pct",
        "elide_default_port",
        "remove_dot_segments",
        "empty_path_to_slash",
        "strip_userinfo",
        "strip_fragment",
        "sort_query",
        "no_transformation_needed",
        "unrecognized_format",
        "grammar_rejected",
        "scheme_not_allowed",
    ):
        assert rule in _RULE_AUTHORITIES, f"missing citation for {rule}"
        assert _RULE_AUTHORITIES[rule], f"empty citation for {rule}"


def test_whatwg_rules_present():
    for rule in (
        "whatwg_trailing_dot_host",
        "whatwg_pct_dot_in_path",
        "whatwg_infinite_slashes",
        "whatwg_backslash_coerce",
    ):
        assert rule in _RULE_AUTHORITIES
        assert _RULE_AUTHORITIES[rule], f"empty citation for {rule}"


def test_evidence_pulls_provenance():
    ev = _evidence("lowercase_scheme")
    assert ev.rule == "lowercase_scheme"
    assert ev.authority is not None and "RFC 3986" in ev.authority.name


def test_unknown_rule_raises():
    with pytest.raises(KeyError):
        _evidence("not_a_real_rule")
