"""Unit tests for ``paxman.artifact.diagnostics`` — DiagnosticStore."""

from __future__ import annotations

import pytest

from paxman.artifact.diagnostics import DiagnosticStore
from paxman.capabilities.result import Diagnostic, DiagnosticCode, DiagnosticSeverity

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

_DIAG_INFO = Diagnostic(
    code=DiagnosticCode.CAPABILITY_OK,
    severity=DiagnosticSeverity.INFO,
    message="Completed successfully",
)

_DIAG_WARN = Diagnostic(
    code=DiagnosticCode.PATTERN_NO_MATCH,
    severity=DiagnosticSeverity.WARNING,
    message="Pattern matched 0 times",
)

_DIAG_ERR = Diagnostic(
    code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
    severity=DiagnosticSeverity.ERROR,
    message="Capability raised an exception",
)

_DIAG_INFO_2 = Diagnostic(
    code=DiagnosticCode.INPUT_NOT_SUPPORTED,
    severity=DiagnosticSeverity.INFO,
    message="Input format not supported",
)

_ALL_NOTES: tuple[Diagnostic, ...] = (_DIAG_INFO, _DIAG_WARN, _DIAG_ERR, _DIAG_INFO_2)


# ============================================================================
# Construction
# ============================================================================


@pytest.mark.deterministic
def test_diagnostic_store_empty() -> None:
    """DiagnosticStore defaults to empty notes."""
    store = DiagnosticStore()
    assert store.notes == ()


@pytest.mark.deterministic
def test_diagnostic_store_with_notes() -> None:
    """DiagnosticStore accepts a tuple of Diagnostic records."""
    store = DiagnosticStore(notes=(_DIAG_INFO, _DIAG_WARN))
    assert store.notes == (_DIAG_INFO, _DIAG_WARN)


@pytest.mark.deterministic
def test_diagnostic_store_frozen() -> None:
    """DiagnosticStore is frozen."""
    store = DiagnosticStore()
    with pytest.raises(AttributeError):
        store.notes = (_DIAG_INFO,)  # type: ignore[misc]


# ============================================================================
# by_severity
# ============================================================================


@pytest.mark.deterministic
def test_by_severity_filters_correctly() -> None:
    """by_severity returns only diagnostics with the matching severity."""
    store = DiagnosticStore(notes=_ALL_NOTES)

    info_results = store.by_severity(DiagnosticSeverity.INFO)
    assert info_results == (_DIAG_INFO, _DIAG_INFO_2)

    warn_results = store.by_severity(DiagnosticSeverity.WARNING)
    assert warn_results == (_DIAG_WARN,)

    err_results = store.by_severity(DiagnosticSeverity.ERROR)
    assert err_results == (_DIAG_ERR,)


@pytest.mark.deterministic
def test_by_severity_empty_result() -> None:
    """by_severity returns empty tuple when no diagnostic matches."""
    store = DiagnosticStore(notes=(_DIAG_INFO,))
    assert store.by_severity(DiagnosticSeverity.ERROR) == ()


@pytest.mark.deterministic
def test_by_severity_empty_store() -> None:
    """by_severity on empty store returns empty tuple."""
    store = DiagnosticStore()
    assert store.by_severity(DiagnosticSeverity.INFO) == ()


# ============================================================================
# by_code
# ============================================================================


@pytest.mark.deterministic
def test_by_code_filters_correctly() -> None:
    """by_code returns only diagnostics with the matching code."""
    store = DiagnosticStore(notes=_ALL_NOTES)

    cap_ok = store.by_code(DiagnosticCode.CAPABILITY_OK)
    assert cap_ok == (_DIAG_INFO,)

    pat_no_match = store.by_code(DiagnosticCode.PATTERN_NO_MATCH)
    assert pat_no_match == (_DIAG_WARN,)


@pytest.mark.deterministic
def test_by_code_empty_result() -> None:
    """by_code returns empty tuple when no diagnostic matches."""
    store = DiagnosticStore(notes=(_DIAG_INFO,))
    assert store.by_code(DiagnosticCode.POLICY_EXCLUDES) == ()


@pytest.mark.deterministic
def test_by_code_empty_store() -> None:
    """by_code on empty store returns empty tuple."""
    store = DiagnosticStore()
    assert store.by_code(DiagnosticCode.CAPABILITY_OK) == ()


# ============================================================================
# errors property
# ============================================================================


@pytest.mark.deterministic
def test_errors_empty_store() -> None:
    """errors returns empty tuple on empty store."""
    assert DiagnosticStore().errors == ()


@pytest.mark.deterministic
def test_errors_only_error_severity() -> None:
    """errors returns only ERROR-severity diagnostics."""
    store = DiagnosticStore(notes=_ALL_NOTES)
    assert store.errors == (_DIAG_ERR,)


@pytest.mark.deterministic
def test_errors_no_errors() -> None:
    """errors returns empty tuple when no ERROR diagnostics exist."""
    store = DiagnosticStore(notes=(_DIAG_INFO, _DIAG_WARN))
    assert store.errors == ()


# ============================================================================
# warnings property
# ============================================================================


@pytest.mark.deterministic
def test_warnings_empty_store() -> None:
    """warnings returns empty tuple on empty store."""
    assert DiagnosticStore().warnings == ()


@pytest.mark.deterministic
def test_warnings_only_warning_severity() -> None:
    """warnings returns only WARNING-severity diagnostics."""
    store = DiagnosticStore(notes=_ALL_NOTES)
    assert store.warnings == (_DIAG_WARN,)


@pytest.mark.deterministic
def test_warnings_no_warnings() -> None:
    """warnings returns empty tuple when no WARNING diagnostics exist."""
    store = DiagnosticStore(notes=(_DIAG_INFO, _DIAG_ERR))
    assert store.warnings == ()
