"""Paxman error hierarchy.

This module defines the 17-class exception hierarchy for Paxman, following
ARCHITECTURE.md §6.2. Every exception is an ``attrs`` frozen dataclass with
slots, carrying a machine-readable ``error_code`` and a structured ``context``
dict for logging and tracing.

The 11 public errors are re-exported in ``paxman.api.errors`` (Sprint 6):

- :class:`PaxmanError` (base)
- :class:`InvalidContractError`
- :class:`ExecutionError`
- :class:`CapabilityError`
- :class:`InferenceProviderError`
- :class:`BudgetExceededError`
- :class:`ReconciliationError`
- :class:`ReplayError`
- :class:`VersionMismatchError`
- :class:`HashMismatchError`
- :class:`ConfigurationError`

The remaining 6 are internal contract/configuration errors not surfaced
through the public API.
"""

from __future__ import annotations

from typing import Any

import attrs


@attrs.frozen(slots=True)
class PaxmanError(Exception):
    """Base exception for all Paxman errors.

    Public: re-exported in api.errors.

    Every Paxman exception carries a machine-readable ``error_code`` and a
    structured ``context`` dict. Subclasses override the ``error_code``
    default with a domain-specific constant.

    Attributes:
        message: Human-readable error description.
        error_code: ``"PAXMAN_ERROR"`` by default; subclasses override.
        context: Structured details for logging and tracing (e.g.,
            ``{"field_path": "$.customer.name", "reason": "missing"}``).

    Example:
        >>> raise PaxmanError("Something went wrong")
        >>> raise PaxmanError(
        ...     "Unexpected state",
        ...     context={"step": "reconciliation"},
        ... )
    """

    message: str = attrs.field()
    error_code: str = attrs.field(default="PAXMAN_ERROR")
    context: dict[str, Any] = attrs.field(factory=dict)

    def __str__(self) -> str:
        """Return the human-readable error message."""
        return self.message

    def __attrs_post_init__(self) -> None:
        """Validate invariants after attrs construction."""
        if not self.message:
            raise ValueError("PaxmanError message must be non-empty")
        # Convert None → {} for ergonomic call-sites.
        if self.context is None:
            object.__setattr__(self, "context", {})
        if not self.error_code:
            raise ValueError("error_code must be a non-empty string")
        if not isinstance(self.context, dict):
            raise TypeError(f"context must be dict, got {type(self.context).__name__}")


# ---------------------------------------------------------------------------
# InvalidContractError branch
# ---------------------------------------------------------------------------


@attrs.frozen(slots=True)
class InvalidContractError(PaxmanError):
    """Raised when a contract fails validation.

    Public: re-exported in api.errors.

    Attributes:
        message: Human-readable error description.
        error_code: ``"INVALID_CONTRACT"`` by default; subclasses override.
        context: Structured details for logging and tracing (e.g.,
            ``{"field_path": "$.customer.name", "expected": "string"}``).

    Example:
        >>> raise InvalidContractError(
        ...     "Field 'age' has invalid type",
        ...     context={"field_path": "$.age", "got": "str"},
        ... )
    """

    message: str = attrs.field()
    error_code: str = attrs.field(default="INVALID_CONTRACT")
    context: dict[str, Any] = attrs.field(factory=dict)


@attrs.frozen(slots=True)
class UnsupportedFieldTypeError(InvalidContractError):
    """Raised when a contract references a field type not supported by this Paxman version.

    Attributes:
        message: Human-readable error description.
        error_code: ``"UNSUPPORTED_FIELD_TYPE"`` by default.
        context: Structured details for logging and tracing (e.g.,
            ``{"field_type": "GEO_POINT", "supported": ["STRING", "INTEGER", ...]}``).

    Example:
        >>> raise UnsupportedFieldTypeError(
        ...     "Field type 'GEO_POINT' is not supported in V1",
        ...     context={"field_type": "GEO_POINT"},
        ... )
    """

    message: str = attrs.field()
    error_code: str = attrs.field(default="UNSUPPORTED_FIELD_TYPE")
    context: dict[str, Any] = attrs.field(factory=dict)


