"""Phone contract value objects + builder/registration.

Mandate Law 5: the contract is the truth. It declares *what* the canonical
form is (which country code to apply), never *how* it is produced.
"""

from __future__ import annotations

from typing import Any

import attrs

from paxman._capabilities._shared.contract import (
    _authority_override_from_spec,
    authority_override_field,
)
from paxman._errors import ContractError
from paxman._registry.contract_registry import register_contract


@attrs.frozen
class CanonicalPhoneContract:
    """The v1 phone contract.

    Fields are policy declarations (mandate Law 7 — Explicit Over Clever).
    There is no `auto_detect_country`. There is no `infer_region`. The caller
    declares the country; the capability applies it.
    """

    country: str = "US"
    kind: str = "canonical_phone"
    version: int = 1
    version_field: int = 1

    authority_override: Any = authority_override_field()

    def as_dict(self) -> dict[str, Any]:
        """Return the Dict DSL form of this contract.

        Round-trips through `parse_contract` (the `kind` discriminator and
        the `version` are explicit so a future schema change can detect a
        stale serialization).

        Returns:
            A dict compatible with `parse_contract`.
        """
        return {
            "kind": self.kind,
            "country": self.country,
            "version": self.version,
        }


def Phone(*, country: str = "US", authority_override: Any | None = None) -> CanonicalPhoneContract:
    """Domain-type sugar: declare a phone contract in user vocabulary.

    MANDATE §4: the contract is the user's language; the capability is
    Paxman's language. This factory returns a configured
    CanonicalPhoneContract value object; it does NOT subclass it (preserves
    all isinstance checks and @attrs.frozen immutability without introducing
    a new abstraction to defend under Law 11).

    Args:
        country: ISO 3166-1 alpha-2 country code used to expand national
            numbers into E.164. Declared policy; never inferred (Law 7).
            Default "US".

    Returns:
        A frozen CanonicalPhoneContract instance.
    """
    return CanonicalPhoneContract(country=country, authority_override=authority_override)


def _build_phone(spec: dict[str, Any]) -> CanonicalPhoneContract:
    country = spec.get("country", "US")
    if not isinstance(country, str):
        raise ContractError(f"contract field 'country' must be a str, got {type(country).__name__}")
    # Validate the country against the v1 lookup table up front; an unknown
    # country is a contract error, not a runtime guess (Law 3).
    from paxman._capabilities.phone.parser import _cc_for_country

    _cc_for_country(country)  # raises ContractError if unknown
    authority_override = _authority_override_from_spec(spec)
    return CanonicalPhoneContract(country=country, authority_override=authority_override)


register_contract("canonical_phone", _build_phone)
