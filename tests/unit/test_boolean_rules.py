"""Law 14 rule→authority manifest audit for the boolean capability."""

from __future__ import annotations

from paxman._capabilities.boolean.rules import _RULE_AUTHORITIES

_DISPATCH_INVARIANTS = frozenset({"not_a_boolean_contract", "not_a_string_value"})


def test_every_manifest_entry_beyond_dispatch_has_authority() -> None:
    for rule_name, authority in _RULE_AUTHORITIES.items():
        if rule_name in _DISPATCH_INVARIANTS:
            continue
        assert authority is not None, f"Law 14 violation: {rule_name!r} empty authority"


def test_dispatch_invariants_allow_listed_with_empty_authority() -> None:
    for invariant in _DISPATCH_INVARIANTS:
        assert invariant in _RULE_AUTHORITIES
        assert _RULE_AUTHORITIES[invariant] is None