@attrs.frozen(slots=True)
class InvalidConstraintError(InvalidContractError):
    """Raised when a field constraint is syntactically or semantically invalid.

    Attributes:
        message: Human-readable error description.
        error_code: ``"INVALID_CONSTRAINT"`` by default.
        context: Structured details for logging and tracing (e.g.,
            ``{"field_path": "$.amount", "constraint": "min_value", "detail": "must be >= 0"}``).

    Example:
        >>> raise InvalidConstraintError(
        ...     "Constraint 'min_length' requires a non-negative integer",
        ...     context={"field_path": "$.name", "constraint": "min_length"},
        ... )
    """

    message: str = attrs.field()
    error_code: str = attrs.field(default="INVALID_CONSTRAINT")
    context: dict[str, Any] = attrs.field(factory=dict)


@attrs.frozen(slots=True)
class InvalidPathError(InvalidContractError):
    """Raised when a field path in the contract does not resolve.

    Attributes:
        message: Human-readable error description.
        error_code: ``"INVALID_PATH"`` by default.
        context: Structured details for logging and tracing (e.g.,
            ``{"field_path": "$.customer..name", "reason": "empty segment"}``).

    Example:
        >>> raise InvalidPathError(
        ...     "Field path '$.items[].' has a trailing dot",
        ...     context={"field_path": "$.items[]."},
        ... )
    """

    message: str = attrs.field()
    error_code: str = attrs.field(default="INVALID_PATH")
    context: dict[str, Any] = attrs.field(factory=dict)


@attrs.frozen(slots=True)
class InvalidSemanticTagError(InvalidContractError):
    """Raised when a semantic tag on a field is unknown or malformed.

    Attributes:
        message: Human-readable error description.
        error_code: ``"INVALID_SEMANTIC_TAG"`` by default.
        context: Structured details for logging and tracing (e.g.,
            ``{"field_path": "$.invoice_date", "tag": "date:iso8601", "reason": "unknown tag"}``).

    Example:
        >>> raise InvalidSemanticTagError(
        ...     "Semantic tag 'currency:crypto' is not recognized",
        ...     context={"field_path": "$.total", "tag": "currency:crypto"},
        ... )
    """

    message: str = attrs.field()
    error_code: str = attrs.field(default="INVALID_SEMANTIC_TAG")
    context: dict[str, Any] = attrs.field(factory=dict)


# ---------------------------------------------------------------------------
# ExecutionError branch
# ---------------------------------------------------------------------------


@attrs.frozen(slots=True)
class ExecutionError(PaxmanError):
    """Raised when plan execution fails at runtime.

    Public: re-exported in api.errors.

    Attributes:
        message: Human-readable error description.
        error_code: ``"EXECUTION_ERROR"`` by default; subclasses override.
        context: Structured details for logging and tracing (e.g.,
            ``{"field_path": "$.total", "step": "regex_extraction"}``).

    Example:
        >>> raise ExecutionError(
        ...     "Execution halted: unrecoverable state",
        ...     context={"field_path": "$.total"},
        ... )
    """

    message: str = attrs.field()
    error_code: str = attrs.field(default="EXECUTION_ERROR")
    context: dict[str, Any] = attrs.field(factory=dict)


@attrs.frozen(slots=True)
class CapabilityError(ExecutionError):
    """Raised when an individual capability (e.g., text_extraction) fails.

    Public: re-exported in api.errors.

    Attributes:
        message: Human-readable error description.
        error_code: ``"CAPABILITY_ERROR"`` by default; subclasses override.
        context: Structured details for logging and tracing (e.g.,
            ``{"capability": "text_extraction", "reason": "unsupported encoding"}``).

    Example:
        >>> raise CapabilityError(
        ...     "OCR provider returned empty result",
        ...     context={"capability": "text_extraction"},
        ... )
    """

    message: str = attrs.field()
    error_code: str = attrs.field(default="CAPABILITY_ERROR")
    context: dict[str, Any] = attrs.field(factory=dict)


