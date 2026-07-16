"""Tests for the BooleanCapability (four-stage canonicalization)."""

from __future__ import annotations

from typing import Any, cast

from paxman._capabilities.boolean import _RULE_PROVENANCE, BooleanCapability
from paxman._capabilities.boolean.contract import CanonicalBooleanContract
from paxman._core.contracts import Contract
from paxman._core.status import Status


def _cap() -> BooleanCapability:
    return BooleanCapability()


def _contract(**kw: object) -> CanonicalBooleanContract:
    base: dict[str, object] = dict(accept_numeric=True, accept_words=True, case_sensitive=False)
    base.update(kw)
    return CanonicalBooleanContract(**cast(Any, base))


class TestBooleanCapability:
    def test_capability_metadata(self) -> None:
        assert _cap().name == "boolean_canonicalization"

    def test_can_handle_matches_boolean_contract(self) -> None:
        assert _cap().can_handle(_contract(), "true") is True

    def test_can_handle_accepts_none_and_str(self) -> None:
        assert _cap().can_handle(_contract(), None) is True
        assert _cap().can_handle(_contract(), "true") is True

    def test_can_handle_rejects_non_str_non_none(self) -> None:
        assert _cap().can_handle(_contract(), 1) is False

    def test_can_handle_rejects_non_boolean_contract(self) -> None:
        assert _cap().can_handle(cast(Contract, "nope"), "true") is False

    def test_word_true(self) -> None:
        r = _cap().canonicalize("true", _contract())
        assert r.status is Status.CANONICALIZED and r.value == "true"

    def test_word_case_insensitive(self) -> None:
        r = _cap().canonicalize("YES", _contract())
        assert r.status is Status.CANONICALIZED and r.value == "true"

    def test_y_alias(self) -> None:
        assert _cap().canonicalize("y", _contract()).value == "true"

    def test_numeric_true(self) -> None:
        assert _cap().canonicalize("1", _contract()).value == "true"

    def test_word_false(self) -> None:
        assert _cap().canonicalize("No", _contract()).value == "false"

    def test_numeric_false(self) -> None:
        assert _cap().canonicalize("0", _contract()).value == "false"

    def test_on_off(self) -> None:
        assert _cap().canonicalize("on", _contract()).value == "true"
        assert _cap().canonicalize("off", _contract()).value == "false"

    def test_enabled_disabled(self) -> None:
        assert _cap().canonicalize("enabled", _contract()).value == "true"
        assert _cap().canonicalize("disabled", _contract()).value == "false"

    def test_case_sensitive_rejects_upper(self) -> None:
        r = _cap().canonicalize("TRUE", _contract(case_sensitive=True))
        assert r.status is Status.INVALID

    def test_accept_numeric_false_rejects_one(self) -> None:
        r = _cap().canonicalize("1", _contract(accept_numeric=False))
        assert r.status is Status.INVALID
        assert "policy_disabled_token" in {e.rule for e in r.evidence}

    def test_accept_words_false_rejects_yes(self) -> None:
        r = _cap().canonicalize("yes", _contract(accept_words=False))
        assert r.status is Status.INVALID

    def test_whitespace_is_trimmed(self) -> None:
        r = _cap().canonicalize("  yes  ", _contract())
        assert r.status is Status.CANONICALIZED and r.value == "true"
        assert "trimmed_whitespace" in {e.rule for e in r.evidence}

    def test_empty_string_is_missing(self) -> None:
        assert _cap().canonicalize("", _contract()).status is Status.MISSING

    def test_none_is_missing(self) -> None:
        assert _cap().canonicalize(None, _contract()).status is Status.MISSING

    def test_unknown_token_is_invalid(self) -> None:
        r = _cap().canonicalize("maybe", _contract())
        assert r.status is Status.INVALID
        assert "unrecognized_token" in {e.rule for e in r.evidence}

    def test_idempotence(self) -> None:
        once = _cap().canonicalize("  Yes  ", _contract())
        assert once.status is Status.CANONICALIZED
        twice = _cap().canonicalize(once.value, _contract())
        assert twice.value == once.value


class TestLaw14ProvenanceManifest:
    _DISPATCH_INVARIANTS = frozenset({"not_a_boolean_contract", "not_a_string_value"})

    def test_every_manifest_entry_beyond_dispatch_has_provenance(self) -> None:
        for rule, prov in _RULE_PROVENANCE.items():
            if rule in self._DISPATCH_INVARIANTS:
                continue
            assert prov != ""

    def test_dispatch_invariants_allow_listed(self) -> None:
        for inv in self._DISPATCH_INVARIANTS:
            assert inv in _RULE_PROVENANCE and _RULE_PROVENANCE[inv] == ""

    def test_manifest_keys_cover_every_fired_rule(self) -> None:
        c = _cap()
        contract = _contract()
        inputs: list[tuple[object, Contract]] = [
            ("Yes", contract),
            ("  NO  ", contract),
            ("1", contract),
            ("0", contract),
            ("TRUE", _contract(case_sensitive=True)),
            ("maybe", contract),
            ("", contract),
            (None, contract),
            ("1", _contract(accept_numeric=False)),
            ("yes", _contract(accept_words=False)),
        ]
        fired: set[str] = set()
        for value, contract in inputs:
            r = c.canonicalize(value, contract)
            for ev in r.evidence:
                fired.add(ev.rule)
        not_contract: Contract = cast(Contract, "not_a_contract")
        r1 = c.canonicalize("true", not_contract)
        for ev in r1.evidence:
            fired.add(ev.rule)
        for rule in fired:
            assert rule in _RULE_PROVENANCE, f"fired rule {rule!r} missing from manifest"
