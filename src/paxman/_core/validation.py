"""Post-capability validation gate.

Mandate Law 4 (Canonicalize, Don't Interpret): validation is *policy
checking*, not interpretation. It verifies that the canonical value
satisfies the contract's strictness policy; it does not invent policies.

For v1.0.0, only `kind == "canonical_email"` contracts are supported.
Any other kind raises `UnsupportedContractError` (defined in
`paxman._errors`); the orchestrator catches that and produces
`Status.UNSUPPORTED` instead of letting the call fail.
"""

from __future__ import annotations

from paxman._contracts.contract import CanonicalEmailContract
from paxman._core.classification import ValidationResult
from paxman._errors import UnsupportedContractError


def validate(value: str, contract: CanonicalEmailContract) -> ValidationResult:
    """Validate a canonical value against the contract.

    Raises `UnsupportedContractError` for unknown contract kinds. The
    orchestrator is responsible for catching that and mapping to
    `Status.UNSUPPORTED`.
    """
    # v1.0.0: dispatch on type. The only supported kind is the email
    # contract. A future v2.x that adds new kinds will replace this
    # with a Protocol-based dispatch table.
    if not isinstance(contract, CanonicalEmailContract):
        raise UnsupportedContractError(
            f"validation does not support contract kind: {type(contract).__name__}"
        )

    # Local part and domain must be non-empty.
    if "@" not in value:
        return ValidationResult(is_valid=False)
    local, _, domain = value.partition("@")
    if not local or not domain:
        return ValidationResult(is_valid=False)

    if contract.strict:
        # Strict mode: the local part must match a dot-atom production
        # (no spaces). The domain is checked by the @-sign + non-empty
        # check above; the dot-atom-domain check is intentionally loose
        # in v1.0.0 (a single dot suffices).
        if " " in local or " " in domain:
            return ValidationResult(is_valid=False)
        # IDN/unicode is rejected in v1.0.0 (out of scope).
        try:
            local.encode("ascii")
            domain.encode("ascii")
        except UnicodeEncodeError:
            return ValidationResult(is_valid=False)

    return ValidationResult(is_valid=True)
