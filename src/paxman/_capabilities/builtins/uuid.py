"""UUIDCapability: the second built-in capability of Paxman v2.

Mandate alignment:
- Law 4: rewrites known representations (RFC 4122 canonical form).
- Law 5: the contract declares the policy; the capability applies it.
- Law 7: explicit over clever. The capability accepts only the
  canonical 36-char form. Alternative surface forms (32-hex, braced,
  URN) are `INVALID` per the spec.
- Law 8a: pure function of (value, contract). No network, no time,
  no randomness, no filesystem.
- Law 11: SPI litmus. Two independent implementations must produce
  the same canonical form for the same input.
- Law 14: every rule cites a source. The rule→citation manifest is
  `_RULE_PROVENANCE`; `Evidence.provenance` is populated from it.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from paxman._contracts.contract import CanonicalUUIDContract, Contract
from paxman._core.types import CapabilityResult, Evidence, Status

# The canonical form has 36 chars total: 32 hex + 4 hyphens at positions
# 8, 13, 18, 23 (counting from 0). The first hex digit of the third
# group is the version-nibble (RFC 4122 §4.1.3).
CANONICAL_LENGTH = 36
HYPHEN_POSITIONS = frozenset({8, 13, 18, 23})
CANONICAL_CHARS = frozenset("0123456789abcdef-")


_RULE_PROVENANCE: Mapping[str, str] = MappingProxyType(
    {
        # --- dispatch invariants (no provenance — Law 14 allow-list) ---
        "not_a_uuid_contract": "",
        "not_a_string_value": "",
        # --- rejecting rules (authoritative spec) ---
        "not_canonical_form": (
            "RFC 4122 §3 (the canonical form is 36 chars; 8-4-4-4-12 grouping; lowercase hex)"
        ),
        "version_mismatch": "RFC 4122 §4.1.3 (version field encoding)",
        # --- transforming rule (success path) ---
        "no_transformation_needed": "RFC 4122 §3 (the canonical form is X; X was provided)",
    }
)


def _evidence(rule: str, detail: str = "") -> Evidence:
    """Build an `Evidence` pulling the Law 14 provenance citation from
    the `_RULE_PROVENANCE` manifest.

    A rule with no manifest entry raises `KeyError`, surfacing a
    missing citation at the exact site where the rule is emitted.
    """
    return Evidence(rule=rule, detail=detail, provenance=_RULE_PROVENANCE[rule])


class UUIDCapability:
    """A pure deterministic transformation that canonicalizes UUIDs.

    The capability accepts only the RFC 4122 §3 canonical form (36
    lowercase hex chars, 8-4-4-4-12). Inputs in any other form
    (32-hex without hyphens, braced, URN, uppercase, with extra
    whitespace) are `Status.INVALID` with a `not_canonical_form` rule.
    """

    name: str = "uuid_canonicalization"

    def can_handle(self, contract: Contract, value: object) -> bool:
        return isinstance(contract, CanonicalUUIDContract) and isinstance(value, str)

    def canonicalize(self, value: object, contract: Contract) -> CapabilityResult:
        # Defensive type-check (mirrors email's pattern).
        if not isinstance(contract, CanonicalUUIDContract):
            return CapabilityResult(
                status=Status.INVALID,
                evidence=(_evidence("not_a_uuid_contract"),),
            )
        if not isinstance(value, str):
            return CapabilityResult(
                status=Status.INVALID,
                evidence=(_evidence("not_a_string_value"),),
            )

        # Check 1: length must be 36.
        if len(value) != CANONICAL_LENGTH:
            return CapabilityResult(
                status=Status.INVALID,
                evidence=(_evidence("not_canonical_form"),),
            )

        # Check 2: characters must be in [0-9a-f-], and hyphens at the
        # four canonical positions only.
        for i, ch in enumerate(value):
            if ch not in CANONICAL_CHARS:
                return CapabilityResult(
                    status=Status.INVALID,
                    evidence=(_evidence("not_canonical_form"),),
                )
            if ch == "-" and i not in HYPHEN_POSITIONS:
                return CapabilityResult(
                    status=Status.INVALID,
                    evidence=(_evidence("not_canonical_form"),),
                )
            if ch != "-" and i in HYPHEN_POSITIONS:
                return CapabilityResult(
                    status=Status.INVALID,
                    evidence=(_evidence("not_canonical_form"),),
                )

        # Check 3: version-nibble must match the contract's `version` policy.
        # The version-nibble is the first hex digit of the third group,
        # which starts at position 14 (after 8 + 1 + 4 + 1 = 14).
        version_nibble = value[14]
        expected = contract.version
        if expected != "any":
            if version_nibble != expected:
                return CapabilityResult(
                    status=Status.INVALID,
                    evidence=(_evidence("version_mismatch"),),
                )

        # All checks passed: the input is already in canonical form.
        return CapabilityResult(
            status=Status.CANONICALIZED,
            value=value,
            evidence=(_evidence("no_transformation_needed"),),
        )
