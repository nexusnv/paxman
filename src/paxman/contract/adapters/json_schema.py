"""JSON Schema (draft 2020-12) adapter — JSON Schema dict ↔ ``CanonicalContract``.

The adapter translates a JSON Schema document (a Python ``dict``) into a
:class:`~paxman.contract.canonical.CanonicalContract` and back. The
**primary target** is draft 2020-12, with earlier drafts handled
best-effort (per ``PACKAGE_STRUCTURE.md`` §3.4).

MONEY representation
-------------------

JSON Schema has no native MONEY type. Per the Sprint 2 risk register, the
adapter supports two equivalent MONEY representations:

1. **Explicit Paxman extension** (recommended): a schema that adds
   ``"x-paxman-type": "MONEY"`` to a string field whose ``pattern`` is a
   3-letter-currency code. The string value is the **currency code**;
   the field is treated as a money currency. To express a full
   MONEY (amount + currency), use a JSON Schema ``object`` with the
   ``"x-paxman-type"`` extension at the object level.
2. **Heuristic fallback**: a string field with ``format: "currency"``
   and a 3-letter-currency pattern is mapped to MONEY heuristically.

V1 supports the ``object`` form (recommended). The string form is
accepted as a ``STRING`` with ``iso_4217`` and ``currency-sensitive``
tags.

V1 type mapping (draft 2020-12 → ``FieldType``):

- ``"string"`` with ``format: "date"`` or ``"date-time"`` → ``DATE``
- ``"string"`` with ``"x-paxman-type": "MONEY"`` at the object level → ``MONEY``
- ``"string"`` → ``STRING``
- ``"integer"`` → ``INTEGER``
- ``"number"`` → ``DECIMAL``
- ``"boolean"`` → ``BOOLEAN``
- ``"null"`` → ``nullable`` flag (no separate type)
- ``"array"`` → ``ARRAY``
- ``"object"`` → ``OBJECT``
- ``"enum": [...]`` → ``ENUM`` (with ``enum_values``)

V1 constraint mapping:

- ``"minLength"`` → ``MIN_LENGTH``
- ``"maxLength"`` → ``MAX_LENGTH``
- ``"pattern"`` → ``PATTERN``
- ``"minimum"`` / ``"exclusiveMinimum"`` → ``MIN_VALUE`` (inclusive flag preserved)
- ``"maximum"`` / ``"exclusiveMaximum"`` → ``MAX_VALUE``
- ``"enum"`` → ``ENUM`` (also drives the ENUM type detection)
- ``"minItems"`` / ``"maxItems"`` → ``MIN_LENGTH`` / ``MAX_LENGTH`` on ``ARRAY``

V1 reject-list (V2 features; explicitly rejected to fail fast instead of
silently dropping information):

- ``"const"`` — has no V1 canonical equivalent; rejected with
  ``UNSUPPORTED_JSON_SCHEMA_FEATURE``. Use ``"enum": [<literal>]`` to
  express a single-value constraint.
- ``"oneOf"`` / ``"anyOf"`` / ``"allOf"`` — composition is V2; rejected
  with ``UNSUPPORTED_JSON_SCHEMA_FEATURE``.
- ``"$ref"`` — reference resolution is V2 (use the Pydantic adapter for
  shared models); rejected with ``UNSUPPORTED_JSON_SCHEMA_FEATURE``.
- ``"additionalProperties"`` — not enforced in V1; accepted but not
  honored. ``UNSUPPORTED_JSON_SCHEMA_FEATURE`` is raised only when set
  to ``false`` (which would imply a constraint we cannot represent).

Error model
-----------

Every error raised is :class:`paxman.errors.InvalidContractError` with
one of the following ``error_code`` values:

- ``UNSUPPORTED_FIELD_TYPE`` — the JSON Schema ``type`` is not in the V1 set.
- ``INVALID_CONSTRAINT`` — a constraint is malformed (e.g., wrong type).
- ``INVALID_FIELD`` — the field shape is wrong.
- ``INVALID_VERSION`` — the ``$schema`` is unrecognized.
- ``UNSUPPORTED_JSON_SCHEMA_FEATURE`` — a V2-only keyword (``const``,
  ``oneOf``, ``anyOf``, ``allOf``, ``$ref``, or
  ``additionalProperties: false``) was used. Fail-fast so the caller
  knows the schema is not fully representable in V1.
"""

