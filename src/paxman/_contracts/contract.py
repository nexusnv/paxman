"""Contract value objects and the Dict DSL parser.

Mandate Law 5: the contract is the truth. It declares *what* the canonical
form is, never *how* it is produced. The DSL is a closed vocabulary:
`kind` is a fixed set, and an unknown `kind` raises `ContractError` at
parse time (the orchestrator catches that and yields `Status.UNSUPPORTED`).
"""

from __future__ import annotations

from typing import Any, Literal, cast

import attrs

from paxman._core.types import ProviderAliasesPolicy
from paxman._errors import ContractError


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
    kind: str = "canonical_email"
    version: int = 1
    version_field: int = 1

    def as_dict(self) -> dict[str, Any]:
        """Return the Dict DSL form of this contract.

        Round-trips through `parse_contract` (the `kind` discriminator
        and the `version` are explicit so a future schema change can
        detect a stale serialization).

        Returns:
            A dict compatible with `parse_contract`.
        """
        return {
            "kind": self.kind,
            "lowercase": self.lowercase,
            "strip_whitespace": self.strip_whitespace,
            "provider_aliases": self.provider_aliases,
            "strict": self.strict,
            "version": self.version,
        }


def Email(
    *,
    strict: bool = False,
    provider_aliases: ProviderAliasesPolicy = "none",
    lowercase: bool = True,
    strip_whitespace: bool = True,
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

    Returns:
        A frozen CanonicalEmailContract instance.
    """
    return CanonicalEmailContract(
        lowercase=lowercase,
        strip_whitespace=strip_whitespace,
        provider_aliases=provider_aliases,
        strict=strict,
    )


@attrs.frozen
class CanonicalUUIDContract:
    """The v2.0.0 UUID contract.

    The canonical form is the RFC 4122 §3 representation: 32 lowercase
    hex characters in 8-4-4-4-12 grouping, total 36 characters. The
    `version` field is the only policy lever; a contract that says
    `version="4"` rejects v1, v3, v5, and v7 inputs with `Status.INVALID`.
    """

    version: Literal["any", "1", "3", "4", "5", "7"] = "any"
    kind: str = "canonical_uuid"
    version_field: int = 1

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


# v2.0.0 has exactly one contract kind. New kinds bump the contract
# version and are added here.
Contract = CanonicalEmailContract | CanonicalUUIDContract

_KIND_DISPATCH: dict[str, type[Contract]] = {
    "canonical_email": CanonicalEmailContract,
    "canonical_uuid": CanonicalUUIDContract,
}

_VALID_PROVIDER_ALIASES = {"none", "gmail"}


def _require_bool(field: str, value: object) -> bool:
    """Validate that a contract field is a real bool. Non-bool values
    (including truthy strings) raise `ContractError` rather than being
    silently coerced. Mandate Law 7 — explicit over clever."""
    if not isinstance(value, bool):
        raise ContractError(f"contract field {field!r} must be a bool, got {type(value).__name__}")
    return value


def parse_contract(spec: Any) -> Contract:
    """Parse a Dict DSL contract into a Contract value object.

    Raises `ContractError` on:
    - non-dict input (unless it's already a CanonicalEmailContract)
    - missing or unknown `kind`
    - invalid field values (wrong type, unknown provider_aliases)
    """
    # Short-circuit: an already-parsed contract value object is the
    # source of truth (Law 5). Exact-type checks (not the parent
    # `Contract` alias) so a future multi-field contract type is NOT
    # silently absorbed here — it must grow its own dispatch branch.
    if isinstance(spec, CanonicalEmailContract):
        return spec
    if isinstance(spec, CanonicalUUIDContract):
        return spec

    if not isinstance(spec, dict):
        raise ContractError(f"contract must be a dict, got {type(spec).__name__}")

    kind = spec.get("kind")
    if not isinstance(kind, str):
        raise ContractError("contract must have a string 'kind' field")

    if kind not in _KIND_DISPATCH:
        raise ContractError(
            f"unknown contract kind: {kind!r}; supported kinds: {sorted(_KIND_DISPATCH)}"
        )

    if kind == "canonical_email":
        provider_aliases = spec.get("provider_aliases", "none")
        if provider_aliases not in _VALID_PROVIDER_ALIASES:
            raise ContractError(
                f"invalid provider_aliases: {provider_aliases!r}; "
                f"allowed: {sorted(_VALID_PROVIDER_ALIASES)}"
            )
        return CanonicalEmailContract(
            lowercase=_require_bool("lowercase", spec.get("lowercase", True)),
            strip_whitespace=_require_bool("strip_whitespace", spec.get("strip_whitespace", True)),
            provider_aliases=cast(ProviderAliasesPolicy, provider_aliases),
            strict=_require_bool("strict", spec.get("strict", False)),
        )

    if kind == "canonical_uuid":
        version = spec.get("version", "any")
        if version not in {"any", "1", "3", "4", "5", "7"}:
            raise ContractError(
                f"invalid uuid version: {version!r}; allowed: ['any', '1', '3', '4', '5', '7']"
            )
        return CanonicalUUIDContract(version=version)

    # Unreachable: kind is guaranteed to be in _KIND_DISPATCH above.
    raise ContractError(f"unhandled contract kind: {kind!r}")
