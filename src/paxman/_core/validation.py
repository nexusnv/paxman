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

from paxman._capabilities.boolean.contract import CanonicalBooleanContract
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


def validate(
    value: str,
    contract: object,
) -> ValidationResult:
    """Validate a canonical value against the contract.

    Raises `UnsupportedContractError` for unknown contract kinds. The
    orchestrator is responsible for catching that and mapping to
    `Status.UNSUPPORTED`.
    """
    # v2.0.0: dispatch on type. The supported kinds are the email,
    # uuid, and date contracts. A future v2.x that adds new kinds will replace this
    # with a Protocol-based dispatch table.
    if isinstance(contract, CanonicalUUIDContract):
        # The UUIDCapability has already validated the canonical form and
        # the version policy; no further policy check is needed here.
        # Mandate Law 11: Paxman must not silently canonicalize
        # incorrectly — delegating to the capability's prior validation
        # upholds that guarantee (deterministic, no guessing).
        return ValidationResult(is_valid=True)
    if isinstance(contract, CanonicalDateContract):
        # The DateCapability has already validated the canonical form;
        # no further policy check is needed here (same rationale as
        # UUID above — Law 11).
        return ValidationResult(is_valid=True)
    if isinstance(contract, CanonicalPhoneContract):
        # The PhoneCapability has already validated the canonical form
        # against the E.164 global shape rule; no further policy check
        # is needed here (same rationale as UUID/Date above — Law 11).
        return ValidationResult(is_valid=True)
    if isinstance(contract, CanonicalURLContract):
        # The URLCapability has already validated the canonical form;
        # no further policy check is needed here (same rationale as
        # UUID/Date/Phone above — Law 11).
        return ValidationResult(is_valid=True)
    if isinstance(contract, CanonicalBooleanContract):
        # The BooleanCapability has already validated the canonical form
        # ("true"/"false"); no further policy check is needed here
        # (same rationale as UUID/Date/Phone/URL above — Law 11).
        return ValidationResult(is_valid=True)
    if isinstance(contract, CanonicalIPContract):
        # The IPCapability has already validated the canonical form
        # (RFC 5952 / dotted-decimal); no further policy check is needed
        # here (mandate Law 11 — delegating to the capability's prior
        # validation upholds the no-silent-canonicalization guarantee).
        return ValidationResult(is_valid=True)
    if isinstance(contract, CanonicalMoneyContract):
        # The MoneyCapability has already validated the canonical form
        # ("<ISO4217>:<amount>"); no further policy check is needed here
        # (same rationale as UUID/Date/Phone/URL/IP above — Law 11).
        return ValidationResult(is_valid=True)
    if isinstance(contract, CanonicalGeolocationContract):
        # The GeolocationCapability has already validated the canonical form
        # ("<lat>,<lon>" decimal WGS84); no further policy check is needed here
        # (same rationale as UUID/Date/Phone/URL/IP/Money above — Law 11).
        return ValidationResult(is_valid=True)
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
