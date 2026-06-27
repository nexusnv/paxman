"""Unit tests for ``paxman.errors`` — the 18-class PaxmanError hierarchy.

Per V1_ACCEPTANCE_CRITERIA.md §2.2, ``errors.py`` must have 100% line coverage.
These tests exercise every code path: each class instantiation, each
validator, the context-None guard, the error_code validation, and the
exception inheritance.

Note: the hierarchy was 17 classes in Sprint 1 (per the
[Sprint 1 — Foundation](https://github.com/nexusnv/paxman-wiki/blob/main/Internal-Development/Sprint-1-—-Foundation.md) D1.10); Sprint 6 added the 18th
class, :class:`~paxman.errors.CapabilityNotFoundError`, per the
[V1 acceptance criteria](https://github.com/nexusnv/paxman-wiki/blob/main/Internal-Development/V1-acceptance-criteria.md) §1.5 (see the
[CHANGES_LOG](https://github.com/nexusnv/paxman-wiki/blob/main/Internal-Development/CHANGES-LOG.md) C1).
The current source of truth is the ``__all__`` list in ``src/paxman/errors.py``.
"""

from __future__ import annotations

import pytest

from paxman.errors import (
    BudgetExceededError,
    CapabilityError,
    CapabilityNotFoundError,
    ConfigurationError,
    ExecutionError,
    HashMismatchError,
    InferenceProviderError,
    InvalidBudgetError,
    InvalidConstraintError,
    InvalidContractError,
    InvalidPathError,
    InvalidPolicyError,
    InvalidSemanticTagError,
    PaxmanError,
    ReconciliationError,
    ReplayError,
    UnsupportedFieldTypeError,
    VersionMismatchError,
)

# --- 18-class inventory -----------------------------------------------------

ALL_18 = [
    PaxmanError,
    InvalidContractError,
    UnsupportedFieldTypeError,
    InvalidConstraintError,
    InvalidPathError,
    InvalidSemanticTagError,
    ExecutionError,
    CapabilityError,
    InferenceProviderError,
    BudgetExceededError,
    ReconciliationError,
    ReplayError,
    VersionMismatchError,
    HashMismatchError,
    ConfigurationError,
    InvalidBudgetError,
    InvalidPolicyError,
    CapabilityNotFoundError,
]
ALL_18_NAMES = [c.__name__ for c in ALL_18]
PUBLIC_12 = [
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
    ConfigurationError,
    CapabilityNotFoundError,
]


def test_eighteen_classes_total() -> None:
    """The 18 classes are exactly the ARCHITECTURE.md §6.2 + Sprint 6 classes."""
    from paxman import errors

    module_classes = {
        name
        for name, value in vars(errors).items()
        if isinstance(value, type)
        and issubclass(value, BaseException)
        and value is not BaseException
    }
    assert module_classes == set(ALL_18_NAMES)


# --- Inheritance ------------------------------------------------------------


@pytest.mark.parametrize("cls", ALL_18)
def test_class_inherits_from_paxman_error_or_exception(cls: type) -> None:
    """Every error class inherits from ``PaxmanError`` (which inherits from ``Exception``)."""
    assert issubclass(cls, Exception), f"{cls.__name__} does not inherit from Exception"
    if cls is not PaxmanError:
        assert issubclass(cls, PaxmanError), f"{cls.__name__} does not inherit from PaxmanError"


def test_inheritance_chain_capability_error_to_inference_provider() -> None:
    """``CapabilityError`` -> ``ExecutionError`` -> ``PaxmanError``; ``InferenceProviderError`` -> ``CapabilityError``."""
    assert issubclass(CapabilityError, ExecutionError)
    assert issubclass(InferenceProviderError, CapabilityError)
    assert issubclass(ExecutionError, PaxmanError)


def test_inheritance_chain_invalid_contract_to_children() -> None:
    """``UnsupportedFieldTypeError`` etc. -> ``InvalidContractError`` -> ``PaxmanError``."""
    for child in (
        UnsupportedFieldTypeError,
        InvalidConstraintError,
        InvalidPathError,
        InvalidSemanticTagError,
    ):
        assert issubclass(child, InvalidContractError)
        assert issubclass(child, PaxmanError)


def test_inheritance_chain_configuration_error_to_children() -> None:
    """``InvalidBudgetError`` / ``InvalidPolicyError`` -> ``ConfigurationError`` -> ``PaxmanError``."""
    assert issubclass(InvalidBudgetError, ConfigurationError)
    assert issubclass(InvalidPolicyError, ConfigurationError)


def test_inheritance_chain_replay_error_to_children() -> None:
    """``VersionMismatchError`` / ``HashMismatchError`` -> ``ReplayError`` -> ``PaxmanError``."""
    assert issubclass(VersionMismatchError, ReplayError)
    assert issubclass(HashMismatchError, ReplayError)


# --- Error codes ------------------------------------------------------------

EXPECTED_CODES = {
    "PaxmanError": "PAXMAN_ERROR",
    "InvalidContractError": "INVALID_CONTRACT",
    "UnsupportedFieldTypeError": "UNSUPPORTED_FIELD_TYPE",
    "InvalidConstraintError": "INVALID_CONSTRAINT",
    "InvalidPathError": "INVALID_PATH",
    "InvalidSemanticTagError": "INVALID_SEMANTIC_TAG",
    "ExecutionError": "EXECUTION_ERROR",
    "CapabilityError": "CAPABILITY_ERROR",
    "InferenceProviderError": "INFERENCE_PROVIDER_ERROR",
    "BudgetExceededError": "BUDGET_EXCEEDED",
    "ReconciliationError": "RECONCILIATION_ERROR",
    "ReplayError": "REPLAY_ERROR",
    "VersionMismatchError": "VERSION_MISMATCH",
    "HashMismatchError": "HASH_MISMATCH",
    "ConfigurationError": "CONFIGURATION_ERROR",
    "InvalidBudgetError": "INVALID_BUDGET",
    "InvalidPolicyError": "INVALID_POLICY",
    "CapabilityNotFoundError": "CAPABILITY_NOT_FOUND",
}


