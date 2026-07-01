"""Contract subsystem — adapter + validation boundary.

This is the only Paxman subsystem that knows about external contract formats
(Pydantic, JSON Schema, Dict DSL, OpenAPI). It translates caller-provided
contracts into Paxman's internal :class:`CanonicalContract` and rejects
anything invalid with an :class:`~paxman.errors.InvalidContractError` subclass.

Module layout
-------------
- :mod:`paxman.contract._types` — internal primitives: :class:`FieldType`
  re-export, :class:`Constraint`, :class:`ResolutionPolicy`, :class:`ContractPolicy`.
- :mod:`paxman.contract.canonical` — :class:`CanonicalContract`,
  :class:`CanonicalField`, :class:`MoneyValue` (the V1 canonical model).
- :mod:`paxman.contract.semantics` — semantic-tag handling (known tags,
  validation, type-suggestion).
- :mod:`paxman.contract.validator` — rejects invalid contracts.
- :mod:`paxman.contract.registry` — adapter lookup by ``format_id``.
- :mod:`paxman.contract.adapters` — concrete adapters (Pydantic, JSON Schema,
  Dict DSL, OpenAPI).
- :mod:`paxman.contract.adapters.base` — the :class:`ContractAdapter` Protocol
  (the SPI).
- :mod:`paxman.contract._format_hint` — :class:`FormatHint` enum and string
  resolver (the V1.1.0+ format-aware dispatch contract; see ADR-0015 and
  `issue #73 <https://github.com/nexusnv/paxman/issues/73>`_).

Boundary rules (per ``PACKAGE_STRUCTURE.md`` §2):

- ``contract/`` may NOT import from ``planner/``, ``executor/``,
  ``reconciler/``, ``artifact/``, ``capabilities/``, or ``api/``.
- ``contract/`` is the only layer that knows about external schemas.
"""

from __future__ import annotations

from paxman.contract._format_hint import (
    FormatHint,
    FormatHintValidationError,
    parse_format_hints,
    resolve_format_hint,
)
from paxman.contract._types import (
    # FieldType is intentionally re-exported from paxman.types (single source of
    # truth); the contract layer uses it but does not redefine it.
    Constraint,
    ContractPolicy,
    EnumValue,
    EnumValueSet,
    ResolutionPolicy,
)
from paxman.contract.canonical import (
    CanonicalContract,
    CanonicalField,
    MoneyValue,
)
from paxman.types import FieldType

__all__ = [
    "CanonicalContract",
    "CanonicalField",
    "Constraint",
    "ContractPolicy",
    "EnumValue",
    "EnumValueSet",
    "FieldType",
    "FormatHint",
    "FormatHintValidationError",
    "MoneyValue",
    "ResolutionPolicy",
    "parse_format_hints",
    "resolve_format_hint",
]
