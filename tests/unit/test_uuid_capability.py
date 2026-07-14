"""Tests for the UUIDCapability.

These tests assert the v2.0.0 default behaviour:
- The capability accepts ONLY the RFC 4122 §3 canonical 36-char form.
- Alternative surface forms (32-hex, braced, URN, uppercase, padded)
  are rejected with `Status.INVALID` + the `not_canonical_form` rule.
- The version policy filters by UUID version with `version_mismatch`.
- Idempotent (mandate Law 2): a canonical input returns itself.
- Pure function (mandate Law 8a).
- Every Evidence rule carries a Law 14 provenance citation (except the
  two dispatch invariants).
"""

from __future__ import annotations

from typing import cast

from paxman import Status
from paxman._capabilities.builtins.uuid import _RULE_PROVENANCE, UUIDCapability
from paxman._contracts.contract import CanonicalUUIDContract, Contract

V4_CANONICAL = "550e8400-e29b-41d4-a716-446655440000"  # index 14 char = '4'
V1_CANONICAL = "e034b584-7d89-11ed-a1eb-0242ac120002"  # index 14 char = '1'


def _cap() -> UUIDCapability:
    return UUIDCapability()


def _contract(version: str = "any") -> CanonicalUUIDContract:
    return CanonicalUUIDContract(version=version)


class TestUUIDCapability:
    def test_name_is_uuid_canonicalization(self) -> None:
        assert _cap().name == "uuid_canonicalization"

    def test_can_handle_accepts_uuid_contract_and_string(self) -> None:
        c = _cap()
        assert c.can_handle(_contract(), V4_CANONICAL) is True

    def test_can_handle_rejects_non_uuid_contract(self) -> None:
        c = _cap()
        assert c.can_handle(cast(Contract, "not a contract"), V4_CANONICAL) is False

    def test_can_handle_rejects_non_string_value(self) -> None:
        c = _cap()
        assert c.can_handle(_contract(), cast(str, 12345)) is False

    def test_canonicalize_on_canonical_input_returns_canonical(self) -> None:
        c = _cap()
        r = c.canonicalize(V4_CANONICAL, _contract())
        assert r.status is Status.CANONICALIZED
        assert r.value == V4_CANONICAL
        assert len(r.evidence) == 1
        assert r.evidence[0].rule == "no_transformation_needed"

    def test_canonicalize_rejects_32_hex_no_hyphens(self) -> None:
        c = _cap()
        r = c.canonicalize("550e8400e29b41d4a716446655440000", _contract())
        assert r.status is Status.INVALID
        assert r.evidence[0].rule == "not_canonical_form"

    def test_canonicalize_rejects_braced_form(self) -> None:
        c = _cap()
        r = c.canonicalize("{550e8400-e29b-41d4-a716-446655440000}", _contract())
        assert r.status is Status.INVALID
        assert r.evidence[0].rule == "not_canonical_form"

    def test_canonicalize_rejects_urn_form(self) -> None:
        c = _cap()
        r = c.canonicalize("urn:uuid:550e8400-e29b-41d4-a716-446655440000", _contract())
        assert r.status is Status.INVALID
        assert r.evidence[0].rule == "not_canonical_form"

    def test_canonicalize_rejects_uppercase(self) -> None:
        c = _cap()
        r = c.canonicalize("550E8400-E29B-41D4-A716-446655440000", _contract())
        assert r.status is Status.INVALID
        assert r.evidence[0].rule == "not_canonical_form"

    def test_canonicalize_rejects_extra_whitespace(self) -> None:
        c = _cap()
        r = c.canonicalize(" 550e8400-e29b-41d4-a716-446655440000 ", _contract())
        assert r.status is Status.INVALID
        assert r.evidence[0].rule == "not_canonical_form"

    def test_canonicalize_rejects_version_mismatch(self) -> None:
        c = _cap()
        r = c.canonicalize(V1_CANONICAL, _contract(version="4"))
        assert r.status is Status.INVALID
        assert r.evidence[0].rule == "version_mismatch"

    def test_canonicalize_version_filter_accepts_matching(self) -> None:
        c = _cap()
        r = c.canonicalize(V4_CANONICAL, _contract(version="4"))
        assert r.status is Status.CANONICALIZED

    def test_canonicalize_rejects_non_uuid_contract(self) -> None:
        c = _cap()
        r = c.canonicalize(V4_CANONICAL, cast(Contract, "not a contract"))
        assert r.status is Status.INVALID
        assert r.evidence[0].rule == "not_a_uuid_contract"

    def test_canonicalize_rejects_non_string_value(self) -> None:
        c = _cap()
        r = c.canonicalize(cast(str, 12345), _contract())
        assert r.status is Status.INVALID
        assert r.evidence[0].rule == "not_a_string_value"

    def test_canonicalize_rejects_non_hex_character(self) -> None:
        """Spec §9.1 case #11: a 36-char string with a non-hex character
        (e.g. a trailing 'Z') is INVALID with not_canonical_form, even
        though its length and hyphen positions are otherwise canonical."""
        c = _cap()
        non_hex = "00000000-0000-0000-0000-00000000000Z"
        result = c.canonicalize(non_hex, _contract())
        assert result.status is Status.INVALID
        assert result.evidence[0].rule == "not_canonical_form"

    def test_every_evidence_rule_has_provenance_in_manifest(self) -> None:
        c = _cap()
        inputs: list[tuple[object, Contract]] = [
            (V4_CANONICAL, _contract()),
            ("550e8400e29b41d4a716446655440000", _contract()),
            ("{550e8400-e29b-41d4-a716-446655440000}", _contract()),
            ("urn:uuid:550e8400-e29b-41d4-a716-446655440000", _contract()),
            ("550E8400-E29B-41D4-A716-446655440000", _contract()),
            (" 550e8400-e29b-41d4-a716-446655440000 ", _contract()),
            (V1_CANONICAL, _contract(version="4")),
            (12345, _contract()),
            (V4_CANONICAL, cast(Contract, "not a contract")),
        ]
        fired: set[str] = set()
        for value, contract in inputs:
            r = c.canonicalize(value, contract)
            for ev in r.evidence:
                fired.add(ev.rule)
        dispatch_invariants = {"not_a_uuid_contract", "not_a_string_value"}
        for rule in fired:
            assert rule in _RULE_PROVENANCE, f"fired rule {rule!r} missing from manifest"
        for rule_name, provenance in _RULE_PROVENANCE.items():
            if rule_name in dispatch_invariants:
                assert provenance == "", f"dispatch invariant {rule_name!r} must be empty"
                continue
            assert provenance != "", f"Law 14 violation: rule {rule_name!r} has empty provenance"
