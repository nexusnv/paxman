"""Shared internal enums for the paxman normalization engine.

This module is a leaf in the import DAG — it imports nothing from
``paxman.*`` submodules.  Public-facing types will be re-exported from
``paxman.api.types`` in Sprint 6.
"""

from __future__ import annotations

import enum


@enum.unique
class Status(enum.Enum):
    """Artifact-level status returned by :func:`paxman.normalize`.

    Each value corresponds to a distinct terminal state of the normalize
    pipeline (see ``ARCHITECTURE.md`` §6.1).

    Values:
        SUCCESS: all required fields resolved with sufficient confidence.
        PARTIAL_SUCCESS: some fields resolved, some unresolved, but the
            call returned a usable artifact.
        UNRESOLVED: one or more required fields could not be resolved.
        INVALID_CONTRACT: the contract was malformed before any execution
            began.
        EXECUTION_FAILED: an unrecoverable error halted execution.
    """

    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    UNRESOLVED = "UNRESOLVED"
    INVALID_CONTRACT = "INVALID_CONTRACT"
    EXECUTION_FAILED = "EXECUTION_FAILED"


@enum.unique
class ConfidenceBand(enum.Enum):
    """Discrete confidence bands assigned by the Reconciler.

    The Reconciler is the sole confidence authority (ADR-0005).  Each band
    maps to a half-open numeric interval (see ``ADR-0005`` lines 74-81).

    Values:
        CERTAIN: 0.95-1.00 - near-certain extraction.
        HIGH: 0.80-0.95 - strong evidence, minor ambiguity.
        MEDIUM: 0.60-0.80 - plausible but needs review.
        LOW: 0.30-0.60 - weak evidence, likely requires human check.
        UNTRUSTED: 0.00-0.30 - effectively no usable signal.
    """

    CERTAIN = "CERTAIN"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNTRUSTED = "UNTRUSTED"


@enum.unique
class FieldType(enum.Enum):
    """The 9 canonical V1 field types for ``CanonicalField``.

    ``MONEY`` is first-class per ADR-0004: it carries an amount (Decimal),
    ISO-4217 currency code, and optional precision — it is NOT a tagged
    ``DECIMAL``.

    Values:
        STRING: free-form text.
        INTEGER: bounded integer.
        DECIMAL: bounded decimal.
        BOOLEAN: true / false.
        DATE: ISO-8601 date (or datetime).
        ENUM: one of a fixed set of values.
        OBJECT: nested structure.
        ARRAY: ordered list of items.
        MONEY: amount + currency + optional precision.
    """

    STRING = "STRING"
    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    ENUM = "ENUM"
    OBJECT = "OBJECT"
    ARRAY = "ARRAY"
    MONEY = "MONEY"


__all__ = ["ConfidenceBand", "FieldType", "Status"]
