"""Boolean contract value objects + builder/registration.

Mandate Law 5: the contract is the truth. It declares *what* the canonical
form is, never *how* it is produced.
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


def _validate_output_format_boolean(inst: object, attr: object, value: object) -> None:
    """Attrs validator: output_format must be one of the supported formats."""
    _SUPPORTED = frozenset({"truefalse"})
    if not isinstance(value, str) or value not in _SUPPORTED:
        name = getattr(attr, "name", attr)
        raise ContractError(
            f"contract field {name!r} must be one of {sorted(_SUPPORTED)}, got {value!r}"
        )


@attrs.frozen
class CanonicalBooleanContract:
    """The boolean contract.

    Fields are policy declarations (mandate Law 7 — Explicit Over Clever).
    There is no `auto_detect`. The caller declares the policy; the
    capability applies it.
    """

    accept_numeric: bool = True
    accept_words: bool = True
    case_sensitive: bool = False
    output_format: Literal["truefalse"] = attrs.field(
        default="truefalse", validator=_validate_output_format_boolean
    )
    kind: str = "canonical_boolean"
    version: int = 1
    version_field: int = 1

    include_grammar: tuple[str, ...] = ()
    exclude_grammar: tuple[str, ...] = ()

    authority_override: Any = authority_override_field()

    def as_dict(self) -> dict[str, Any]:
        """Return the Dict DSL form of this contract."""
        return strip_authority_override(
            {
                "kind": self.kind,
                "accept_numeric": self.accept_numeric,
                "accept_words": self.accept_words,
                "case_sensitive": self.case_sensitive,
                "output_format": self.output_format,
                "version": self.version,
                "include_grammar": self.include_grammar,
                "exclude_grammar": self.exclude_grammar,
            }
        )


def Boolean(
    *,
    accept_numeric: bool = True,
    accept_words: bool = True,
    case_sensitive: bool = False,
    output_format: Literal["truefalse"] = "truefalse",
    include_grammar: tuple[str, ...] = (),
    exclude_grammar: tuple[str, ...] = (),
    authority_override: Any | None = None,
) -> CanonicalBooleanContract:
    """Domain-type sugar: declare a boolean contract in user vocabulary.

    Args:
        accept_numeric: enable "1" -> true, "0" -> false. Default True.
        accept_words: enable yes/no, y/n, t/f, on/off, enabled/disabled.
            Default True.
        case_sensitive: match tokens case-insensitively when False.
            Default False.
        output_format: the canonical output form. Default "truefalse".

    Returns:
        A frozen CanonicalBooleanContract instance.
    """
    return CanonicalBooleanContract(
        accept_numeric=accept_numeric,
        accept_words=accept_words,
        case_sensitive=case_sensitive,
        output_format=output_format,
        include_grammar=include_grammar,
        exclude_grammar=exclude_grammar,
        authority_override=authority_override,
    )


def _require_bool(field: str, value: object) -> bool:
    """Validate that a contract field is a real bool (Law 7 — explicit)."""
    if not isinstance(value, bool):
        raise ContractError(f"contract field {field!r} must be a bool, got {type(value).__name__}")
    return value


def _build_boolean(spec: dict[str, Any]) -> CanonicalBooleanContract:
    authority_override = _authority_override_from_spec(spec)
    output_format = spec.get("output_format", "truefalse")
    _SUPPORTED_OUTPUT_FORMATS = frozenset({"truefalse"})
    if not isinstance(output_format, str) or output_format not in _SUPPORTED_OUTPUT_FORMATS:
        raise ContractError(
            f"output_format must be one of {sorted(_SUPPORTED_OUTPUT_FORMATS)},"
            f" got {output_format!r}"
        )
    output_format = cast(Literal["truefalse"], output_format)
    return CanonicalBooleanContract(
        accept_numeric=_require_bool("accept_numeric", spec.get("accept_numeric", True)),
        accept_words=_require_bool("accept_words", spec.get("accept_words", True)),
        case_sensitive=_require_bool("case_sensitive", spec.get("case_sensitive", False)),
        output_format=output_format,
        include_grammar=tuple(spec.get("include_grammar", ())),
        exclude_grammar=tuple(spec.get("exclude_grammar", ())),
        authority_override=authority_override,
    )


register_contract("canonical_boolean", _build_boolean)
