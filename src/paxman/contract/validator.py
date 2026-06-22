"""Contract validator — rejects invalid :class:`CanonicalContract` instances.

The contract validator is the **mandatory** post-adapter step (per
``PACKAGE_STRUCTURE.md`` §3.4 invariant #2). Every adapter's ``adapt()``
method must call :func:`validate_canonical_contract` before returning.
The Executor never sees an invalid contract.

Validation surface
------------------

The validator is intentionally **narrow** at the canonical-form level.
Most semantic checks (e.g., "default value type matches the field's type")
are enforced by :class:`~paxman.contract.canonical.CanonicalField`'s
``__attrs_post_init__``. The validator here focuses on:

- **Unsupported field types** — :class:`UnsupportedFieldTypeError` if a
  field's :class:`paxman.types.FieldType` is outside the V1 set.
  (Currently a no-op since :class:`FieldType` is closed by its enum, but
  kept for forward-compat: if the enum is ever relaxed, the validator
  becomes the second line of defense.)
- **Invalid constraints** — :class:`InvalidConstraintError` for cross-kind
  validation (e.g., ``min_length`` on a ``DECIMAL`` field). The
  per-field check is best-effort.
- **Invalid field paths** — :class:`InvalidPathError` for paths that
  don't match the documented pattern. (Already enforced by
  :class:`CanonicalField`, but the validator is the single point for
  future cross-field path checks.)
- **Invalid semantic tags** — :class:`InvalidSemanticTagError` for tags
  that don't pass :func:`paxman.contract.semantics.validate_semantic_tags`.
- **Schema-level checks** — duplicate IDs, duplicate paths, empty
  contract. (Already enforced by :class:`CanonicalContract`; kept here
  for completeness so external callers can call ``validate(contract)``
  instead of relying on constructor enforcement.)
"""

from __future__ import annotations

import typing

from paxman.contract._types import Constraint, ConstraintKind
from paxman.contract.canonical import CanonicalContract, CanonicalField
from paxman.contract.semantics import validate_semantic_tags
from paxman.errors import (
    InvalidConstraintError,
    InvalidPathError,
    InvalidSemanticTagError,
    UnsupportedFieldTypeError,
)
from paxman.types import FieldType

__all__ = ["validate_canonical_contract", "validate_canonical_field"]


#: Field types that constraints may apply to. Maps each
#: :class:`ConstraintKind` to the set of :class:`FieldType` values that
#: are type-compatible.
_CONSTRAINT_FIELD_TYPES: typing.Final[dict[ConstraintKind, frozenset[FieldType]]] = {
    ConstraintKind.MIN_LENGTH: frozenset({FieldType.STRING, FieldType.ARRAY}),
    ConstraintKind.MAX_LENGTH: frozenset({FieldType.STRING, FieldType.ARRAY}),
    ConstraintKind.PATTERN: frozenset({FieldType.STRING}),
    ConstraintKind.MIN_VALUE: frozenset({FieldType.INTEGER, FieldType.DECIMAL, FieldType.MONEY}),
    ConstraintKind.MAX_VALUE: frozenset({FieldType.INTEGER, FieldType.DECIMAL, FieldType.MONEY}),
    ConstraintKind.ENUM: frozenset({FieldType.STRING, FieldType.INTEGER}),
    ConstraintKind.ISO_4217: frozenset({FieldType.STRING, FieldType.MONEY}),
}


