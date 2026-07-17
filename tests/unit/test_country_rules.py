"""Static audit of the country Law 14 rule->provenance manifest."""

from __future__ import annotations

from paxman._capabilities.country import _RULE_PROVENANCE
from paxman._capabilities.country.policy import (
    COUNTRY_POLICY_EXTRA_SYNONYMS,
    COUNTRY_POLICY_KIND_GATING,
    COUNTRY_POLICY_MISSING_VALUE,
    COUNTRY_POLICY_WHITESPACE_TRIM,
)


def test_all_rules_have_nonempty_provenance() -> None:
    # Law 14 §838: a rule with an empty provenance string is a violation.
    # No rule — including dispatch invariants — may use "".
    for rule, provenance in _RULE_PROVENANCE.items():
        assert provenance, f"rule {rule!r} has empty provenance (Law 14 §838)"


def test_dispatch_invariants_cite_mandate() -> None:
    assert _RULE_PROVENANCE["not_a_country_contract"].startswith("MANDATE.md §5.1")
    assert _RULE_PROVENANCE["not_a_string_value"].startswith("MANDATE.md §5.1")


def test_policy_rules_reference_recorded_policy_constants() -> None:
    # Paxman-defined policy provenance must resolve to a recorded constant
    # in policy.py (not an inline string), so amendments are traceable.
    assert _RULE_PROVENANCE["trimmed_whitespace"] == COUNTRY_POLICY_WHITESPACE_TRIM
    assert _RULE_PROVENANCE["extra_synonym_resolved"] == COUNTRY_POLICY_EXTRA_SYNONYMS
    assert _RULE_PROVENANCE["policy_disabled_kind"] == COUNTRY_POLICY_KIND_GATING
    assert _RULE_PROVENANCE["missing_value"] == COUNTRY_POLICY_MISSING_VALUE


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
    assert required <= set(_RULE_PROVENANCE)
