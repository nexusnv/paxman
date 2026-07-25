"""Email contract value objects + builder/registration.

Mandate Law 5: the contract is the truth. It declares *what* the canonical
form is, never *how* it is produced.
"""

from __future__ import annotations

from typing import Any, Literal, cast

import attrs

from paxman._capabilities._shared.contract import (
    _authority_override_from_spec,
    authority_override_field,
    grammar_selector_converter,
    require_bool,
    strip_authority_override,
)
from paxman._errors import ContractError
from paxman._registry.contract_registry import register_contract
from paxman._types.common import ProviderAliasesPolicy


def _validate_output_format_email(inst: object, attr: object, value: object) -> None:
    """Attrs validator: output_format must be one of the supported formats."""
    _SUPPORTED = frozenset({"email"})
    if not isinstance(value, str) or value not in _SUPPORTED:
        name = getattr(attr, "name", attr)
        raise ContractError(
            f"contract field {name!r} must be one of {sorted(_SUPPORTED)}, got {value!r}"
        )


@attrs.frozen
class CanonicalEmailContract:
    """The v2.0.0 email contract.

    Fields are policy declarations (mandate Law 7 — Explicit Over Clever).
    There is no `auto_detect`. There is no `infer_provider`. The caller
    declares the policy; the capability applies it.
    """

    lowercase: bool = True
    strip_whitespace: bool = True
    provider_aliases: ProviderAliasesPolicy = "none"
    strict: bool = False
    output_format: Literal["email"] = attrs.field(
        default="email", validator=_validate_output_format_email
    )
    kind: str = "canonical_email"
    version: int = 1
    version_field: int = 1

    include_grammar: tuple[str, ...] = attrs.field(default=(), converter=grammar_selector_converter)
    exclude_grammar: tuple[str, ...] = attrs.field(default=(), converter=grammar_selector_converter)

    authority_override: Any = authority_override_field()

    def as_dict(self) -> dict[str, Any]:
        """Return the Dict DSL form of this contract.

        Round-trips through `parse_contract` (the `kind` discriminator
        and the `version` are explicit so a future schema change can
        detect a stale serialization).

        Returns:
            A dict compatible with `parse_contract`.
        """
        return strip_authority_override(
            {
                "kind": self.kind,
                "lowercase": self.lowercase,
                "strip_whitespace": self.strip_whitespace,
                "provider_aliases": self.provider_aliases,
                "strict": self.strict,
                "output_format": self.output_format,
                "version": self.version,
                "include_grammar": self.include_grammar,
                "exclude_grammar": self.exclude_grammar,
            }
        )


def Email(
    *,
    strict: bool = False,
    provider_aliases: ProviderAliasesPolicy = "none",
    lowercase: bool = True,
    strip_whitespace: bool = True,
    output_format: Literal["email"] = "email",
    include_grammar: tuple[str, ...] = (),
    exclude_grammar: tuple[str, ...] = (),
    authority_override: Any | None = None,
) -> CanonicalEmailContract:
    """Domain-type sugar: declare an email contract in user vocabulary.

    MANDATE §4: the contract is the user's language; the capability is
    Paxman's language. This factory returns a configured
    CanonicalEmailContract value object; it does NOT subclass it
    (preserves all isinstance checks and @attrs.frozen immutability
    without introducing a new abstraction to defend under Law 11).

    Field defaults mirror CanonicalEmailContract's own field defaults
    exactly. Generalizes cleanly to future domain types (Money(), Date())
    and the north-star multi-field form (InvoiceContract(vendor_email=
    Email(), ...)) — each future type is one factory, no new abstraction
    class.

    Args:
        strict: reject inputs with embedded whitespace or non-ASCII
            characters (Law 7 — Explicit Over Clever). Default False.
        provider_aliases: "none" preserves the input domain; "gmail"
            applies the documented Gmail dot-ignoring and +tag-stripping
            rules (Law 5 — the contract declares the policy). Default
            "none".
        lowercase: lowercase the local part and the domain. Default True.
        strip_whitespace: strip leading/trailing ASCII whitespace.
            Default True.
        output_format: the canonical output form. Default "email".
            Supported: "email".

    Returns:
        A frozen CanonicalEmailContract instance.
    """
    return CanonicalEmailContract(
        lowercase=lowercase,
        strip_whitespace=strip_whitespace,
        provider_aliases=provider_aliases,
        strict=strict,
        output_format=output_format,
        include_grammar=include_grammar,
        exclude_grammar=exclude_grammar,
        authority_override=authority_override,
    )


_VALID_PROVIDER_ALIASES = {"none", "gmail"}


def _build_email(spec: dict[str, Any]) -> CanonicalEmailContract:
    provider_aliases = spec.get("provider_aliases", "none")
    if provider_aliases not in _VALID_PROVIDER_ALIASES:
        raise ContractError(
            f"invalid provider_aliases: {provider_aliases!r}; "
            f"allowed: {sorted(_VALID_PROVIDER_ALIASES)}"
        )
    output_format = spec.get("output_format", "email")
    _validate_output_format_email(None, None, output_format)
    return CanonicalEmailContract(
        lowercase=require_bool("lowercase", spec.get("lowercase", True)),
        strip_whitespace=require_bool("strip_whitespace", spec.get("strip_whitespace", True)),
        provider_aliases=cast(ProviderAliasesPolicy, provider_aliases),
        strict=require_bool("strict", spec.get("strict", False)),
        output_format=cast(Literal["email"], output_format),
        include_grammar=spec.get("include_grammar", ()),
        exclude_grammar=spec.get("exclude_grammar", ()),
        authority_override=_authority_override_from_spec(spec),
    )


register_contract("canonical_email", _build_email)