@attrs.frozen(slots=True)
class InferenceProviderError(CapabilityError):
    """Raised when a remote inference provider (e.g., LLM API) fails.

    Public: re-exported in api.errors.

    Attributes:
        message: Human-readable error description.
        error_code: ``"INFERENCE_PROVIDER_ERROR"`` by default.
        context: Structured details for logging and tracing (e.g.,
            ``{"provider": "openai", "status_code": 429, "retry_after": 30}``).

    Example:
        >>> raise InferenceProviderError(
        ...     "Rate limited by inference provider",
        ...     context={"provider": "openai", "status_code": 429},
        ... )
    """

    message: str = attrs.field()
    error_code: str = attrs.field(default="INFERENCE_PROVIDER_ERROR")
    context: dict[str, Any] = attrs.field(factory=dict)


@attrs.frozen(slots=True)
class BudgetExceededError(ExecutionError):
    """Raised when execution exceeds the caller-supplied budget.

    Public: re-exported in api.errors.

    Attributes:
        message: Human-readable error description.
        error_code: ``"BUDGET_EXCEEDED"`` by default.
        context: Structured details for logging and tracing (e.g.,
            ``{"limit_usd": "0.10", "spent_usd": "0.12", "field_path": "$.total"}``).

    Example:
        >>> raise BudgetExceededError(
        ...     "Budget exceeded: spent $0.12 of $0.10 limit",
        ...     context={"limit_usd": "0.10", "spent_usd": "0.12"},
        ... )
    """

    message: str = attrs.field()
    error_code: str = attrs.field(default="BUDGET_EXCEEDED")
    context: dict[str, Any] = attrs.field(factory=dict)


@attrs.frozen(slots=True)
class ReconciliationError(ExecutionError):
    """Raised when the reconciler cannot merge candidates into a resolved truth.

    Public: re-exported in api.errors.

    Attributes:
        message: Human-readable error description.
        error_code: ``"RECONCILIATION_ERROR"`` by default.
        context: Structured details for logging and tracing (e.g.,
            ``{"field_path": "$.supplier_name", "candidate_count": 3}``).

    Example:
        >>> raise ReconciliationError(
        ...     "Conflicting candidates for field 'supplier_name'",
        ...     context={"field_path": "$.supplier_name", "candidate_count": 3},
        ... )
    """

    message: str = attrs.field()
    error_code: str = attrs.field(default="RECONCILIATION_ERROR")
    context: dict[str, Any] = attrs.field(factory=dict)


# ---------------------------------------------------------------------------
# ReplayError branch
# ---------------------------------------------------------------------------


@attrs.frozen(slots=True)
class ReplayError(PaxmanError):
    """Raised when replay of a captured artifact fails.

    Public: re-exported in api.errors.

    Attributes:
        message: Human-readable error description.
        error_code: ``"REPLAY_ERROR"`` by default; subclasses override.
        context: Structured details for logging and tracing (e.g.,
            ``{"artifact_version": "0.1.0", "reason": "unsupported format"}``).

    Example:
        >>> raise ReplayError(
        ...     "Cannot replay artifact: format not recognized",
        ...     context={"artifact_version": "0.1.0"},
        ... )
    """

    message: str = attrs.field()
    error_code: str = attrs.field(default="REPLAY_ERROR")
    context: dict[str, Any] = attrs.field(factory=dict)


@attrs.frozen(slots=True)
class VersionMismatchError(ReplayError):
    """Raised when the artifact was produced by an incompatible Paxman version.

    Public: re-exported in api.errors.

    Attributes:
        message: Human-readable error description.
        error_code: ``"VERSION_MISMATCH"`` by default.
        context: Structured details for logging and tracing (e.g.,
            ``{"artifact_version": "0.1.0", "current_version": "0.5.0"}``).

    Example:
        >>> raise VersionMismatchError(
        ...     "Artifact produced by Paxman 0.1.0, current version is 0.5.0",
        ...     context={"artifact_version": "0.1.0", "current_version": "0.5.0"},
        ... )
    """

    message: str = attrs.field()
    error_code: str = attrs.field(default="VERSION_MISMATCH")
    context: dict[str, Any] = attrs.field(factory=dict)


