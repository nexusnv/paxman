"""Paxman v2: a deterministic canonicalization engine.

Mandate: see MANDATE.md. Spec: see docs/superpowers/specs/.
"""

from __future__ import annotations

from typing import Any

__version__ = "0.0.0.dev0"

from paxman import _orchestrator_runtime
from paxman._capabilities.boolean.contract import Boolean, CanonicalBooleanContract
from paxman._capabilities.date.contract import CanonicalDateContract, Date
from paxman._capabilities.email.contract import CanonicalEmailContract, Email
from paxman._capabilities.ip.contract import IP, CanonicalIPContract
from paxman._capabilities.money.contract import CanonicalMoneyContract, Money
from paxman._capabilities.phone.contract import CanonicalPhoneContract, Phone
from paxman._capabilities.protocol import Capability
from paxman._capabilities.url.contract import URL, CanonicalURLContract
from paxman._capabilities.uuid.contract import UUID, CanonicalUUIDContract
from paxman._core.artifact import ExecutionArtifact
from paxman._core.classification import ValidationResult
from paxman._core.engine import canonicalize as _canonicalize
from paxman._core.provenance import Evidence
from paxman._core.replay import replay as _replay
from paxman._core.result import CapabilityResult, VersionStamp
from paxman._core.status import Status
from paxman._dsl.parser import parse_contract
from paxman._errors import (
    CanonicalizationError,
    ConfigurationError,
    ContractError,
    FrozenRegistryError,
    PaxmanError,
    UnsupportedContractError,
    VersionMismatchError,
)
from paxman._registry.capability_registry import CapabilityRegistry

# Public `Contract` union of concrete value objects (mandate Law 5). The
# structural `Contract` Protocol of the same name lives in
# `paxman._core.contracts`; this union is what the DSL parser returns and
# what callers hold.
Contract = (
    CanonicalEmailContract
    | CanonicalUUIDContract
    | CanonicalDateContract
    | CanonicalPhoneContract
    | CanonicalURLContract
    | CanonicalBooleanContract
    | CanonicalIPContract
    | CanonicalMoneyContract
)


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


def __getattr__(name: str) -> Any:
    """PEP 562 module-level attribute lookup (mandate §1.1, Law 8).

    The 'normalize' name does not exist on this module — Paxman
    canonicalizes, it does not normalize. Raising an AttributeError that
    teaches the right function is informative failure (Law 8); there is
    still no 'normalize' attribute (§1.1 identity boundary holds).
    """
    if name == "normalize":
        raise AttributeError(
            "the 'normalize' name does not exist on this module; "
            "Paxman canonicalizes, it does not normalize. "
            "Use canonicalize() instead."
        )
    raise AttributeError(f"module 'paxman' has no attribute {name!r}")


__all__ = [
    "IP",
    "URL",
    "UUID",
    "Boolean",
    "CanonicalBooleanContract",
    "CanonicalDateContract",
    "CanonicalEmailContract",
    "CanonicalIPContract",
    "CanonicalMoneyContract",
    "CanonicalPhoneContract",
    "CanonicalURLContract",
    "CanonicalUUIDContract",
    "CanonicalizationError",
    "Capability",
    "CapabilityRegistry",
    "CapabilityResult",
    "ConfigurationError",
    "Contract",
    "ContractError",
    "Date",
    "Email",
    "Evidence",
    "ExecutionArtifact",
    "FrozenRegistryError",
    "Money",
    "PaxmanError",
    "Phone",
    "Status",
    "UnsupportedContractError",
    "ValidationResult",
    "VersionMismatchError",
    "VersionStamp",
    "__version__",
    "canonicalize",
    "parse_contract",
    "register_capability",
    "replay",
]
