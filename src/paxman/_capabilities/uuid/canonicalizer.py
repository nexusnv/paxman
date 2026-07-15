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

from paxman._capabilities.uuid.contract import CanonicalUUIDContract
from paxman._capabilities.uuid.parser import CANONICAL_CHARS, CANONICAL_LENGTH, HYPHEN_POSITIONS
from paxman._capabilities.uuid.rules import _evidence
from paxman._core.contracts import Contract
from paxman._core.result import CapabilityResult
from paxman._core.status import Status


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