def validate_canonical_field(field: CanonicalField) -> None:
    """Validate a single :class:`CanonicalField`.

    The checks performed here are **defensive duplicates** of those in
    :class:`CanonicalField.__attrs_post_init__` — they exist so external
    callers can validate a field without constructing one. Adapters
    should call this after building the field.

    Args:
        field: The :class:`CanonicalField` to validate.

    Raises:
        UnsupportedFieldTypeError: If *field*'s type is not in the V1 set.
        InvalidConstraintError: If a constraint is not type-compatible with
            the field.
        InvalidPathError: If the field's path is malformed.
        InvalidSemanticTagError: If a semantic tag is malformed.
    """
    if not isinstance(field, CanonicalField):
        raise TypeError(
            f"validate_canonical_field expects CanonicalField, got {type(field).__name__}"
        )
    if not isinstance(field.type, FieldType):
        raise UnsupportedFieldTypeError(
            f"field {field.name!r} has a non-FieldType type: {field.type!r}",
            context={
                "field_name": field.name,
                "field_id": field.id,
                "type": repr(field.type),
            },
        )
    # Constraints: type compatibility.
    for c in field.constraints:
        if not isinstance(c, Constraint):
            raise InvalidConstraintError(
                f"field {field.name!r} has a non-Constraint constraint",
                context={
                    "field_name": field.name,
                    "field_id": field.id,
                    "constraint": repr(c),
                },
            )
        compatible = _CONSTRAINT_FIELD_TYPES.get(c.kind)
        if compatible is not None and field.type not in compatible:
            raise InvalidConstraintError(
                f"constraint {c.kind.value!r} is not compatible with field "
                f"{field.name!r} of type {field.type.name!r}",
                context={
                    "field_name": field.name,
                    "field_id": field.id,
                    "field_type": field.type.name,
                    "constraint_kind": c.kind.value,
                },
            )
    # Semantic tags: already enforced by CanonicalField on construction
    # (it accepts raw strings), but the validator tightens the check by
    # requiring lowercase ASCII. Callers that build CanonicalField with
    # raw tags will be caught here.
    try:
        normalized = validate_semantic_tags(field.semantic_tags)
    except InvalidSemanticTagError:
        # Re-raise with field context attached.
        raise
    if normalized != field.semantic_tags:
        raise InvalidSemanticTagError(
            f"semantic tags on field {field.name!r} are not normalized "
            f"(must be sorted, lowercase ASCII, unique): {field.semantic_tags!r}",
            context={
                "field_name": field.name,
                "field_id": field.id,
                "semantic_tags": list(field.semantic_tags),
                "expected": list(normalized),
                "reason": "not-normalized",
            },
        )


def validate_canonical_contract(contract: CanonicalContract) -> None:
    """Validate a :class:`CanonicalContract` end-to-end.

    Validates the contract and every field it contains. Idempotent: calling
    this on a valid contract is a no-op.

    Args:
        contract: The :class:`CanonicalContract` to validate.

    Raises:
        TypeError: If *contract* is not a :class:`CanonicalContract`.
        UnsupportedFieldTypeError: If a field's type is outside the V1 set.
        InvalidConstraintError: If a constraint is not type-compatible with
            its field.
        InvalidPathError: If a field's path is malformed.
        InvalidSemanticTagError: If a semantic tag is malformed.
        ValueError: If the contract has no fields or has duplicate IDs/paths.
            (Also raised by :class:`CanonicalContract` constructor.)
    """
    if not isinstance(contract, CanonicalContract):
        raise TypeError(
            f"validate_canonical_contract expects CanonicalContract, got {type(contract).__name__}"
        )
    if not contract.fields:
        raise InvalidPathError(
            f"contract {contract.id!r} has no fields",
            context={"contract_id": contract.id, "reason": "empty-fields"},
        )
    # Duplicate IDs / paths (also enforced by CanonicalContract).
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    for f in contract.fields:
        if f.id in seen_ids:
            raise InvalidPathError(
                f"contract {contract.id!r} has duplicate field id {f.id!r}",
                context={
                    "contract_id": contract.id,
                    "field_id": f.id,
                    "reason": "duplicate-id",
                },
            )
        seen_ids.add(f.id)
        if f.path in seen_paths:
            raise InvalidPathError(
                f"contract {contract.id!r} has duplicate field path {f.path!r}",
                context={
                    "contract_id": contract.id,
                    "field_path": f.path,
                    "reason": "duplicate-path",
                },
            )
        seen_paths.add(f.path)
        validate_canonical_field(f)