@pytest.mark.parametrize("cls", ALL_18)
def test_default_error_code_is_correct(cls: type) -> None:
    """The default error_code for each class is non-empty and matches the spec."""
    exc = cls("test message")
    assert exc.error_code == EXPECTED_CODES[cls.__name__]
    assert exc.error_code  # non-empty
    assert exc.error_code == exc.error_code.upper()  # SCREAMING_SNAKE_CASE
    assert exc.error_code.replace("_", "").isalnum()  # no special chars


# --- Construction ------------------------------------------------------------


@pytest.mark.parametrize("cls", ALL_18)
def test_minimal_construction(cls: type) -> None:
    """Every class can be constructed with just a message."""
    exc = cls("something went wrong")
    assert exc.message == "something went wrong"
    assert exc.error_code == EXPECTED_CODES[cls.__name__]
    assert exc.context == {}


@pytest.mark.parametrize("cls", ALL_18)
def test_construction_with_context(cls: type) -> None:
    """Every class accepts a context dict."""
    ctx = {"field_path": "$.x", "got": "str"}
    exc = cls("bad field", context=ctx)
    assert exc.context == ctx


@pytest.mark.parametrize("cls", ALL_18)
def test_construction_with_context_none_normalizes_to_empty_dict(cls: type) -> None:
    """``context=None`` is normalized to ``{}`` (per the spec)."""
    exc = cls("oops", context=None)
    assert exc.context == {}


@pytest.mark.parametrize("cls", ALL_18)
def test_message_is_required(cls: type) -> None:
    """Message must be a non-empty string."""
    with pytest.raises((ValueError, TypeError)):
        cls("")  # empty message rejected by validator


# --- Exception behavior -----------------------------------------------------


@pytest.mark.parametrize("cls", ALL_18)
def test_can_be_raised_and_caught(cls: type) -> None:
    """Every error class can be raised and caught by its own type."""
    with pytest.raises(cls):
        raise cls("boom")


@pytest.mark.parametrize("cls", ALL_18)
def test_caught_as_paxman_error(cls: type) -> None:
    """Every error class can be caught as ``PaxmanError`` (the base)."""
    with pytest.raises(PaxmanError):
        raise cls("boom")


@pytest.mark.parametrize("cls", ALL_18)
def test_caught_as_exception(cls: type) -> None:
    """Every error class is a real ``Exception``."""
    with pytest.raises(BaseException):  # noqa: B017  (blind exception is intentional)
        raise cls("boom")


@pytest.mark.parametrize("cls", ALL_18)
def test_str_returns_message(cls: type) -> None:
    """``str(exc)`` returns the message (per Python ``Exception`` convention)."""
    exc = cls("specific message")
    assert str(exc) == "specific message"


# --- Immutability ------------------------------------------------------------


@pytest.mark.parametrize("cls", ALL_18)
def test_frozen_no_attribute_assignment(cls: type) -> None:
    """Frozen attrs classes reject attribute assignment."""
    exc = cls("test")
    with pytest.raises((AttributeError, Exception)):
        exc.error_code = "HACKED"  # type: ignore[misc]


# --- Public-surface contract ------------------------------------------------


def test_public_12_are_reexported() -> None:
    """The public error re-export is exactly the 12-name set.

    This pins the **public re-export contract** in
    :mod:`paxman.api.errors`, not the internal :mod:`paxman.errors`
    module. ``paxman.errors`` is allowed to expose more symbols (the 6
    internal contract/configuration errors); what matters for
    downstream consumers is the 12-name set surfaced via
    :mod:`paxman.api.errors`.

    The comparison is **exact equality** (not ``issubset``), so:

    - removing any of the 12 public exports fails;
    - adding an undocumented public export fails (an ADR is required
      to widen the public surface — see the
      ``tests/public_api/test_public_api.py`` snapshot for the
      matching guard at the function-level).
    """
    from paxman.api import errors as api_errors

    public_names = {c.__name__ for c in PUBLIC_12}
    listed = set(getattr(api_errors, "__all__", []))
    assert listed == public_names, (
        f"paxman.api.errors.__all__ drift. "
        f"expected={sorted(public_names)}, got={sorted(listed)}, "
        f"missing={sorted(public_names - listed)}, "
        f"extra={sorted(listed - public_names)}"
    )


def test_all_18_are_in_dunder_all() -> None:
    """All 18 error names are listed in ``paxman.errors.__all__``."""
    from paxman import errors

    listed = set(getattr(errors, "__all__", []))
    expected = set(ALL_18_NAMES)
    assert expected.issubset(listed), f"Missing from __all__: {expected - listed}"


# --- Context validation -----------------------------------------------------


@pytest.mark.parametrize("cls", ALL_18)
def test_context_must_be_dict(cls: type) -> None:
    """Non-dict context raises ``TypeError`` (per the ``__attrs_post_init__`` guard)."""
    with pytest.raises(TypeError):
        cls("boom", context=["not", "a", "dict"])  # type: ignore[arg-type]
