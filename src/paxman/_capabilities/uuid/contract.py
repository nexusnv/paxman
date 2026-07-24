"""UUID contract value object and builder.

Mandate Law 5: the contract is the truth. It declares *what* the canonical
form is, never *how* it is produced.

This module lives under `paxman._capabilities.uuid` as part of the additive
architecture migration. It is a verbatim move of `CanonicalUUIDContract`,
the `UUID()` factory, and `_UUID_VERSIONS_ALLOWED` from
`paxman._contracts.contract`, plus a builder registration (`_build_uuid`)
that mirrors the old `parse_contract` uuid branch exactly.
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

_UUID_VERSIONS_ALLOWED = frozenset({"any", "1", "3", "4", "5", "7"})
_UUID_OUTPUT_FORMATS_ALLOWED = frozenset({"hex"})


def _validate_output_format_uuid(inst: object, attr: object, value: object) -> None:
    """Attrs validator: output_format must be one of the supported UUID formats."""
    if not isinstance(value, str) or value not in _UUID_OUTPUT_FORMATS_ALLOWED:
        name = getattr(attr, "name", attr)
        raise ContractError(
            f"contract field {name!r} must be one of {sorted(_UUID_OUTPUT_FORMATS_ALLOWED)}, "
            f"got {value!r}"
        )


@attrs.frozen
class CanonicalUUIDContract:
    """The v2.0.0 UUID contract.

    Mandate alignment:
    - Law 5: the contract declares the policy (which UUID versions to
      accept); the capability applies it.
    - Law 7: explicit over clever. `version`, `include_grammar`, and
      `exclude_grammar` are the policy levers; an unknown version raises
      `ContractError` at construction (see `__attrs_post_init__`), never
      a silent `INVALID`.
    - Law 13: the contract is `@attrs.frozen` — immutable by mandate.
    - Law 14: every capability rule that fires cites a source via
      `_RULE_AUTHORITIES`; `Evidence.authority` is populated from it.

    The canonical form is the RFC 4122 §3 representation: 32 lowercase
    hex characters in 8-4-4-4-12 grouping, total 36 characters. The
    `version`, `include_grammar`, and `exclude_grammar` fields control
    recognition policy; a contract that says `version="4"` rejects
    v1, v3, v5, and v7 inputs with `Status.INVALID`.
    When `version="any"` (the default) only the *form* is validated —
    the variant nibble is intentionally not constrained (per the
    documented `version="any"` form-only contract).
    """

    version: Literal["any", "1", "3", "4", "5", "7"] = "any"
    output_format: Literal["hex"] = attrs.field(
        default="hex", validator=_validate_output_format_uuid
    )
    kind: str = "canonical_uuid"
    version_field: int = 1
    include_grammar: tuple[str, ...] = ()
    exclude_grammar: tuple[str, ...] = ()

    authority_override: Any = authority_override_field()

    def __attrs_post_init__(self) -> None:
        if self.version not in _UUID_VERSIONS_ALLOWED:
            raise ContractError(
                f"invalid uuid version: {self.version!r}; allowed: {sorted(_UUID_VERSIONS_ALLOWED)}"
            )

    def as_dict(self) -> dict[str, Any]:
        """Return the Dict DSL form of this contract (round-trips via parse_contract)."""
        return strip_authority_override(
            {
                "kind": self.kind,
                "version": self.version,
                "output_format": self.output_format,
                "version_field": self.version_field,
                "include_grammar": self.include_grammar,
                "exclude_grammar": self.exclude_grammar,
            }
        )


def UUID(
    *,
    version: Literal["any", "1", "3", "4", "5", "7"] = "any",
    output_format: Literal["hex"] = "hex",
    include_grammar: tuple[str, ...] = (),
    exclude_grammar: tuple[str, ...] = (),
    authority_override: Any | None = None,
) -> CanonicalUUIDContract:
    """Domain-type sugar: declare a UUID contract in user vocabulary.

    Returns a `CanonicalUUIDContract` value object; does NOT subclass it.
    Mirrors the `Email()` factory pattern.
    """
    return CanonicalUUIDContract(
        version=version,
        output_format=output_format,
        include_grammar=include_grammar,
        exclude_grammar=exclude_grammar,
        authority_override=authority_override,
    )


def _build_uuid(spec: dict[str, Any]) -> CanonicalUUIDContract:
    version = spec.get("version", "any")
    if not isinstance(version, str) or version not in _UUID_VERSIONS_ALLOWED:
        raise ContractError(
            f"invalid uuid version: {version!r}; allowed: {sorted(_UUID_VERSIONS_ALLOWED)}"
        )
    output_format = spec.get("output_format", "hex")
    if not isinstance(output_format, str) or output_format not in _UUID_OUTPUT_FORMATS_ALLOWED:
        raise ContractError(
            f"output_format must be one of {sorted(_UUID_OUTPUT_FORMATS_ALLOWED)}, "
            f"got {output_format!r}"
        )
    authority_override = _authority_override_from_spec(spec)
    return CanonicalUUIDContract(
        version=cast(Literal["any", "1", "3", "4", "5", "7"], version),
        output_format=cast(Literal["hex"], output_format),
        include_grammar=tuple(spec.get("include_grammar", ())),
        exclude_grammar=tuple(spec.get("exclude_grammar", ())),
        authority_override=authority_override,
    )


register_contract("canonical_uuid", _build_uuid)
