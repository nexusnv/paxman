"""Post-capability validation gate.

Mandate Law 4 (Canonicalize, Don't Interpret): validation is *policy
checking*, not interpretation. It verifies that the canonical value
satisfies the contract's strictness policy; it does not invent policies.

For v2.0.0, the supported kinds are `canonical_email`, `canonical_uuid`,
`canonical_date`, `canonical_phone`, `canonical_url`, and `canonical_boolean`.
Any other kind raises `UnsupportedContractError` (defined in
`paxman._errors`); the orchestrator catches that and produces
`Status.UNSUPPORTED` instead of letting the call fail.
"""

from __future__ import annotations

from collections.abc import Callable

from paxman._capabilities.boolean.contract import CanonicalBooleanContract
from paxman._capabilities.country.contract import CanonicalCountryContract
from paxman._capabilities.date.contract import CanonicalDateContract
from paxman._capabilities.email.contract import CanonicalEmailContract
from paxman._capabilities.geolocation.contract import CanonicalGeolocationContract
from paxman._capabilities.ip.contract import CanonicalIPContract
from paxman._capabilities.money.contract import CanonicalMoneyContract
from paxman._capabilities.phone.contract import CanonicalPhoneContract
from paxman._capabilities.url.contract import CanonicalURLContract
from paxman._capabilities.uuid.contract import CanonicalUUIDContract
from paxman._core.classification import ValidationResult
from paxman._errors import UnsupportedContractError


def _always_valid(value: str, contract: object) -> ValidationResult:
    """Return a passing result for a contract already validated by its capability.

    The relevant capability has already validated the canonical form and any
    version/shape policy; no further policy check is needed here. Mandate Law 11:
    Paxman must not silently canonicalize incorrectly — delegating to the
    capability's prior validation upholds that guarantee (deterministic, no
    guessing).
    """
    return ValidationResult(is_valid=True)


def _validate_email(value: str, contract: object) -> ValidationResult:
    """Validate a canonical email value against the contract's strictness policy.

    The EmailCapability has already validated the canonical form; this step only
    enforces the post-capability policy (Law 4): non-empty local/domain parts and,
    in strict mode, no embedded whitespace and ASCII-only local/domain.
    """
    # Local part and domain must be non-empty.
    if "@" not in value:
        return ValidationResult(is_valid=False)
    local, _, domain = value.partition("@")
    if not local or not domain:
        return ValidationResult(is_valid=False)

    if contract.strict:
        # Strict mode in v2.0.0 is intentionally narrow: it rejects
        # embedded whitespace and non-ASCII characters in the local
        # and domain parts. It does NOT enforce a dot-atom grammar —
        # the dot-atom gate is owned by the EmailCapability's
        # surface-grammar check (Law 14 spec), not by this post-
        # capability validation step. The domain check below is the
        # same non-empty + ASCII check as for the local part; single-
        # label domains like `localhost` are accepted.
        if " " in local or " " in domain:
            return ValidationResult(is_valid=False)
        # IDN/unicode is rejected in v2.0.0 (out of scope).
        try:
            local.encode("ascii")
            domain.encode("ascii")
        except UnicodeEncodeError:
            return ValidationResult(is_valid=False)

    return ValidationResult(is_valid=True)


# Registry mapping each supported contract type to its validator. Dispatch is on
# the exact contract type (type(contract)), preserving the prior per-branch
# isinstance behavior. The eight non-email kinds are already validated by their
# capability (Law 11), so they share the no-op _always_valid validator.
VALIDATORS: dict[type, Callable[[str, object], ValidationResult]] = {
    CanonicalUUIDContract: _always_valid,
    CanonicalDateContract: _always_valid,
    CanonicalPhoneContract: _always_valid,
    CanonicalURLContract: _always_valid,
    CanonicalBooleanContract: _always_valid,
    CanonicalIPContract: _always_valid,
    CanonicalMoneyContract: _always_valid,
    CanonicalCountryContract: _always_valid,
    CanonicalGeolocationContract: _always_valid,
    CanonicalEmailContract: _validate_email,
}


def validate(
    value: str,
    contract: object,
) -> ValidationResult:
    """Validate a canonical value against the contract.

    Raises `UnsupportedContractError` for unknown contract kinds. The
    orchestrator is responsible for catching that and mapping to
    `Status.UNSUPPORTED`.
    """
    validator = VALIDATORS.get(type(contract))
    if validator is None:
        raise UnsupportedContractError(
            f"validation does not support contract kind: {type(contract).__name__}"
        )
    return validator(value, contract)
