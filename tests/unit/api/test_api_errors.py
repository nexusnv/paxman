"""Unit tests for ``paxman.api.errors`` — public error re-exports.

All 12 public error classes should be importable from ``paxman.api.errors``
and maintain their inheritance hierarchy:

- ``PaxmanError`` (base of all)
- ``InvalidContractError`` → ``PaxmanError``
- ``ExecutionError`` → ``PaxmanError``
- ``CapabilityError`` → ``ExecutionError`` → ``PaxmanError``
- ``InferenceProviderError`` → ``CapabilityError`` → ``ExecutionError`` → ``PaxmanError``
- ``BudgetExceededError`` → ``PaxmanError``
- ``ReconciliationError`` → ``PaxmanError``
- ``ReplayError`` → ``PaxmanError``
- ``VersionMismatchError`` → ``ReplayError`` → ``PaxmanError``
- ``HashMismatchError`` → ``ReplayError`` → ``PaxmanError``
- ``CapabilityNotFoundError`` → ``ReplayError`` → ``PaxmanError``
- ``ConfigurationError`` → ``PaxmanError``
"""

from __future__ import annotations

import pytest

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

pytestmark = pytest.mark.deterministic

# ---------------------------------------------------------------------------
# 12-class inventory
# ---------------------------------------------------------------------------

ALL_12 = [
    PaxmanError,
    InvalidContractError,
    ExecutionError,
    CapabilityError,
    InferenceProviderError,
    BudgetExceededError,
    ReconciliationError,
    ReplayError,
    VersionMismatchError,
    HashMismatchError,
    CapabilityNotFoundError,
    ConfigurationError,
]


class TestAllErrorsImportable:
    """All 12 error classes are importable from ``paxman.api.errors``."""

    def test_paxman_error_importable(self) -> None:
        assert PaxmanError is not None

    def test_invalid_contract_error_importable(self) -> None:
        assert InvalidContractError is not None

    def test_execution_error_importable(self) -> None:
        assert ExecutionError is not None

    def test_capability_error_importable(self) -> None:
        assert CapabilityError is not None

    def test_inference_provider_error_importable(self) -> None:
        assert InferenceProviderError is not None

    def test_budget_exceeded_error_importable(self) -> None:
        assert BudgetExceededError is not None

    def test_reconciliation_error_importable(self) -> None:
        assert ReconciliationError is not None

    def test_replay_error_importable(self) -> None:
        assert ReplayError is not None

    def test_version_mismatch_error_importable(self) -> None:
        assert VersionMismatchError is not None

    def test_hash_mismatch_error_importable(self) -> None:
        assert HashMismatchError is not None

    def test_capability_not_found_error_importable(self) -> None:
        assert CapabilityNotFoundError is not None

    def test_configuration_error_importable(self) -> None:
        assert ConfigurationError is not None


# ---------------------------------------------------------------------------
# Each is a subclass of BaseException
# ---------------------------------------------------------------------------


class TestInheritFromException:
    """Every public error is a proper ``Exception`` subclass."""

    @pytest.mark.parametrize("cls", ALL_12)
    def test_is_exception_subclass(self, cls: type) -> None:
        assert issubclass(cls, BaseException)

    @pytest.mark.parametrize("cls", ALL_12)
    def test_is_paxman_error_subclass(self, cls: type) -> None:
        """All error classes (except PaxmanError itself) inherit from PaxmanError."""
        if cls is not PaxmanError:
            assert issubclass(cls, PaxmanError)


# ---------------------------------------------------------------------------
# Inheritance hierarchy
# ---------------------------------------------------------------------------


class TestInheritanceHierarchy:
    """Specific inheritance chains are correct."""

    def test_paxman_error_is_base(self) -> None:
        assert issubclass(PaxmanError, Exception)

    def test_invalid_contract_error_extends_paxman(self) -> None:
        assert issubclass(InvalidContractError, PaxmanError)

    def test_execution_error_extends_paxman(self) -> None:
        assert issubclass(ExecutionError, PaxmanError)

    def test_capability_error_extends_execution(self) -> None:
        assert issubclass(CapabilityError, ExecutionError)
        assert issubclass(CapabilityError, PaxmanError)

    def test_inference_provider_extends_capability(self) -> None:
        assert issubclass(InferenceProviderError, CapabilityError)
        assert issubclass(InferenceProviderError, ExecutionError)
        assert issubclass(InferenceProviderError, PaxmanError)

    def test_budget_exceeded_extends_paxman(self) -> None:
        assert issubclass(BudgetExceededError, PaxmanError)

    def test_reconciliation_extends_paxman(self) -> None:
        assert issubclass(ReconciliationError, PaxmanError)

    def test_replay_extends_paxman(self) -> None:
        assert issubclass(ReplayError, PaxmanError)

    def test_version_mismatch_extends_replay(self) -> None:
        assert issubclass(VersionMismatchError, ReplayError)
        assert issubclass(VersionMismatchError, PaxmanError)

    def test_hash_mismatch_extends_replay(self) -> None:
        assert issubclass(HashMismatchError, ReplayError)
        assert issubclass(HashMismatchError, PaxmanError)

    def test_capability_not_found_extends_replay(self) -> None:
        assert issubclass(CapabilityNotFoundError, ReplayError)
        assert issubclass(CapabilityNotFoundError, PaxmanError)

    def test_configuration_extends_paxman(self) -> None:
        assert issubclass(ConfigurationError, PaxmanError)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestConstruction:
    """Each error can be instantiated with a message."""

    @pytest.mark.parametrize("cls", ALL_12)
    def test_construction_with_message(self, cls: type) -> None:
        exc = cls("test error message")
        assert str(exc) == "test error message"
        assert exc.message == "test error message"
        assert isinstance(exc.context, dict)

    @pytest.mark.parametrize("cls", ALL_12)
    def test_construction_with_context(self, cls: type) -> None:
        exc = cls("error", context={"key": "value"})
        assert exc.context == {"key": "value"}

    @pytest.mark.parametrize("cls", ALL_12)
    def test_can_be_raised_and_caught(self, cls: type) -> None:
        with pytest.raises(cls):
            raise cls("boom")

    @pytest.mark.parametrize("cls", ALL_12)
    def test_caught_as_paxman_error(self, cls: type) -> None:
        with pytest.raises(PaxmanError):
            raise cls("boom")

    @pytest.mark.parametrize("cls", ALL_12)
    def test_caught_as_exception(self, cls: type) -> None:
        with pytest.raises(Exception, match="boom"):
            raise cls("boom")
