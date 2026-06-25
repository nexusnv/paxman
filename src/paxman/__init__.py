"""Paxman — contract-driven deterministic normalization engine for Python.

This is the public package entry point exposing the stable API surface:

- :func:`normalize` — normalize input against a contract.
- :func:`replay` — verify an artifact without re-execution.
- :func:`register_adapter`, :func:`register_capability` — extension SPIs.
- :data:`__version__` — the package version.
- Public types and errors from ``api.types`` and ``api.errors``.

Subsystems live in submodules and are **not** re-exported here.
"""

from paxman.api.errors import (
    BudgetExceededError,
    CapabilityError,
    CapabilityNotFoundError,
    ConfigurationError,
    ExecutionError,
    HashMismatchError,
    InferenceProviderError,
    InvalidContractError,
    PaxmanError,
    ReconciliationError,
    ReplayError,
    VersionMismatchError,
)
from paxman.api.normalize import normalize
from paxman.api.protocols import Capability, ContractAdapter
from paxman.api.registry import register_adapter, register_capability
from paxman.api.replay import replay
from paxman.api.types import (
    Budget,
    CanonicalContract,
    CanonicalField,
    ConfidenceBand,
    CurrencyPolicy,
    ExecutionArtifact,
    FieldType,
    Policy,
    ResolutionPolicy,
    Status,
)
from paxman.api.version import __version__

__all__ = [
    "Budget",
    "BudgetExceededError",
    "CanonicalContract",
    "CanonicalField",
    "Capability",
    "CapabilityError",
    "CapabilityNotFoundError",
    "ConfidenceBand",
    "ConfigurationError",
    "ContractAdapter",
    "CurrencyPolicy",
    "ExecutionArtifact",
    "ExecutionError",
    "FieldType",
    "HashMismatchError",
    "InferenceProviderError",
    "InvalidContractError",
    "PaxmanError",
    "Policy",
    "ReconciliationError",
    "ReplayError",
    "ResolutionPolicy",
    "Status",
    "VersionMismatchError",
    "__version__",
    "normalize",
    "register_adapter",
    "register_capability",
    "replay",
]
