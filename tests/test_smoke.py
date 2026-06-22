"""Smoke tests for the paxman package.

These tests verify that the package can be imported, that ``__version__`` is a
non-empty string, and that all 9 cross-cutting modules are importable. They
are the minimum bar for a Sprint 1 release; no subsystem behaviour is
exercised (Sprint 2+).
"""

from __future__ import annotations

import importlib

import pytest

# --- Package-level smoke -----------------------------------------------------


def test_paxman_is_importable() -> None:
    """The ``paxman`` package can be imported."""
    import paxman  # noqa: F401  (smoke import; presence is the assertion)


def test_version_is_a_string() -> None:
    """``paxman.__version__`` is a non-empty string."""
    import paxman

    assert isinstance(paxman.__version__, str)
    assert paxman.__version__, "paxman.__version__ is empty"
    # Must be parseable as a semver-ish ``MAJOR.MINOR.PATCH`` string.
    parts = paxman.__version__.split(".")
    assert len(parts) == 3, f"paxman.__version__ = {paxman.__version__!r} is not MAJOR.MINOR.PATCH"
    for part in parts:
        assert part.isdigit(), f"paxman.__version__ component {part!r} is not numeric"


def test_version_is_in_all() -> None:
    """``__version__`` is listed in ``paxman.__all__``."""
    import paxman

    assert hasattr(paxman, "__all__"), "paxman.__all__ is not defined"
    assert "__version__" in paxman.__all__


# --- Cross-cutting module smoke ---------------------------------------------


@pytest.mark.parametrize(
    "module_name",
    [
        "paxman.errors",
        "paxman.types",
        "paxman.protocols",
        "paxman.versioning",
        "paxman.logging",
        "paxman.budget",
        "paxman.clock",
        "paxman.ids",
        "paxman.serialization",
    ],
)
def test_cross_cutting_module_is_importable(module_name: str) -> None:
    """Each cross-cutting module can be imported (no circular import, no syntax error)."""
    module = importlib.import_module(module_name)
    assert module is not None


# --- Public-error surface ---------------------------------------------------


PUBLIC_ERROR_NAMES = [
    "PaxmanError",
    "InvalidContractError",
    "ExecutionError",
    "CapabilityError",
    "InferenceProviderError",
    "BudgetExceededError",
    "ReconciliationError",
    "ReplayError",
    "VersionMismatchError",
    "HashMismatchError",
    "ConfigurationError",
]


@pytest.mark.parametrize("name", PUBLIC_ERROR_NAMES)
def test_public_error_is_importable(name: str) -> None:
    """Each of the 11 public error classes is importable from ``paxman.errors``."""
    from paxman import errors

    assert hasattr(errors, name), f"paxman.errors missing {name}"
    cls = getattr(errors, name)
    assert isinstance(cls, type)
    assert issubclass(cls, BaseException)


def test_all_seventeen_error_classes_exist() -> None:
    """The ``paxman.errors`` module defines all 17 exception classes per ARCHITECTURE §6.2."""
    from paxman import errors

    # The public 11 + the 6 internal-only subclasses.
    all_17 = [
        *PUBLIC_ERROR_NAMES,
        "UnsupportedFieldTypeError",
        "InvalidConstraintError",
        "InvalidPathError",
        "InvalidSemanticTagError",
        "InvalidBudgetError",
        "InvalidPolicyError",
    ]
    missing = [name for name in all_17 if not hasattr(errors, name)]
    assert not missing, f"paxman.errors is missing: {missing}"
    assert len(all_17) == 17


# --- Public-type surface ----------------------------------------------------


def test_status_enum_has_five_values() -> None:
    """``Status`` has 5 members: SUCCESS, PARTIAL_SUCCESS, UNRESOLVED, INVALID_CONTRACT, EXECUTION_FAILED."""
    from paxman.types import Status

    names = {member.name for member in Status}
    assert names == {
        "SUCCESS",
        "PARTIAL_SUCCESS",
        "UNRESOLVED",
        "INVALID_CONTRACT",
        "EXECUTION_FAILED",
    }


def test_confidence_band_has_five_values() -> None:
    """``ConfidenceBand`` has 5 members: CERTAIN, HIGH, MEDIUM, LOW, UNTRUSTED (per ADR-0005)."""
    from paxman.types import ConfidenceBand

    names = {member.name for member in ConfidenceBand}
    assert names == {"CERTAIN", "HIGH", "MEDIUM", "LOW", "UNTRUSTED"}


def test_field_type_has_nine_values() -> None:
    """``FieldType`` has 9 members (the canonical V1 set)."""
    from paxman.types import FieldType

    names = {member.name for member in FieldType}
    assert names == {
        "STRING",
        "INTEGER",
        "DECIMAL",
        "BOOLEAN",
        "DATE",
        "ENUM",
        "OBJECT",
        "ARRAY",
        "MONEY",
    }


# --- Public-config surface --------------------------------------------------


def test_budget_default_values() -> None:
    """``Budget()`` with no arguments has all caps set to ``None``."""
    from paxman.budget import Budget

    b = Budget()
    assert b.max_total_cost_usd is None
    assert b.max_total_latency_ms is None
    assert b.max_remote_inference_calls is None
    assert b.max_capability_invocations is None


def test_policy_default_values() -> None:
    """``Policy()`` with no arguments has the documented safe defaults."""
    from paxman.budget import CurrencyPolicy, Policy

    p = Policy()
    assert p.allow_remote_inference is True
    assert p.allow_local_inference is True
    assert p.confidence_floor == 0.80
    assert p.unresolved_acceptable is False
    assert p.currency_policy is CurrencyPolicy.STRICT_MATCH
    assert p.emit_metrics is False
    assert p.log_raw_input is False
    assert p.record_inference_io is False
    assert p.embed_evidence_payload is False
