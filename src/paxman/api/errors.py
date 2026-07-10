"""Public error classes for the Paxman API.

Re-exports the 12 public exception classes from :mod:`paxman.errors`
plus the 2 V1.2.0 inference SPI types (SecretResolver and
EnvSecretResolver) used by the provider layer. All errors inherit
from :class:`PaxmanError`.
"""

from paxman.errors import (
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
from paxman.providers._resolver import EnvSecretResolver, SecretResolver

__all__ = [
    "BudgetExceededError",
    "CapabilityError",
    "CapabilityNotFoundError",
    "ConfigurationError",
    "EnvSecretResolver",
    "ExecutionError",
    "HashMismatchError",
    "InferenceProviderError",
    "InvalidContractError",
    "PaxmanError",
    "ReconciliationError",
    "ReplayError",
    "SecretResolver",
    "VersionMismatchError",
]
