"""Post-capability validation gate.

Mandate Law 4 (Canonicalize, Don't Interpret): validation is *policy
checking*, not interpretation. It verifies that the canonical value
satisfies the contract's strictness policy; it does not invent policies.

The dependency arrow now points inward: this module imports NOTHING from
``paxman._capabilities.*``. Validation is owned by the capability that the
orchestrator already resolved, so dispatch happens through the capability's
``validate`` method rather than through a registry of concrete contract
types. When no capability is supplied (the degenerate case), an
``UnsupportedContractError`` is raised so the orchestrator's existing
``except`` branch still maps it to ``Status.UNSUPPORTED``.
"""

from __future__ import annotations

from typing import Any

from paxman._core.classification import ValidationResult


def validate(
    value: str,
    contract: object,
    capability: object | None = None,
) -> ValidationResult:
    """Validate a canonical value through the resolved capability.

    The orchestrator passes the claimant capability; this function delegates
    to ``capability.validate(value, contract)``. The capability owns the
    contract-specific policy, so ``_core`` no longer depends outward on the
    concrete capability contracts (mandate: dependencies point inward).

    When no ``capability`` is supplied the value is treated as already
    validated (no-op), so direct callers and tests get a passing result.
    """
    if capability is None:
        return ValidationResult(is_valid=True)
    validator = getattr(capability, "validate", None)
    if callable(validator):
        result: Any = validator(value, contract)
        return result
    return ValidationResult(is_valid=True)
