"""Dict DSL adapter — Paxman's internal escape-hatch contract format.

The Dict DSL is the V1 contract format that maps directly to
:class:`~paxman.contract.canonical.CanonicalContract`. It is defined
authoritatively in ``docs/specs/dict-dsl-spec.md`` (Sprint 0, ADR-0009).

The adapter is a **pure recursive dict-walk** (~250 lines). The grammar,
the five concepts (``FieldSpec``, ``Constraint``, ``Tag``, ``Policy``,
``Contract``), and the 13 documented ``error_code`` values are all
specified by the linked spec; this module implements them.

Invariants
----------

- The adapter is pure: same input dict → same :class:`CanonicalContract`.
- Every error raised is an :class:`paxman.errors.InvalidContractError`
  with one of the 13 documented ``error_code`` values.
- The adapter never mutates its input (it copies what it needs).
- The adapter never reads the clock, network, or filesystem.

Format
------

The V1 format is a Python literal ``dict``. The shape is:

    {
        "id": "<str>",
        "version": "1",  # optional, default "1"
        "fields": [
            {
                "name": "<str>",
                "type": "STRING" | "INTEGER" | ... | "MONEY",
                "required": <bool>,
                "description": "<str>"?,  # optional
                "tags": ["<str>", ...]?,  # optional
                "default": <typed_value>?,  # optional
                "constraints": [{"kind": "...", "params": {...}}, ...]?,  # optional
            },
            ...
        ],
        "constraints": [<constraint>, ...]?,  # optional, contract-level
        "policy": {  # optional
            "confidence_floor": <float>?,
            "unresolved_acceptable": <bool>?,
            "stop_on_first_unresolved": <bool>?,
        },
    }

See ``docs/specs/dict-dsl-spec.md`` for the BNF grammar, 3 worked
examples, 6 edge cases, and the full error model.
"""

from __future__ import annotations

import decimal
import re
import typing

import attrs

from paxman.contract._types import (
    Constraint,
    ConstraintKind,
    ContractPolicy,
    EnumValueSet,
)
from paxman.contract.canonical import CanonicalContract, CanonicalField, MoneyValue
from paxman.errors import InvalidContractError
from paxman.types import FieldType

__all__ = ["DictDSLAdapter"]


# ISO-4217 currency code pattern: 3 uppercase ASCII letters.
_ISO_4217_RE: typing.Final[re.Pattern[str]] = re.compile(r"^[A-Z]{3}$")

# Tag pattern: lowercase ASCII, hyphen-separated. V1 convention.
_TAG_RE: typing.Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9-]*$")

# Mapping from Dict DSL type literal to FieldType.
_TYPE_LITERAL_TO_FIELD_TYPE: typing.Final[dict[str, FieldType]] = {
    "STRING": FieldType.STRING,
    "INTEGER": FieldType.INTEGER,
    "DECIMAL": FieldType.DECIMAL,
    "BOOLEAN": FieldType.BOOLEAN,
    "DATE": FieldType.DATE,
    "ENUM": FieldType.ENUM,
    "OBJECT": FieldType.OBJECT,
    "ARRAY": FieldType.ARRAY,
    "MONEY": FieldType.MONEY,
}

# Mapping from ConstraintKind to its required param keys (for validation).
_CONSTRAINT_PARAM_KEYS: typing.Final[dict[ConstraintKind, frozenset[str]]] = {
    ConstraintKind.MIN_LENGTH: frozenset({"min"}),
    ConstraintKind.MAX_LENGTH: frozenset({"max"}),
    ConstraintKind.PATTERN: frozenset({"regex"}),
    ConstraintKind.MIN_VALUE: frozenset({"min"}),
    ConstraintKind.MAX_VALUE: frozenset({"max"}),
    ConstraintKind.ENUM: frozenset({"values"}),
    ConstraintKind.ISO_4217: frozenset(),
}


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