from __future__ import annotations

import decimal
import re
import typing

import attrs

from paxman.contract._types import (
    Constraint,
    ConstraintKind,
    EnumValueSet,
)
from paxman.contract.canonical import CanonicalContract, CanonicalField, MoneyValue
from paxman.errors import InvalidContractError
from paxman.types import FieldType

__all__ = ["JsonSchemaAdapter"]


# JSON Schema draft URI we explicitly support.
_DRAFT_2020_12: typing.Final[str] = "https://json-schema.org/draft/2020-12/schema"
_DRAFT_07: typing.Final[str] = "http://json-schema.org/draft-07/schema#"
_DRAFT_06: typing.Final[str] = "http://json-schema.org/draft-06/schema#"
_DRAFT_04: typing.Final[str] = "http://json-schema.org/draft-04/schema#"
_DRAFT_2019_09: typing.Final[str] = "https://json-schema.org/draft/2019-09/schema"

_SUPPORTED_DRAFTS: typing.Final[frozenset[str]] = frozenset(
    {_DRAFT_2020_12, _DRAFT_07, _DRAFT_06, _DRAFT_04, _DRAFT_2019_09}
)

# Paxman extension key for MONEY.
_PAXMAN_TYPE_KEY: typing.Final[str] = "x-paxman-type"

# Map of JSON Schema "type" strings to FieldType.
_JSON_TYPE_TO_FIELD_TYPE: typing.Final[dict[str, FieldType]] = {
    "string": FieldType.STRING,
    "integer": FieldType.INTEGER,
    "number": FieldType.DECIMAL,
    "boolean": FieldType.BOOLEAN,
    "array": FieldType.ARRAY,
    "object": FieldType.OBJECT,
}


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


