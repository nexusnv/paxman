"""Boolean contract value objects + builder/registration.

Mandate Law 5: the contract is the truth. It declares *what* the canonical
form is, never *how* it is produced.
"""

from __future__ import annotations

from typing import Any

import attrs

from paxman._errors import ContractError
from paxman._registry.contract_registry import register_contract


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
    kind: str = "canonical_boolean"
    version: int = 1
    version_field: int = 1

    authority_override: Any = attrs.field(
        default=None,
        repr=False,
    )

    def as_dict(self) -> dict[str, Any]:
        """Return the Dict DSL form of this contract."""
        return {
            "kind": self.kind,
            "accept_numeric": self.accept_numeric,
            "accept_words": self.accept_words,
            "case_sensitive": self.case_sensitive,
            "version": self.version,
        }


def Boolean(
    *,
    accept_numeric: bool = True,
    accept_words: bool = True,
    case_sensitive: bool = False,
    authority_override: Any | None = None,
) -> CanonicalBooleanContract:
    """Domain-type sugar: declare a boolean contract in user vocabulary.

    Args:
        accept_numeric: enable "1" -> true, "0" -> false. Default True.
        accept_words: enable yes/no, y/n, t/f, on/off, enabled/disabled.
            Default True.
        case_sensitive: match tokens case-insensitively when False.
            Default False.

    Returns:
        A frozen CanonicalBooleanContract instance.
    """
    return CanonicalBooleanContract(
        accept_numeric=accept_numeric,
        accept_words=accept_words,
        case_sensitive=case_sensitive,
        authority_override=authority_override,
    )


def _require_bool(field: str, value: object) -> bool:
    """Validate that a contract field is a real bool (Law 7 — explicit)."""
    if not isinstance(value, bool):
        raise ContractError(f"contract field {field!r} must be a bool, got {type(value).__name__}")
    return value


def _build_boolean(spec: dict[str, Any]) -> CanonicalBooleanContract:
    return CanonicalBooleanContract(
        accept_numeric=_require_bool("accept_numeric", spec.get("accept_numeric", True)),
        accept_words=_require_bool("accept_words", spec.get("accept_words", True)),
        case_sensitive=_require_bool("case_sensitive", spec.get("case_sensitive", False)),
    )


register_contract("canonical_boolean", _build_boolean)