@attrs.frozen(slots=True)
class DictDSLAdapter:
    """Adapter for Paxman's internal Dict DSL contract format.

    Implements the :class:`paxman.contract.adapters.base.ContractAdapter`
    Protocol. The adapter is stateless and side-effect-free; it can be
    shared across threads.

    Attributes:
        This class has no fields. All methods are pure functions of their
        arguments.

    Examples:
        >>> from paxman.contract.adapters.dict_dsl import DictDSLAdapter
        >>> from paxman.contract.canonical import CanonicalContract
        >>> adapter = DictDSLAdapter()
        >>> contract = adapter.adapt({
        ...     "id": "user",
        ...     "fields": [
        ...         {"name": "age", "type": "INTEGER", "required": True},
        ...     ],
        ... })
        >>> contract.id
        'user'
        >>> contract.fields[0].name
        'age'
    """

    @property
    def format_id(self) -> str:
        """The adapter's format identifier."""
        return "dict_dsl"

    # ----- adapt ---------------------------------------------------------

    def adapt(self, external: object) -> CanonicalContract:
        """Translate a Dict DSL dict into a :class:`CanonicalContract`.

        Args:
            external: A Python ``dict`` matching the Dict DSL grammar
                (see module docstring and ``docs/specs/dict-dsl-spec.md``).

        Returns:
            The :class:`CanonicalContract` representation.

        Raises:
            InvalidContractError: If *external* is not a valid Dict DSL
                contract. The error's ``error_code`` is one of the 13
                documented values (see ``docs/specs/dict-dsl-spec.md`` §7).
        """
        if not isinstance(external, dict):
            raise InvalidContractError(
                "Dict DSL contract must be a dict",
                error_code="MISSING_CONTRACT_ID",
                context={"got_type": type(external).__name__},
            )
        contract_id = self._extract_contract_id(external)
        version = self._extract_version(external)
        raw_fields = self._extract_fields(external)
        if not raw_fields:
            raise InvalidContractError(
                f"contract {contract_id!r} has no fields",
                error_code="EMPTY_FIELDS",
                context={"contract_id": contract_id},
            )
        # Parse fields, checking for duplicate names.
        seen_names: set[str] = set()
        canonical_fields: list[CanonicalField] = []
        for index, raw_field in enumerate(raw_fields):
            field = self._parse_field(raw_field, contract_id=contract_id, field_index=index)
            if field.name in seen_names:
                raise InvalidContractError(
                    f"contract {contract_id!r} has duplicate field name {field.name!r}",
                    error_code="DUPLICATE_FIELD",
                    context={
                        "contract_id": contract_id,
                        "field_name": field.name,
                    },
                )
            seen_names.add(field.name)
            canonical_fields.append(field)
        # Contract-level constraints (V2 feature; accepted but not enforced).
        raw_constraints = external.get("constraints", [])
        if not isinstance(raw_constraints, list):
            raise InvalidContractError(
                f"contract {contract_id!r} has non-list 'constraints'",
                error_code="INVALID_CONSTRAINT",
                context={"contract_id": contract_id},
            )
        canonical_constraints: list[Constraint] = []
        for raw_c in raw_constraints:
            canonical_constraints.append(self._parse_constraint(raw_c, contract_id=contract_id))
        # Contract policy.
        policy: ContractPolicy | None = None
        if "policy" in external:
            policy = self._parse_policy(external["policy"], contract_id=contract_id)
        return CanonicalContract(
            id=contract_id,
            version=version,
            fields=tuple(canonical_fields),
            constraints=tuple(canonical_constraints),
            policies=policy,
        )

    # ----- export --------------------------------------------------------

    def export(self, canonical: CanonicalContract) -> dict[str, typing.Any]:
        """Translate a :class:`CanonicalContract` back to a Dict DSL dict.

        The output is a Python ``dict`` suitable for re-input to
        :meth:`adapt` (round-trippable within the Dict DSL's expressible
        subset).

        Args:
            canonical: The :class:`CanonicalContract` to export.

        Returns:
            A Python ``dict`` matching the Dict DSL grammar.

        Raises:
            InvalidContractError: If *canonical* carries a value the Dict
                DSL cannot represent (e.g., a non-ISO-4217 currency).
        """
        if not isinstance(canonical, CanonicalContract):
            raise InvalidContractError(
                f"export expects CanonicalContract, got {type(canonical).__name__}",
                error_code="INVALID_CONTRACT",
                context={"got_type": type(canonical).__name__},
            )
        out: dict[str, typing.Any] = {
            "id": canonical.id,
            "version": canonical.version,
            "fields": [self._export_field(f) for f in canonical.fields],
        }
        if canonical.constraints:
            out["constraints"] = [self._export_constraint(c) for c in canonical.constraints]
        if canonical.policies is not None:
            out["policy"] = self._export_policy(canonical.policies)
        return out

    # =====================================================================
    # Internal: top-level extraction
    # =====================================================================

    @staticmethod
    def _extract_contract_id(external: dict[str, typing.Any]) -> str:
        """Extract and validate the contract's ``id`` field."""
        if "id" not in external:
            raise InvalidContractError(
                "Dict DSL contract is missing required 'id' key",
                error_code="MISSING_CONTRACT_ID",
                context={"contract_keys": sorted(external.keys())},
            )
        cid = external["id"]
        if not isinstance(cid, str) or not cid:
            raise InvalidContractError(
                f"Dict DSL contract 'id' must be a non-empty string, got {cid!r}",
                error_code="MISSING_CONTRACT_ID",
                context={"id": repr(cid)},
            )
        return cid

    @staticmethod
    def _extract_version(external: dict[str, typing.Any]) -> str:
        """Extract the contract's ``version`` (default: ``"1"``)."""
        version = external.get("version", "1")
        if not isinstance(version, str) or not version:
            raise InvalidContractError(
                f"Dict DSL contract 'version' must be a non-empty string, got {version!r}",
                error_code="INVALID_VERSION",
                context={"version": repr(version)},
            )
        return version

    @staticmethod
    def _extract_fields(external: dict[str, typing.Any]) -> list[typing.Any]:
        """Extract the contract's ``fields`` list."""
        if "fields" not in external:
            raise InvalidContractError(
                "Dict DSL contract is missing required 'fields' key",
                error_code="MISSING_FIELDS",
            )
        fields = external["fields"]
        if not isinstance(fields, list):
            raise InvalidContractError(
                f"Dict DSL contract 'fields' must be a list, got {type(fields).__name__}",
                error_code="MISSING_FIELDS",
                context={"got_type": type(fields).__name__},
            )
        return fields

    # =====================================================================
    # Internal: per-field parsing
    # =====================================================================

    def _parse_field(
        self,
        raw: typing.Any,
        *,
        contract_id: str,
        field_index: int,
    ) -> CanonicalField:
        """Parse a single ``FieldSpec`` dict into a :class:`CanonicalField`."""
        if not isinstance(raw, dict):
            raise InvalidContractError(
                f"field #{field_index} in contract {contract_id!r} is not a dict",
                error_code="INVALID_FIELD",
                context={"contract_id": contract_id, "field_index": field_index},
            )
        # --- name ---
        if "name" not in raw:
            raise InvalidContractError(
                f"field #{field_index} in contract {contract_id!r} is missing 'name'",
                error_code="MISSING_FIELD_NAME",
                context={"contract_id": contract_id, "field_index": field_index},
            )
        name = raw["name"]
        if not isinstance(name, str) or not name:
            raise InvalidContractError(
                f"field #{field_index} in contract {contract_id!r} has invalid 'name'",
                error_code="MISSING_FIELD_NAME",
                context={
                    "contract_id": contract_id,
                    "field_index": field_index,
                    "name": repr(name),
                },
            )
        # --- type ---
        if "type" not in raw:
            raise InvalidContractError(
                f"field {name!r} is missing 'type'",
                error_code="MISSING_TYPE",
                context={"contract_id": contract_id, "field_name": name},
            )
        type_str = raw["type"]
        if not isinstance(type_str, str):
            raise InvalidContractError(
                f"field {name!r} 'type' must be a string, got {type(type_str).__name__}",
                error_code="MISSING_TYPE",
                context={"contract_id": contract_id, "field_name": name},
            )
        field_type = _TYPE_LITERAL_TO_FIELD_TYPE.get(type_str)
        if field_type is None:
            raise InvalidContractError(
                f"field {name!r} has unknown type {type_str!r}",
                error_code="UNKNOWN_FIELD_TYPE",
                context={
                    "contract_id": contract_id,
                    "field_name": name,
                    "type": type_str,
                },
            )
        # --- required ---
        if "required" not in raw:
            raise InvalidContractError(
                f"field {name!r} is missing 'required'",
                error_code="MISSING_REQUIRED_FLAG",
                context={"contract_id": contract_id, "field_name": name},
            )
        required = raw["required"]
        if not isinstance(required, bool):
            raise InvalidContractError(
                f"field {name!r} 'required' must be a bool, got {type(required).__name__}",
                error_code="MISSING_REQUIRED_FLAG",
                context={
                    "contract_id": contract_id,
                    "field_name": name,
                    "got_type": type(required).__name__,
                },
            )
        # --- description ---
        description = raw.get("description")
        if description is not None and not isinstance(description, str):
            raise InvalidContractError(
                f"field {name!r} 'description' must be a string, got {type(description).__name__}",
                error_code="INVALID_FIELD",
                context={
                    "contract_id": contract_id,
                    "field_name": name,
                    "got_type": type(description).__name__,
                },
            )
        # --- semantic tags ---
        tags_list = raw.get("tags", [])
        if not isinstance(tags_list, list):
            raise InvalidContractError(
                f"field {name!r} 'tags' must be a list, got {type(tags_list).__name__}",
                error_code="INVALID_SEMANTIC_TAG",
                context={"contract_id": contract_id, "field_name": name},
            )
        normalized_tags: list[str] = []
        for tag in tags_list:
            if not isinstance(tag, str) or not _TAG_RE.match(tag):
                # Be lenient: known tags are validated, unknown tags are
                # accepted per spec §3.3. But malformed tags (non-string,
                # bad characters) are rejected.
                if not isinstance(tag, str):
                    raise InvalidContractError(
                        f"field {name!r} has non-string tag {tag!r}",
                        error_code="INVALID_SEMANTIC_TAG",
                        context={
                            "contract_id": contract_id,
                            "field_name": name,
                            "tag": repr(tag),
                        },
                    )
                # Tag is a string but doesn't match the lowercase pattern.
                raise InvalidContractError(
                    f"field {name!r} has malformed tag {tag!r} "
                    "(must be lowercase ASCII, hyphen-separated)",
                    error_code="INVALID_SEMANTIC_TAG",
                    context={"contract_id": contract_id, "field_name": name, "tag": tag},
                )
            normalized_tags.append(tag)
        # --- constraints ---
        raw_constraints = raw.get("constraints", [])
        if not isinstance(raw_constraints, list):
            raise InvalidContractError(
                f"field {name!r} 'constraints' must be a list",
                error_code="INVALID_CONSTRAINT",
                context={"contract_id": contract_id, "field_name": name},
            )
        constraints: list[Constraint] = []
        for raw_c in raw_constraints:
            constraints.append(
                self._parse_constraint(raw_c, contract_id=contract_id, field_name=name)
            )
        # --- default ---
        default_value: typing.Any = raw.get("default", None)
        if default_value is not None:
            default_value = self._coerce_default(
                default_value, field_type=field_type, contract_id=contract_id, field_name=name
            )
        # --- ENUM values ---
        enum_values: EnumValueSet | None = None
        if field_type is FieldType.ENUM:
            if "enum_values" in raw:
                enum_values = self._coerce_enum_values(
                    raw["enum_values"], contract_id=contract_id, field_name=name
                )
            else:
                # Look for an ENUM constraint with `values`.
                for c in constraints:
                    if c.kind is ConstraintKind.ENUM:
                        enum_values = EnumValueSet(tuple(c.params["values"]))
                        break
                if enum_values is None:
                    raise InvalidContractError(
                        f"ENUM field {name!r} must have 'enum_values' or an 'enum' constraint",
                        error_code="MISSING_ENUM_VALUES",
                        context={"contract_id": contract_id, "field_name": name},
                    )
        # --- id & path ---
        # In V1 the field id is derived deterministically from the contract
        # id + field name. The canonical form's `id` is a stable string.
        fid = f"field_{contract_id}_{name}"
        return CanonicalField(
            id=fid,
            path=name,
            name=name,
            type=field_type,
            required=required,
            description=description,
            semantic_tags=tuple(normalized_tags),
            constraints=tuple(constraints),
            default=default_value,
            enum_values=enum_values,
        )

    # =====================================================================
    # Internal: constraint parsing
    # =====================================================================

    @staticmethod
    def _parse_constraint(
        raw: typing.Any,
        *,
        contract_id: str,
        field_name: str | None = None,
    ) -> Constraint:
        """Parse a constraint dict into a :class:`Constraint`."""
        if not isinstance(raw, dict):
            raise InvalidContractError(
                f"constraint must be a dict, got {type(raw).__name__}",
                error_code="INVALID_CONSTRAINT",
                context={
                    "contract_id": contract_id,
                    "field_name": field_name,
                    "got_type": type(raw).__name__,
                },
            )
        if "kind" not in raw:
            raise InvalidContractError(
                "constraint is missing 'kind'",
                error_code="UNKNOWN_CONSTRAINT_KIND",
                context={"contract_id": contract_id, "field_name": field_name},
            )
        kind_str = raw["kind"]
        try:
            kind = ConstraintKind(kind_str)
        except ValueError as e:
            raise InvalidContractError(
                f"unknown constraint kind {kind_str!r}",
                error_code="UNKNOWN_CONSTRAINT_KIND",
                context={
                    "contract_id": contract_id,
                    "field_name": field_name,
                    "kind": kind_str,
                },
            ) from e
        params = raw.get("params", {})
        if not isinstance(params, dict):
            raise InvalidContractError(
                f"constraint {kind_str!r} 'params' must be a dict",
                error_code="INVALID_CONSTRAINT",
                context={
                    "contract_id": contract_id,
                    "field_name": field_name,
                    "kind": kind_str,
                },
            )
        # Validate required param keys.
        required_keys = _CONSTRAINT_PARAM_KEYS[kind]
        missing = required_keys - params.keys()
        if missing:
            raise InvalidContractError(
                f"constraint {kind_str!r} is missing required params: {sorted(missing)}",
                error_code="CONSTRAINT_PARAM_MISSING",
                context={
                    "contract_id": contract_id,
                    "field_name": field_name,
                    "kind": kind_str,
                    "missing": sorted(missing),
                },
            )
        # Validate pattern regex (if applicable).
        if kind is ConstraintKind.PATTERN:
            regex = params["regex"]
            if not isinstance(regex, str):
                raise InvalidContractError(
                    "constraint 'pattern' 'regex' must be a string",
                    error_code="INVALID_REGEX_PATTERN",
                    context={
                        "contract_id": contract_id,
                        "field_name": field_name,
                        "regex": repr(regex),
                    },
                )
            try:
                re.compile(regex)
            except re.error as e:
                raise InvalidContractError(
                    f"constraint 'pattern' has invalid regex: {e}",
                    error_code="INVALID_REGEX_PATTERN",
                    context={
                        "contract_id": contract_id,
                        "field_name": field_name,
                        "regex": regex,
                        "parse_error": str(e),
                    },
                ) from e
        # Validate enum values.
        if kind is ConstraintKind.ENUM:
            values = params["values"]
            if not isinstance(values, list):
                raise InvalidContractError(
                    "constraint 'enum' 'values' must be a list",
                    error_code="INVALID_CONSTRAINT",
                    context={
                        "contract_id": contract_id,
                        "field_name": field_name,
                        "kind": kind_str,
                    },
                )
        # ISO_4217 requires no params; accept empty.
        return Constraint(kind=kind, params=dict(params))

    # =====================================================================
    # Internal: default-value coercion
    # =====================================================================

    @staticmethod
    def _coerce_default(
        value: typing.Any,
        *,
        field_type: FieldType,
        contract_id: str,
        field_name: str,
    ) -> typing.Any:
        """Coerce and validate the ``default`` value against the field's type.

        MONEY defaults are validated for shape (must have ``amount`` and
        ``currency``). DECIMAL defaults are coerced to ``Decimal`` from
        string or int.
        """
        ctx = {"contract_id": contract_id, "field_name": field_name}
        if field_type is FieldType.MONEY:
            if not isinstance(value, dict):
                raise InvalidContractError(
                    f"MONEY field {field_name!r} default must be a dict "
                    "with 'amount' and 'currency'",
                    error_code="DEFAULT_TYPE_MISMATCH",
                    context={**ctx, "expected_type": "MONEY", "actual_value": repr(value)},
                )
            if "amount" not in value or "currency" not in value:
                raise InvalidContractError(
                    f"MONEY field {field_name!r} default is missing 'amount' or 'currency'",
                    error_code="MONEY_REQUIRES_CURRENCY",
                    context=ctx,
                )
            currency = value["currency"]
            if not isinstance(currency, str) or not _ISO_4217_RE.match(currency):
                raise InvalidContractError(
                    f"MONEY field {field_name!r} default has invalid currency {currency!r}",
                    error_code="INVALID_ISO_4217",
                    context={**ctx, "currency": repr(currency)},
                )
            try:
                amount = decimal.Decimal(str(value["amount"]))
            except (decimal.InvalidOperation, ValueError, TypeError) as e:
                raise InvalidContractError(
                    f"MONEY field {field_name!r} default has invalid amount {value['amount']!r}",
                    error_code="DEFAULT_TYPE_MISMATCH",
                    context={**ctx, "amount": repr(value["amount"]), "error": str(e)},
                ) from e
            return MoneyValue(amount=amount, currency=currency)
        if field_type is FieldType.DECIMAL:
            if isinstance(value, decimal.Decimal):
                return value
            if isinstance(value, (str, int)):
                try:
                    return decimal.Decimal(str(value))
                except (decimal.InvalidOperation, ValueError) as e:
                    raise InvalidContractError(
                        f"DECIMAL field {field_name!r} default is not a valid number: {value!r}",
                        error_code="DEFAULT_TYPE_MISMATCH",
                        context={**ctx, "actual_value": repr(value), "error": str(e)},
                    ) from e
            raise InvalidContractError(
                f"DECIMAL field {field_name!r} default must be a number or numeric string",
                error_code="DEFAULT_TYPE_MISMATCH",
                context={**ctx, "actual_value": repr(value)},
            )
        if field_type is FieldType.STRING and not isinstance(value, str):
            raise InvalidContractError(
                f"STRING field {field_name!r} default must be a string",
                error_code="DEFAULT_TYPE_MISMATCH",
                context={**ctx, "expected_type": "STRING", "actual_value": repr(value)},
            )
        if field_type is FieldType.INTEGER and (
            not isinstance(value, int) or isinstance(value, bool)
        ):
            raise InvalidContractError(
                f"INTEGER field {field_name!r} default must be an int (bool is rejected)",
                error_code="DEFAULT_TYPE_MISMATCH",
                context={**ctx, "expected_type": "INTEGER", "actual_value": repr(value)},
            )
        if field_type is FieldType.BOOLEAN and not isinstance(value, bool):
            raise InvalidContractError(
                f"BOOLEAN field {field_name!r} default must be a bool",
                error_code="DEFAULT_TYPE_MISMATCH",
                context={**ctx, "expected_type": "BOOLEAN", "actual_value": repr(value)},
            )
        if field_type is FieldType.OBJECT and not isinstance(value, dict):
            raise InvalidContractError(
                f"OBJECT field {field_name!r} default must be a dict",
                error_code="DEFAULT_TYPE_MISMATCH",
                context={**ctx, "expected_type": "OBJECT", "actual_value": repr(value)},
            )
        if field_type is FieldType.ARRAY and not isinstance(value, list):
            raise InvalidContractError(
                f"ARRAY field {field_name!r} default must be a list",
                error_code="DEFAULT_TYPE_MISMATCH",
                context={**ctx, "expected_type": "ARRAY", "actual_value": repr(value)},
            )
        if field_type is FieldType.ENUM:
            # ENUM defaults are accepted as-is; enum_values validation
            # happens in CanonicalField construction.
            return value
        if field_type is FieldType.DATE and not isinstance(value, str):
            raise InvalidContractError(
                f"DATE field {field_name!r} default must be a string",
                error_code="DEFAULT_TYPE_MISMATCH",
                context={**ctx, "expected_type": "DATE", "actual_value": repr(value)},
            )
        return value

    @staticmethod
    def _coerce_enum_values(
        raw: typing.Any,
        *,
        contract_id: str,
        field_name: str,
    ) -> EnumValueSet:
        """Coerce the ``enum_values`` list into an :class:`EnumValueSet`."""
        if not isinstance(raw, list):
            raise InvalidContractError(
                f"ENUM field {field_name!r} 'enum_values' must be a list",
                error_code="INVALID_FIELD",
                context={
                    "contract_id": contract_id,
                    "field_name": field_name,
                    "got_type": type(raw).__name__,
                },
            )
        if not raw:
            raise InvalidContractError(
                f"ENUM field {field_name!r} 'enum_values' must not be empty",
                error_code="MISSING_ENUM_VALUES",
                context={"contract_id": contract_id, "field_name": field_name},
            )
        return EnumValueSet(tuple(raw))

    # =====================================================================
    # Internal: policy parsing
    # =====================================================================

    @staticmethod
    def _parse_policy(raw: typing.Any, *, contract_id: str) -> ContractPolicy:
        """Parse the contract-level policy dict."""
        if not isinstance(raw, dict):
            raise InvalidContractError(
                f"contract {contract_id!r} 'policy' must be a dict",
                error_code="INVALID_POLICY_KEY",
                context={"contract_id": contract_id, "got_type": type(raw).__name__},
            )
        known = {"confidence_floor", "unresolved_acceptable", "stop_on_first_unresolved"}
        unknown = set(raw.keys()) - known
        if unknown:
            raise InvalidContractError(
                f"contract {contract_id!r} 'policy' has unknown keys: {sorted(unknown)}",
                error_code="INVALID_POLICY_KEY",
                context={
                    "contract_id": contract_id,
                    "unknown_keys": sorted(unknown),
                    "valid_keys": sorted(known),
                },
            )
        cf = raw.get("confidence_floor")
        if cf is not None and (
            not isinstance(cf, (int, float)) or isinstance(cf, bool) or not 0.0 <= cf <= 1.0
        ):
            raise InvalidContractError(
                f"contract {contract_id!r} 'confidence_floor' must be in [0.0, 1.0], got {cf!r}",
                error_code="INVALID_CONFIDENCE_FLOOR",
                context={"contract_id": contract_id, "value": cf},
            )
        # Type validation (Oracle review F4): policy booleans must be bool,
        # not arbitrary truthy values. ``ContractPolicy.__attrs_post_init__``
        # also enforces this, but rejecting at the adapter boundary gives a
        # clearer error pointing at the source contract.
        for key in ("unresolved_acceptable", "stop_on_first_unresolved"):
            v = raw.get(key)
            if v is not None and not isinstance(v, bool):
                raise InvalidContractError(
                    f"contract {contract_id!r} 'policy.{key}' must be a bool, got {v!r}",
                    error_code="INVALID_POLICY_KEY",
                    context={
                        "contract_id": contract_id,
                        "key": key,
                        "value": v,
                        "valid_keys": sorted(
                            {
                                "unresolved_acceptable",
                                "stop_on_first_unresolved",
                                "confidence_floor",
                            }
                        ),
                    },
                )
        return ContractPolicy(
            confidence_floor=float(cf) if cf is not None else None,
            unresolved_acceptable=raw.get("unresolved_acceptable"),
            stop_on_first_unresolved=raw.get("stop_on_first_unresolved"),
        )

    # =====================================================================
    # Internal: export helpers
    # =====================================================================

    @staticmethod
    def _export_field(f: CanonicalField) -> dict[str, typing.Any]:
        out: dict[str, typing.Any] = {
            "name": f.name,
            "type": f.type.name,
            "required": f.required,
        }
        if f.description is not None:
            out["description"] = f.description
        if f.semantic_tags:
            out["tags"] = list(f.semantic_tags)
        if f.constraints:
            out["constraints"] = [DictDSLAdapter._export_constraint(c) for c in f.constraints]
        if f.default is not None:
            out["default"] = DictDSLAdapter._export_default(f.default, f.type)
        if f.enum_values is not None:
            out["enum_values"] = list(f.enum_values)
        return out

    @staticmethod
    def _export_constraint(c: Constraint) -> dict[str, typing.Any]:
        return {"kind": c.kind.value, "params": dict(c.params)}

    @staticmethod
    def _export_policy(p: ContractPolicy) -> dict[str, typing.Any]:
        out: dict[str, typing.Any] = {}
        if p.confidence_floor is not None:
            out["confidence_floor"] = p.confidence_floor
        if p.unresolved_acceptable is not None:
            out["unresolved_acceptable"] = p.unresolved_acceptable
        if p.stop_on_first_unresolved is not None:
            out["stop_on_first_unresolved"] = p.stop_on_first_unresolved
        return out

    @staticmethod
    def _export_default(value: typing.Any, field_type: FieldType) -> typing.Any:
        if field_type is FieldType.MONEY and isinstance(value, MoneyValue):
            return {"amount": str(value.amount), "currency": value.currency}
        if field_type is FieldType.DECIMAL and isinstance(value, decimal.Decimal):
            return str(value)
        return value


# Self-register the adapter on import so the registry is populated
# automatically (per EXTENDING.md §1.3 step 4).
def _register_on_import() -> None:
    from paxman.contract import registry

    registry.register(DictDSLAdapter(), replace=True)


_register_on_import()