@attrs.frozen(slots=True)
class HashMismatchError(ReplayError):
    """Raised when the artifact's replay hash does not match its contents.

    Public: re-exported in api.errors.

    Attributes:
        message: Human-readable error description.
        error_code: ``"HASH_MISMATCH"`` by default.
        context: Structured details for logging and tracing (e.g.,
            ``{"expected_hash": "a3f8...", "actual_hash": "b7c1..."}``).

    Example:
        >>> raise HashMismatchError(
        ...     "Artifact hash mismatch: expected a3f8..., got b7c1...",
        ...     context={"expected_hash": "a3f8", "actual_hash": "b7c1"},
        ... )
    """

    message: str = attrs.field()
    error_code: str = attrs.field(default="HASH_MISMATCH")
    context: dict[str, Any] = attrs.field(factory=dict)


# ---------------------------------------------------------------------------
# ConfigurationError branch
# ---------------------------------------------------------------------------


@attrs.frozen(slots=True)
class ConfigurationError(PaxmanError):
    """Raised when a configuration value is invalid or missing.

    Public: re-exported in api.errors.

    Attributes:
        message: Human-readable error description.
        error_code: ``"CONFIGURATION_ERROR"`` by default; subclasses override.
        context: Structured details for logging and tracing (e.g.,
            ``{"setting": "max_retries", "reason": "must be positive"}``).

    Example:
        >>> raise ConfigurationError(
        ...     "Missing required configuration: 'provider_api_key'",
        ...     context={"setting": "provider_api_key"},
        ... )
    """

    message: str = attrs.field()
    error_code: str = attrs.field(default="CONFIGURATION_ERROR")
    context: dict[str, Any] = attrs.field(factory=dict)


@attrs.frozen(slots=True)
class InvalidBudgetError(ConfigurationError):
    """Raised when a Budget object has invalid parameters.

    Attributes:
        message: Human-readable error description.
        error_code: ``"INVALID_BUDGET"`` by default.
        context: Structured details for logging and tracing (e.g.,
            ``{"field": "max_total_cost_usd", "value": -1, "reason": "must be non-negative"}``).

    Example:
        >>> raise InvalidBudgetError(
        ...     "Budget max_total_cost_usd must be non-negative",
        ...     context={"field": "max_total_cost_usd", "value": -1},
        ... )
    """

    message: str = attrs.field()
    error_code: str = attrs.field(default="INVALID_BUDGET")
    context: dict[str, Any] = attrs.field(factory=dict)


@attrs.frozen(slots=True)
class InvalidPolicyError(ConfigurationError):
    """Raised when a Policy object has invalid parameters.

    Attributes:
        message: Human-readable error description.
        error_code: ``"INVALID_POLICY"`` by default.
        context: Structured details for logging and tracing (e.g.,
            ``{"field": "allow_remote_inference", "reason": "must be bool"}``).

    Example:
        >>> raise InvalidPolicyError(
        ...     "Policy 'log_raw_input' must be a boolean",
        ...     context={"field": "log_raw_input", "got": "str"},
        ... )
    """

    message: str = attrs.field()
    error_code: str = attrs.field(default="INVALID_POLICY")
    context: dict[str, Any] = attrs.field(factory=dict)


__all__ = [
    "BudgetExceededError",
    "CapabilityError",
    "ConfigurationError",
    "ExecutionError",
    "HashMismatchError",
    "InferenceProviderError",
    "InvalidBudgetError",
    "InvalidConstraintError",
    "InvalidContractError",
    "InvalidPathError",
    "InvalidPolicyError",
    "InvalidSemanticTagError",
    "PaxmanError",
    "ReconciliationError",
    "ReplayError",
    "UnsupportedFieldTypeError",
    "VersionMismatchError",
]
