"""Paxman — contract-driven deterministic normalization engine for Python.

This is the public package entry point exposing the stable API surface:

- :func:`normalize` — normalize input against a contract.
- :func:`replay` — verify an artifact without re-execution.
- :func:`register_adapter`, :func:`register_capability` — extension SPIs.
- :data:`__version__` — the package version.
- Public types and errors from ``api.types`` and ``api.errors``.

Subsystems live in submodules and are **not** re-exported here.

Imports are **lazy** (PEP 562): ``import paxman`` only loads
``paxman.api.version`` eagerly.  All other symbols are resolved
on first attribute access via ``__getattr__``, deferring the
heavy subsystem tree (planner, executor, reconciler, artifact)
until ``normalize()`` or ``replay()`` is first called.
"""

from __future__ import annotations

import typing

# Eager: __version__ is a cheap string constant.
from paxman.api.version import __version__

# ---------------------------------------------------------------------------
# Static-analysis-only re-exports (never executed at runtime).
# mypy / pyright read these to resolve types on ``paxman.Foo``.
# ---------------------------------------------------------------------------
if typing.TYPE_CHECKING:
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

# ---------------------------------------------------------------------------
# Lazy attribute loading (PEP 562).
#
# On first access of any public symbol (except ``__version__``), the
# corresponding ``paxman.api.*`` submodule is imported and the attribute
# is cached in the module globals for subsequent access.
# ---------------------------------------------------------------------------

# Mapping: attribute name → (module path, attribute name in that module)
_LAZY_IMPORT_MAP: typing.Final[dict[str, tuple[str, str]]] = {
    # errors
    "BudgetExceededError": ("paxman.api.errors", "BudgetExceededError"),
    "CapabilityError": ("paxman.api.errors", "CapabilityError"),
    "CapabilityNotFoundError": ("paxman.api.errors", "CapabilityNotFoundError"),
    "ConfigurationError": ("paxman.api.errors", "ConfigurationError"),
    "ExecutionError": ("paxman.api.errors", "ExecutionError"),
    "HashMismatchError": ("paxman.api.errors", "HashMismatchError"),
    "InferenceProviderError": ("paxman.api.errors", "InferenceProviderError"),
    "InvalidContractError": ("paxman.api.errors", "InvalidContractError"),
    "PaxmanError": ("paxman.api.errors", "PaxmanError"),
    "ReconciliationError": ("paxman.api.errors", "ReconciliationError"),
    "ReplayError": ("paxman.api.errors", "ReplayError"),
    "VersionMismatchError": ("paxman.api.errors", "VersionMismatchError"),
    # core API
    "normalize": ("paxman.api.normalize", "normalize"),
    "replay": ("paxman.api.replay", "replay"),
    "register_adapter": ("paxman.api.registry", "register_adapter"),
    "register_capability": ("paxman.api.registry", "register_capability"),
    # protocols
    "Capability": ("paxman.api.protocols", "Capability"),
    "ContractAdapter": ("paxman.api.protocols", "ContractAdapter"),
    # types
    "Budget": ("paxman.api.types", "Budget"),
    "CanonicalContract": ("paxman.api.types", "CanonicalContract"),
    "CanonicalField": ("paxman.api.types", "CanonicalField"),
    "ConfidenceBand": ("paxman.api.types", "ConfidenceBand"),
    "CurrencyPolicy": ("paxman.api.types", "CurrencyPolicy"),
    "ExecutionArtifact": ("paxman.api.types", "ExecutionArtifact"),
    "FieldType": ("paxman.api.types", "FieldType"),
    "Policy": ("paxman.api.types", "Policy"),
    "ResolutionPolicy": ("paxman.api.types", "ResolutionPolicy"),
    "Status": ("paxman.api.types", "Status"),
}


def __getattr__(name: str) -> object:
    """Lazily import public API symbols on first access.

    Args:
        name: The attribute name being accessed.

    Returns:
        The resolved attribute value.

    Raises:
        AttributeError: If *name* is not a public API symbol.
    """
    if name in _LAZY_IMPORT_MAP:
        import importlib

        module_path, attr_name = _LAZY_IMPORT_MAP[name]
        module = importlib.import_module(module_path)
        value: object = getattr(module, attr_name)
        # Cache in module globals so subsequent access is a dict lookup.
        globals()[name] = value
        return value
    raise AttributeError(f"module 'paxman' has no attribute {name!r}")