@attrs.frozen(slots=True)
class JsonSchemaAdapter:
    """Adapter for JSON Schema (draft 2020-12, with earlier-draft best-effort).

    Pure and stateless. Same input dict → same :class:`CanonicalContract`.

    Attributes:
        This class has no fields. All methods are pure functions of their
        arguments.
    """

    @property
    def format_id(self) -> str:
        """The adapter's format identifier (targeting draft 2020-12)."""
        return "json_schema:draft-2020-12"

    # ----- adapt ---------------------------------------------------------

    def adapt(self, external: typing.Any) -> CanonicalContract:
        """Translate a JSON Schema dict into a :class:`CanonicalContract`.

        The schema's top level should be an ``object`` with ``properties``
        and (optionally) ``required``. The adapter uses the ``title`` or
        schema ``$id`` for the contract id, falling back to
        ``"untitled"``.

        Args:
            external: A JSON Schema dict (Python literal).

        Returns:
            The :class:`CanonicalContract` representation.

        Raises:
            InvalidContractError: If the schema is malformed.
        """
        if not isinstance(external, dict):
            # Accept JSON Schema as a string (e.g., loaded from a file).
            # Parse it as JSON before continuing.
            if isinstance(external, str):
                try:
                    import json

                    external = json.loads(external)
                except json.JSONDecodeError as e:
                    raise InvalidContractError(
                        f"JSON Schema adapter received a string that is not valid JSON: {e}",
                        error_code="INVALID_JSON",
                        context={"json_error": str(e)},
                    ) from e
            else:
                raise InvalidContractError(
                    f"JSON Schema adapter requires a dict or str, got {type(external).__name__}",
                    error_code="INVALID_FIELD",
                    context={"got_type": type(external).__name__},
                )
        # Check the schema version (best-effort).
        schema_uri = external.get("$schema")
        if schema_uri is not None and schema_uri not in _SUPPORTED_DRAFTS:
            raise InvalidContractError(
                f"unsupported JSON Schema version: {schema_uri!r}",
                error_code="INVALID_VERSION",
                context={"$schema": schema_uri},
            )
        # Top-level: must be an object.
        top_type = external.get("type", "object")
        if top_type != "object":
            raise InvalidContractError(
                f"top-level JSON Schema must be 'object', got {top_type!r}",
                error_code="UNSUPPORTED_FIELD_TYPE",
                context={"type": top_type},
            )
        contract_id = self._extract_contract_id(external)
        properties = external.get("properties", {})
        if not isinstance(properties, dict):
            raise InvalidContractError(
                f"schema {contract_id!r} 'properties' must be a dict",
                error_code="INVALID_FIELD",
                context={"contract_id": contract_id},
            )
        required_list = external.get("required", [])
        if not isinstance(required_list, list):
            raise InvalidContractError(
                f"schema {contract_id!r} 'required' must be a list",
                error_code="INVALID_FIELD",
                context={"contract_id": contract_id},
            )
        # Oracle review F6: validate that every required entry is a string.
        # Silently filtering non-strings hides malformed schemas.
        for i, item in enumerate(required_list):
            if not isinstance(item, str):
                raise InvalidContractError(
                    f"schema {contract_id!r} 'required[{i}]' must be a string, "
                    f"got {type(item).__name__}: {item!r}",
                    error_code="INVALID_FIELD",
                    context={
                        "contract_id": contract_id,
                        "index": i,
                        "value": repr(item),
                    },
                )
        required_set = set(required_list)
        fields: list[CanonicalField] = []
        for prop_name, prop_schema in properties.items():
            if not isinstance(prop_schema, dict):
                raise InvalidContractError(
                    f"property {prop_name!r} in {contract_id!r} is not a dict",
                    error_code="INVALID_FIELD",
                    context={"contract_id": contract_id, "property": prop_name},
                )
            fields.append(
                self._adapt_property(
                    prop_name,
                    prop_schema,
                    required=prop_name in required_set,
                    contract_id=contract_id,
                )
            )
        if not fields:
            raise InvalidContractError(
                f"schema {contract_id!r} has no properties",
                error_code="INVALID_FIELD",
                context={"contract_id": contract_id},
            )
        return CanonicalContract(id=contract_id, fields=tuple(fields))

    # ----- export --------------------------------------------------------

    def export(self, canonical: CanonicalContract) -> dict[str, typing.Any]:
        """Translate a :class:`CanonicalContract` back into a JSON Schema dict.

        Args:
            canonical: The :class:`CanonicalContract` to export.

        Returns:
            A JSON Schema dict targeting draft 2020-12.
        """
        if not isinstance(canonical, CanonicalContract):
            raise InvalidContractError(
                f"export expects CanonicalContract, got {type(canonical).__name__}",
                error_code="INVALID_FIELD",
                context={"got_type": type(canonical).__name__},
            )
        properties: dict[str, typing.Any] = {}
        required: list[str] = []
        for f in canonical.fields:
            properties[f.name] = self._export_property(f)
            if f.required:
                required.append(f.name)
        schema: dict[str, typing.Any] = {
            "$schema": _DRAFT_2020_12,
            "title": canonical.id,
            "type": "object",
            "properties": properties,
        }
        if required:
            schema["required"] = required
        return schema

    # =====================================================================
    # Internal: top-level helpers
    # =====================================================================

    @staticmethod
    def _extract_contract_id(external: dict[str, typing.Any]) -> str:
        """Extract the contract id from a JSON Schema's ``$id``, ``title``, or fallback."""
        cid = external.get("title")
        if cid:
            return str(cid)
        cid = external.get("$id")
        if cid:
            # Take the last path segment.
            return str(cid).rsplit("/", 1)[-1] or "untitled"
        return "untitled"

    # =====================================================================
    # Internal: per-property adaptation
    # =====================================================================

    def _adapt_property(
        self,
        name: str,
        schema: dict[str, typing.Any],
        *,
        required: bool,
        contract_id: str,
    ) -> CanonicalField:
        """Adapt a single JSON Schema property to :class:`CanonicalField`."""
        # Fail fast on V2-only keywords (Oracle review F3/F8). The V1 canonical
        # model cannot represent these and silently dropping them would lose
        # information; explicit rejection tells the caller the schema is
        # not fully representable in V1.
        for keyword in ("const", "oneOf", "anyOf", "allOf", "$ref"):
            if keyword in schema:
                raise InvalidContractError(
                    f"property {name!r} in {contract_id!r} uses V2-only keyword "
                    f"{keyword!r}; not supported by the V1 JSON Schema adapter",
                    error_code="UNSUPPORTED_JSON_SCHEMA_FEATURE",
                    context={
                        "contract_id": contract_id,
                        "property": name,
                        "keyword": keyword,
                    },
                )
        # additionalProperties: false is a constraint we cannot represent; reject.
        if schema.get("additionalProperties") is False:
            raise InvalidContractError(
                f"property {name!r} in {contract_id!r} uses "
                "'additionalProperties: false', which is not enforced in V1",
                error_code="UNSUPPORTED_JSON_SCHEMA_FEATURE",
                context={
                    "contract_id": contract_id,
                    "property": name,
                    "keyword": "additionalProperties",
                },
            )
        # Detect MONEY via x-paxman-type.
        if schema.get(_PAXMAN_TYPE_KEY) == "MONEY":
            return self._adapt_money_property(
                name, schema, required=required, contract_id=contract_id
            )
        # Detect ENUM via "enum" keyword.
        if "enum" in schema:
            return self._adapt_enum_property(
                name, schema, required=required, contract_id=contract_id
            )
        # Detect DATE via format.
        fmt = schema.get("format")
        if fmt in ("date", "date-time") or (
            schema.get("type") == "string"
            and fmt
            in (
                "date",
                "date-time",
            )
        ):
            return self._adapt_date_property(
                name, schema, required=required, contract_id=contract_id
            )
        # Detect DATE when type is string and format is date / date-time.
        if (
            schema.get("type") == "string"
            and isinstance(fmt, str)
            and fmt
            in (
                "date",
                "date-time",
            )
        ):
            return self._adapt_date_property(
                name, schema, required=required, contract_id=contract_id
            )
        # Map type.
        json_type = schema.get("type", "string")
        # Oracle review F9: handle list types like ``["string", "null"]`` (the
        # form export() produces for nullable fields). Extract the non-null
        # type and set ``nullable=True``.
        if isinstance(json_type, list):
            non_null = [t for t in json_type if t != "null"]
            nullable = "null" in json_type
            if not non_null:
                raise InvalidContractError(
                    f"property {name!r} in {contract_id!r} has empty type array",
                    error_code="INVALID_FIELD",
                    context={"contract_id": contract_id, "property": name, "type": json_type},
                )
            if len(non_null) > 1:
                raise InvalidContractError(
                    f"property {name!r} in {contract_id!r} has multiple non-null types "
                    f"in type array: {non_null!r}",
                    error_code="UNSUPPORTED_JSON_SCHEMA_FEATURE",
                    context={"contract_id": contract_id, "property": name, "type": json_type},
                )
            json_type = non_null[0]
        else:
            nullable = False
        # "null" means nullable.
        if json_type == "null":
            field_type: FieldType = FieldType.STRING
            nullable = True
            required_flag = False
        else:
            field_type_candidate = _JSON_TYPE_TO_FIELD_TYPE.get(json_type)
            if field_type_candidate is None:
                raise InvalidContractError(
                    f"property {name!r} in {contract_id!r} has unsupported type: {json_type!r}",
                    error_code="UNSUPPORTED_FIELD_TYPE",
                    context={
                        "contract_id": contract_id,
                        "property": name,
                        "type": json_type,
                    },
                )
            field_type = field_type_candidate
            required_flag = required
        # Build constraints.
        constraints = self._extract_constraints(name, schema, field_type, contract_id)
        # Optional default.
        default: typing.Any = schema.get("default")
        return CanonicalField(
            id=f"field_{contract_id}_{name}",
            path=name,
            name=name,
            type=field_type,
            required=required_flag,
            nullable=nullable,
            description=schema.get("description") or schema.get("title"),
            default=default,
            constraints=tuple(constraints),
        )

    def _adapt_enum_property(
        self,
        name: str,
        schema: dict[str, typing.Any],
        *,
        required: bool,
        contract_id: str,
    ) -> CanonicalField:
        """Adapt a property with an ``enum`` keyword to an ENUM field."""
        raw_values = schema["enum"]
        if not isinstance(raw_values, list):
            raise InvalidContractError(
                f"ENUM property {name!r} 'enum' must be a list",
                error_code="INVALID_FIELD",
                context={"contract_id": contract_id, "property": name},
            )
        enum_values = EnumValueSet(tuple(raw_values))
        # Determine the underlying type: string-typed enums are common; treat
        # them as STRING with ENUM constraints. Numeric enums are INTEGER.
        # The canonical form uses FieldType.ENUM and carries enum_values.
        return CanonicalField(
            id=f"field_{contract_id}_{name}",
            path=name,
            name=name,
            type=FieldType.ENUM,
            required=required,
            description=schema.get("description") or schema.get("title"),
            default=schema.get("default"),
            constraints=(
                Constraint(kind=ConstraintKind.ENUM, params={"values": list(enum_values)}),
            ),
            enum_values=enum_values,
        )

    def _adapt_date_property(
        self,
        name: str,
        schema: dict[str, typing.Any],
        *,
        required: bool,
        contract_id: str,
    ) -> CanonicalField:
        """Adapt a string-typed date/datetime property to DATE."""
        return CanonicalField(
            id=f"field_{contract_id}_{name}",
            path=name,
            name=name,
            type=FieldType.DATE,
            required=required,
            description=schema.get("description") or schema.get("title"),
            default=schema.get("default"),
            constraints=(),
        )

    def _adapt_money_property(
        self,
        name: str,
        schema: dict[str, typing.Any],
        *,
        required: bool,
        contract_id: str,
    ) -> CanonicalField:
        """Adapt an object-typed MONEY property (x-paxman-type=MONEY)."""
        if schema.get("type") != "object":
            raise InvalidContractError(
                f"MONEY property {name!r} must be an object with 'amount' and 'currency'",
                error_code="UNSUPPORTED_FIELD_TYPE",
                context={"contract_id": contract_id, "property": name},
            )
        props = schema.get("properties", {})
        if "amount" not in props or "currency" not in props:
            raise InvalidContractError(
                f"MONEY property {name!r} must have 'amount' and 'currency' subfields",
                error_code="INVALID_FIELD",
                context={"contract_id": contract_id, "property": name},
            )
        # Optional default.
        default: typing.Any = None
        if "default" in schema and isinstance(schema["default"], dict):
            amt = schema["default"].get("amount")
            cur = schema["default"].get("currency")
            if amt is not None and cur is not None:
                try:
                    default = MoneyValue(
                        amount=decimal.Decimal(str(amt)),
                        currency=str(cur),
                    )
                except (ValueError, TypeError, decimal.DecimalException) as e:
                    # Oracle review F7: don't let raw decimal exceptions leak.
                    # ``decimal.InvalidOperation`` is a ``DecimalException`` (an
                    # ``ArithmeticError``) — not a ``ValueError`` — so we must
                    # catch ``DecimalException`` explicitly.
                    # Raise a structured InvalidContractError instead.
                    raise InvalidContractError(
                        f"MONEY property {name!r} in {contract_id!r} has invalid default "
                        f"value: amount={amt!r}, currency={cur!r}",
                        error_code="INVALID_FIELD",
                        context={
                            "contract_id": contract_id,
                            "property": name,
                            "amount": repr(amt),
                            "currency": repr(cur),
                            "decimal_error": type(e).__name__,
                        },
                    ) from e
        return CanonicalField(
            id=f"field_{contract_id}_{name}",
            path=name,
            name=name,
            type=FieldType.MONEY,
            required=required,
            description=schema.get("description") or schema.get("title"),
            default=default,
            constraints=(Constraint(kind=ConstraintKind.ISO_4217, params={}),),
        )

    def _extract_constraints(
        self,
        name: str,
        schema: dict[str, typing.Any],
        field_type: FieldType,
        contract_id: str,
    ) -> list[Constraint]:
        """Extract a list of :class:`Constraint` from a JSON Schema property."""
        out: list[Constraint] = []
        ctx = {"contract_id": contract_id, "property": name}
        # Length
        if field_type in (FieldType.STRING, FieldType.ARRAY):
            if "minLength" in schema:
                ml = schema["minLength"]
                if not isinstance(ml, int) or ml < 0:
                    raise InvalidContractError(
                        f"property {name!r} 'minLength' must be a non-negative int",
                        error_code="INVALID_CONSTRAINT",
                        context=ctx,
                    )
                out.append(Constraint(kind=ConstraintKind.MIN_LENGTH, params={"min": ml}))
            if "maxLength" in schema:
                ml = schema["maxLength"]
                if not isinstance(ml, int) or ml < 0:
                    raise InvalidContractError(
                        f"property {name!r} 'maxLength' must be a non-negative int",
                        error_code="INVALID_CONSTRAINT",
                        context=ctx,
                    )
                out.append(Constraint(kind=ConstraintKind.MAX_LENGTH, params={"max": ml}))
            # minItems / maxItems map to MIN/MAX_LENGTH for arrays.
            if "minItems" in schema and field_type is FieldType.ARRAY:
                mi = schema["minItems"]
                # Oracle review F8: validate before int() coercion. ``int("1.5")``
                # silently truncates; ``int("abc")`` raises raw ``ValueError``;
                # ``int(True)`` would be accepted as 1.
                if not isinstance(mi, int) or isinstance(mi, bool) or mi < 0:
                    raise InvalidContractError(
                        f"property {name!r} 'minItems' must be a non-negative int, got {mi!r}",
                        error_code="INVALID_CONSTRAINT",
                        context={**ctx, "value": repr(mi)},
                    )
                out.append(
                    Constraint(
                        kind=ConstraintKind.MIN_LENGTH,
                        params={"min": mi},
                    )
                )
            if "maxItems" in schema and field_type is FieldType.ARRAY:
                ma = schema["maxItems"]
                if not isinstance(ma, int) or isinstance(ma, bool) or ma < 0:
                    raise InvalidContractError(
                        f"property {name!r} 'maxItems' must be a non-negative int, got {ma!r}",
                        error_code="INVALID_CONSTRAINT",
                        context={**ctx, "value": repr(ma)},
                    )
                out.append(
                    Constraint(
                        kind=ConstraintKind.MAX_LENGTH,
                        params={"max": ma},
                    )
                )
        # Pattern
        if "pattern" in schema and field_type is FieldType.STRING:
            pat = schema["pattern"]
            if not isinstance(pat, str):
                raise InvalidContractError(
                    f"property {name!r} 'pattern' must be a string",
                    error_code="INVALID_CONSTRAINT",
                    context=ctx,
                )
            try:
                re.compile(pat)
            except re.error as e:
                raise InvalidContractError(
                    f"property {name!r} 'pattern' is invalid: {e}",
                    error_code="INVALID_CONSTRAINT",
                    context={**ctx, "pattern": pat, "error": str(e)},
                ) from e
            out.append(Constraint(kind=ConstraintKind.PATTERN, params={"regex": pat}))
        # Numeric
        if field_type in (FieldType.INTEGER, FieldType.DECIMAL):
            if "minimum" in schema:
                out.append(
                    Constraint(
                        kind=ConstraintKind.MIN_VALUE,
                        params={"min": schema["minimum"], "inclusive": True},
                    )
                )
            elif "exclusiveMinimum" in schema:
                out.append(
                    Constraint(
                        kind=ConstraintKind.MIN_VALUE,
                        params={"min": schema["exclusiveMinimum"], "inclusive": False},
                    )
                )
            if "maximum" in schema:
                out.append(
                    Constraint(
                        kind=ConstraintKind.MAX_VALUE,
                        params={"max": schema["maximum"], "inclusive": True},
                    )
                )
            elif "exclusiveMaximum" in schema:
                out.append(
                    Constraint(
                        kind=ConstraintKind.MAX_VALUE,
                        params={"max": schema["exclusiveMaximum"], "inclusive": False},
                    )
                )
        return out

    # =====================================================================
    # Internal: per-property export
    # =====================================================================

    def _export_property(self, f: CanonicalField) -> dict[str, typing.Any]:
        """Translate a :class:`CanonicalField` back to a JSON Schema property."""
        if f.type is FieldType.MONEY:
            return self._export_money_property(f)
        if f.type is FieldType.ENUM:
            if f.enum_values is None:
                raise InvalidContractError(
                    f"ENUM field {f.name!r} has no enum_values",
                    error_code="INVALID_FIELD",
                    context={"field_name": f.name},
                )
            out: dict[str, typing.Any] = {
                "type": "string",
                "enum": list(f.enum_values),
            }
            if f.description is not None:
                out["description"] = f.description
            return out
        if f.type is FieldType.DATE:
            out = {"type": "string", "format": "date"}
            if f.description is not None:
                out["description"] = f.description
            return out
        out = {"type": _FIELD_TYPE_TO_JSON_TYPE[f.type]}
        if f.nullable:
            # In draft 2020-12, nullable is expressed via type array.
            out["type"] = [out["type"], "null"]
        if f.description is not None:
            out["description"] = f.description
        if f.default is not None:
            out["default"] = f.default
        for c in f.constraints:
            self._export_constraint(c, out)
        return out

    def _export_money_property(self, f: CanonicalField) -> dict[str, typing.Any]:
        out: dict[str, typing.Any] = {
            _PAXMAN_TYPE_KEY: "MONEY",
            "type": "object",
            "properties": {
                "amount": {"type": "string", "pattern": r"^-?\d+(\.\d+)?"},
                "currency": {"type": "string", "pattern": r"^[A-Z]{3}$"},
            },
            "required": ["amount", "currency"],
        }
        if f.description is not None:
            out["description"] = f.description
        if isinstance(f.default, MoneyValue):
            out["default"] = {
                "amount": str(f.default.amount),
                "currency": f.default.currency,
            }
        return out

    @staticmethod
    def _export_constraint(c: Constraint, schema: dict[str, typing.Any]) -> None:
        """Add a JSON Schema kwarg for the given constraint."""
        if c.kind is ConstraintKind.MIN_LENGTH:
            if schema.get("type") == "array":
                schema["minItems"] = c.params["min"]
            else:
                schema["minLength"] = c.params["min"]
        elif c.kind is ConstraintKind.MAX_LENGTH:
            if schema.get("type") == "array":
                schema["maxItems"] = c.params["max"]
            else:
                schema["maxLength"] = c.params["max"]
        elif c.kind is ConstraintKind.PATTERN:
            schema["pattern"] = c.params["regex"]
        elif c.kind is ConstraintKind.MIN_VALUE:
            if c.params.get("inclusive", True):
                schema["minimum"] = c.params["min"]
            else:
                schema["exclusiveMinimum"] = c.params["min"]
        elif c.kind is ConstraintKind.MAX_VALUE:
            if c.params.get("inclusive", True):
                schema["maximum"] = c.params["max"]
            else:
                schema["exclusiveMaximum"] = c.params["max"]
        # ENUM and ISO_4217 are encoded into the property structure directly.


_FIELD_TYPE_TO_JSON_TYPE: typing.Final[dict[FieldType, str]] = {
    FieldType.STRING: "string",
    FieldType.INTEGER: "integer",
    FieldType.DECIMAL: "number",
    FieldType.BOOLEAN: "boolean",
    FieldType.OBJECT: "object",
    FieldType.ARRAY: "array",
    # MONEY/ENUM/DATE handled separately.
}


# Self-register.
def _register_on_import() -> None:
    from paxman.contract import registry

    registry.register(JsonSchemaAdapter(), replace=True)


_register_on_import()
