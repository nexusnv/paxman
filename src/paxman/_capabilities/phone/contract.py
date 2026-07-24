"""Phone contract value objects + builder/registration.

Mandate Law 5: the contract is the truth. It declares *what* the canonical
form is (which country code to apply), never *how* it is produced.
"""

from __future__ import annotations

from typing import Any, Literal, cast

import attrs

from paxman._capabilities._shared.contract import (
    _authority_override_from_spec,
    authority_override_field,
    strip_authority_override,
)
from paxman._errors import ContractError
from paxman._registry.contract_registry import register_contract


def _validate_output_format_phone(inst: object, attr: object, value: object) -> None:
    """Attrs validator: output_format must be one of the supported formats."""
    _SUPPORTED = frozenset({"e164"})
    if not isinstance(value, str) or value not in _SUPPORTED:
        name = getattr(attr, "name", attr)
        raise ContractError(
            f"contract field {name!r} must be one of {sorted(_SUPPORTED)}, got {value!r}"
        )


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

    output_format: Literal["e164"] = attrs.field(
        default="e164", validator=_validate_output_format_phone
    )

    include_grammar: tuple[str, ...] = ()
    exclude_grammar: tuple[str, ...] = ()

    authority_override: Any = authority_override_field()

    def as_dict(self) -> dict[str, Any]:
        """Return the Dict DSL form of this contract.

        Round-trips through `parse_contract` (the `kind` discriminator and
        the `version` are explicit so a future schema change can detect a
        stale serialization).

        Returns:
            A dict compatible with `parse_contract`.
        """
        return strip_authority_override(
            {
                "kind": self.kind,
                "country": self.country,
                "output_format": self.output_format,
                "version": self.version,
                "include_grammar": self.include_grammar,
                "exclude_grammar": self.exclude_grammar,
            }
        )


def Phone(
    *,
    country: str = "US",
    output_format: Literal["e164"] = "e164",
    include_grammar: tuple[str, ...] = (),
    exclude_grammar: tuple[str, ...] = (),
    authority_override: Any | None = None,
) -> CanonicalPhoneContract:
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
        output_format: the canonical output form. Default "e164".

    Returns:
        A frozen CanonicalPhoneContract instance.
    """
    return CanonicalPhoneContract(
        country=country,
        output_format=output_format,
        include_grammar=include_grammar,
        exclude_grammar=exclude_grammar,
        authority_override=authority_override,
    )


def _build_phone(spec: dict[str, Any]) -> CanonicalPhoneContract:
    country = spec.get("country", "US")
    if not isinstance(country, str):
        raise ContractError(f"contract field 'country' must be a str, got {type(country).__name__}")
    # Validate the country against the v1 lookup table up front; an unknown
    # country is a contract error, not a runtime guess (Law 3).
    from paxman._capabilities.phone.parser import _cc_for_country

    _cc_for_country(country)  # raises ContractError if unknown
    output_format = spec.get("output_format", "e164")
    _SUPPORTED_OUTPUT_FORMATS = frozenset({"e164"})
    if not isinstance(output_format, str) or output_format not in _SUPPORTED_OUTPUT_FORMATS:
        supported = sorted(_SUPPORTED_OUTPUT_FORMATS)
        raise ContractError(f"output_format must be one of {supported}, got {output_format!r}")
    authority_override = _authority_override_from_spec(spec)
    output_format = cast(Literal["e164"], output_format)
    return CanonicalPhoneContract(
        country=country,
        output_format=output_format,
        include_grammar=tuple(spec.get("include_grammar", ())),
        exclude_grammar=tuple(spec.get("exclude_grammar", ())),
        authority_override=authority_override,
    )


register_contract("canonical_phone", _build_phone)
