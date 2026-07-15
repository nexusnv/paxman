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

from typing import Any, Literal

import attrs

from paxman._errors import ContractError
from paxman._registry.contract_registry import register_contract

_UUID_VERSIONS_ALLOWED = frozenset({"any", "1", "3", "4", "5", "7"})


@attrs.frozen
class CanonicalUUIDContract:
    """The v2.0.0 UUID contract.

    Mandate alignment:
    - Law 5: the contract declares the policy (which UUID versions to
      accept); the capability applies it.
    - Law 7: explicit over clever. `version` is the only policy lever;
      an unknown version raises `ContractError` at construction (see
      `__attrs_post_init__`), never a silent `INVALID`.
    - Law 13: the contract is `@attrs.frozen` — immutable by mandate.
    - Law 14: every capability rule that fires cites a source via
      `_RULE_PROVENANCE`; `Evidence.provenance` is populated from it.

    The canonical form is the RFC 4122 §3 representation: 32 lowercase
    hex characters in 8-4-4-4-12 grouping, total 36 characters. The
    `version` field is the only policy lever; a contract that says
    `version="4"` rejects v1, v3, v5, and v7 inputs with `Status.INVALID`.
    When `version="any"` (the default) only the *form* is validated —
    the variant nibble is intentionally not constrained (per the
    documented `version="any"` form-only contract).
    """

    version: Literal["any", "1", "3", "4", "5", "7"] = "any"
    kind: str = "canonical_uuid"
    version_field: int = 1

    def __attrs_post_init__(self) -> None:
        # Enforce the allowed version set at runtime. `attrs` does not
        # validate `Literal`, so a misconfigured `UUID(version="99")`
        # would otherwise silently canonicalize every input to INVALID
        # (Mandate Law 7 — explicit over clever; fail loudly).
        if self.version not in _UUID_VERSIONS_ALLOWED:
            raise ContractError(
                f"invalid uuid version: {self.version!r}; allowed: {sorted(_UUID_VERSIONS_ALLOWED)}"
            )

    def as_dict(self) -> dict[str, Any]:
        """Return the Dict DSL form of this contract (round-trips via parse_contract)."""
        return {
            "kind": self.kind,
            "version": self.version,
            "version_field": self.version_field,
        }


def UUID(
    *,
    version: Literal["any", "1", "3", "4", "5", "7"] = "any",
) -> CanonicalUUIDContract:
    """Domain-type sugar: declare a UUID contract in user vocabulary.

    Returns a `CanonicalUUIDContract` value object; does NOT subclass it.
    Mirrors the `Email()` factory pattern.
    """
    return CanonicalUUIDContract(version=version)


def _build_uuid(spec: dict[str, Any]) -> CanonicalUUIDContract:
    version = spec.get("version", "any")
    if not isinstance(version, str) or version not in _UUID_VERSIONS_ALLOWED:
        raise ContractError(
            f"invalid uuid version: {version!r}; allowed: {sorted(_UUID_VERSIONS_ALLOWED)}"
        )
    return CanonicalUUIDContract(version=version)


register_contract("canonical_uuid", _build_uuid)
