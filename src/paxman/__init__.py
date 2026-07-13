"""Paxman v2: a deterministic canonicalization engine.

Mandate: see MANDATE.md. Spec: see docs/superpowers/specs/.
"""
from __future__ import annotations

__version__ = "0.0.0.dev0"

from paxman._capabilities.protocol import Capability
from paxman._capabilities.registry import CapabilityRegistry
from paxman._contracts.contract import (
    CanonicalEmailContract,
    Contract,
    parse_contract,
)
from paxman._core.artifact import ExecutionArtifact
from paxman._core.classification import ValidationResult
from paxman._core.orchestrator import canonicalize as _canonicalize
from paxman._core.replay import replay as _replay
from paxman._core.types import (
    CapabilityResult,
    Evidence,
    Status,
    VersionStamp,
)
from paxman._errors import (
    CanonicalizationError,
    ConfigurationError,
    ContractError,
    FrozenRegistryError,
    PaxmanError,
    UnsupportedContractError,
    VersionMismatchError,
)
from paxman import _orchestrator_runtime


def canonicalize(input_data: object, contract: object) -> ExecutionArtifact:
    """Canonicalize `input_data` against `contract`. See MANDATE §2."""
    return _canonicalize(input_data, contract)


def replay(artifact: ExecutionArtifact, contract: object) -> ExecutionArtifact:
    """Byte-equal rehydration. See MANDATE Law 12."""
    return _replay(artifact, contract)


def register_capability(capability: Capability) -> None:
    """Register a capability with the default registry.

    After the first `canonicalize` call, the registry is frozen and
    further calls raise `FrozenRegistryError` (mandate §5.4).
    """
    _orchestrator_runtime.default_registry.register(capability)


__all__ = [
    "__version__",
    "canonicalize",
    "replay",
    "register_capability",
    # Re-exports of the public types so users do not need to know
    # about the _core / _contracts / _capabilities internal layout.
    "ExecutionArtifact",
    "Status",
    "Evidence",
    "VersionStamp",
    "CapabilityResult",
    "ValidationResult",
    "Contract",
    "CanonicalEmailContract",
    "parse_contract",
    "Capability",
    "CapabilityRegistry",
    # Errors
    "PaxmanError",
    "CanonicalizationError",
    "ContractError",
    "ConfigurationError",
    "FrozenRegistryError",
    "UnsupportedContractError",
    "VersionMismatchError",
]
