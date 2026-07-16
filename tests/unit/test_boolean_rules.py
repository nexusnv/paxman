"""Law 14 rule→provenance manifest audit for the boolean capability."""

from __future__ import annotations

from paxman._capabilities.boolean.rules import _RULE_PROVENANCE

_DISPATCH_INVARIANTS = frozenset({"not_a_boolean_contract", "not_a_string_value"})


def test_every_manifest_entry_beyond_dispatch_has_provenance() -> None:
    for rule_name, provenance in _RULE_PROVENANCE.items():
        if rule_name in _DISPATCH_INVARIANTS:
            continue
        assert provenance != "", f"Law 14 violation: {rule_name!r} empty provenance"


def test_dispatch_invariants_allow_listed_with_empty_provenance() -> None:
    for invariant in _DISPATCH_INVARIANTS:
        assert invariant in _RULE_PROVENANCE
        assert _RULE_PROVENANCE[invariant] == ""
