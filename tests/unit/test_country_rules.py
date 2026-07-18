"""Static audit of the country Law 14 rule->provenance manifest."""

from __future__ import annotations

from paxman._capabilities.country import _RULE_AUTHORITIES


def test_all_rules_have_nonempty_provenance() -> None:
    # Law 14 §838: a rule with an empty authority is a violation.
    # No rule — including dispatch invariants — may use None.
    for rule, authority in _RULE_AUTHORITIES.items():
        assert authority is not None, f"rule {rule!r} has empty authority (Law 14 §838)"


def test_dispatch_invariants_cite_mandate() -> None:
    assert (
        _RULE_AUTHORITIES["not_a_country_contract"] is not None
        and _RULE_AUTHORITIES["not_a_country_contract"].name == "MANDATE.md"
    )
    assert (
        _RULE_AUTHORITIES["not_a_string_value"] is not None
        and _RULE_AUTHORITIES["not_a_string_value"].name == "MANDATE.md"
    )


def test_policy_rules_reference_recorded_policy_constants() -> None:
    # Paxman-defined policy authority must resolve to kind "policy",
    # so amendments are traceable.
    assert (
        _RULE_AUTHORITIES["trimmed_whitespace"] is not None
        and _RULE_AUTHORITIES["trimmed_whitespace"].kind == "policy"
    )
    assert (
        _RULE_AUTHORITIES["extra_synonym_resolved"] is not None
        and _RULE_AUTHORITIES["extra_synonym_resolved"].kind == "policy"
    )
    assert (
        _RULE_AUTHORITIES["policy_disabled_kind"] is not None
        and _RULE_AUTHORITIES["policy_disabled_kind"].kind == "policy"
    )
    assert (
        _RULE_AUTHORITIES["missing_value"] is not None
        and _RULE_AUTHORITIES["missing_value"].kind == "policy"
    )


def test_required_rules_present() -> None:
    required = {
        "not_a_country_contract",
        "not_a_string_value",
        "trimmed_whitespace",
        "recognized_alpha2",
        "recognized_alpha3",
        "recognized_name",
        "canonicalized_country",
        "alias_resolved",
        "extra_synonym_resolved",
        "policy_disabled_kind",
        "missing_value",
        "unrecognized_format",
    }
    assert required <= set(_RULE_AUTHORITIES)
