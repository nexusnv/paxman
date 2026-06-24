"""Tests for paxman.reconciler.unresolved — explicit UNRESOLVED state handling."""

from __future__ import annotations

import pytest

from paxman.capabilities.result import Diagnostic, DiagnosticCode, DiagnosticSeverity
from paxman.contract._types import ResolutionPolicy, ResolutionStrategy
from paxman.contract.canonical import CanonicalField
from paxman.reconciler.unresolved import (
    apply_fallback,
    make_unresolved_result,
    should_use_default,
)
from paxman.types import ConfidenceBand, FieldType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _str_field(
    *,
    required: bool = True,
    default: object = None,
    strategy: ResolutionStrategy = ResolutionStrategy.UNRESOLVED,
) -> CanonicalField:
    return CanonicalField(
        id="f1",
        path="supplier_name",
        name="supplier_name",
        type=FieldType.STRING,
        required=required,
        default=default,
        fallback_policy=ResolutionPolicy(strategy=strategy),
    )


# ---------------------------------------------------------------------------
# make_unresolved_result
# ---------------------------------------------------------------------------


class TestMakeUnresolvedResult:
    def test_basic_unresolved(self) -> None:
        field = _str_field()
        result = make_unresolved_result(field=field, reason="no_candidates")
        assert result.status == "UNRESOLVED"
        assert result.value is None
        assert result.confidence == 0.0
        assert result.confidence_band == ConfidenceBand.UNTRUSTED
        assert result.field_id == "f1"
        assert result.field_path == "supplier_name"
        assert result.field_type_name == "STRING"

    def test_diagnostic_with_reason(self) -> None:
        field = _str_field()
        result = make_unresolved_result(field=field, reason="below_threshold")
        assert len(result.diagnostics) == 1
        diag = result.diagnostics[0]
        assert diag.code == DiagnosticCode.CAPABILITY_OK
        assert diag.severity == DiagnosticSeverity.INFO
        assert "below_threshold" in diag.message
        assert diag.context["reason"] == "below_threshold"
        assert diag.context["field_path"] == "supplier_name"

    def test_empty_reason_skips_diagnostic(self) -> None:
        field = _str_field()
        result = make_unresolved_result(field=field, reason="")
        assert result.diagnostics == ()

    def test_with_prebuilt_diagnostics(self) -> None:
        field = _str_field()
        prebuilt = (
            Diagnostic(
                code=DiagnosticCode.VALIDATION_FAILED,
                severity=DiagnosticSeverity.WARNING,
                message="constraint failed",
            ),
        )
        result = make_unresolved_result(
            field=field,
            reason="validation_failed",
            diagnostics=prebuilt,
        )
        assert len(result.diagnostics) == 2
        assert result.diagnostics[0].code == DiagnosticCode.VALIDATION_FAILED
        assert result.diagnostics[1].code == DiagnosticCode.CAPABILITY_OK

    def test_type_error_for_non_field(self) -> None:
        with pytest.raises(TypeError, match="field must be a CanonicalField"):
            make_unresolved_result(field="not-a-field", reason="x")  # type: ignore[arg-type]

    def test_type_error_for_none(self) -> None:
        with pytest.raises(TypeError, match="field must be a CanonicalField"):
            make_unresolved_result(field=None, reason="x")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# should_use_default
# ---------------------------------------------------------------------------


class TestShouldUseDefault:
    def test_use_default_with_non_none_default_returns_true(self) -> None:
        field = _str_field(default="fallback", strategy=ResolutionStrategy.USE_DEFAULT)
        assert should_use_default(field) is True

    def test_use_default_with_none_default_returns_false(self) -> None:
        field = _str_field(default=None, strategy=ResolutionStrategy.USE_DEFAULT)
        assert should_use_default(field) is False

    def test_unresolved_strategy_returns_false(self) -> None:
        field = _str_field(default="fallback", strategy=ResolutionStrategy.UNRESOLVED)
        assert should_use_default(field) is False

    def test_require_human_returns_false(self) -> None:
        field = _str_field(default="fallback", strategy=ResolutionStrategy.REQUIRE_HUMAN)
        assert should_use_default(field) is False

    def test_type_error_for_non_field(self) -> None:
        with pytest.raises(TypeError, match="field must be a CanonicalField"):
            should_use_default("not-a-field")  # type: ignore[arg-type]

    def test_type_error_for_none(self) -> None:
        with pytest.raises(TypeError, match="field must be a CanonicalField"):
            should_use_default(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# apply_fallback
# ---------------------------------------------------------------------------


class TestApplyFallback:
    def test_use_default_returns_resolved(self) -> None:
        field = _str_field(
            default="default_val",
            strategy=ResolutionStrategy.USE_DEFAULT,
        )
        result = apply_fallback(field=field, reason="no_candidates")
        assert result.status == "RESOLVED"
        assert result.value == "default_val"
        assert result.confidence == 0.60
        assert result.confidence_band == ConfidenceBand.MEDIUM
        assert result.merge_strategy_used == "USE_DEFAULT"

    def test_use_default_adds_diagnostic(self) -> None:
        field = _str_field(
            default="fallback",
            strategy=ResolutionStrategy.USE_DEFAULT,
        )
        result = apply_fallback(field=field, reason="no_candidates")
        assert len(result.diagnostics) == 1
        assert "used field default" in result.diagnostics[0].message

    def test_use_default_with_prebuilt_diagnostics(self) -> None:
        field = _str_field(
            default="fallback",
            strategy=ResolutionStrategy.USE_DEFAULT,
        )
        prebuilt = (
            Diagnostic(
                code=DiagnosticCode.PATTERN_NO_MATCH,
                severity=DiagnosticSeverity.INFO,
                message="pattern did not match",
            ),
        )
        result = apply_fallback(field=field, reason="no_match", diagnostics=prebuilt)
        assert len(result.diagnostics) == 2
        # Prebuilt diagnostics come first
        assert result.diagnostics[0].code == DiagnosticCode.PATTERN_NO_MATCH

    def test_unresolved_default_strategy(self) -> None:
        field = _str_field(strategy=ResolutionStrategy.UNRESOLVED)
        result = apply_fallback(field=field, reason="threshold_not_met")
        assert result.status == "UNRESOLVED"
        assert result.value is None
        assert result.confidence == 0.0
        assert result.confidence_band == ConfidenceBand.UNTRUSTED

    def test_require_human_returns_unresolved_with_diagnostic(self) -> None:
        field = _str_field(strategy=ResolutionStrategy.REQUIRE_HUMAN)
        result = apply_fallback(field=field, reason="below_threshold")
        assert result.status == "UNRESOLVED"
        assert result.value is None
        assert result.confidence == 0.0
        assert len(result.diagnostics) >= 1
        # Check for the REQUIRE_HUMAN diagnostic
        messages = [d.message for d in result.diagnostics]
        assert any("requires human review" in m for m in messages)

    def test_require_human_diagnostic_severity(self) -> None:
        field = _str_field(strategy=ResolutionStrategy.REQUIRE_HUMAN)
        result = apply_fallback(field=field, reason="ambiguous")
        # The REQUIRE_HUMAN diagnostic should be WARNING
        require_human_diags = [
            d for d in result.diagnostics if "requires human review" in d.message
        ]
        assert len(require_human_diags) == 1
        assert require_human_diags[0].severity == DiagnosticSeverity.WARNING

    def test_unresolved_with_custom_diagnostics(self) -> None:
        field = _str_field(strategy=ResolutionStrategy.UNRESOLVED)
        prebuilt = (
            Diagnostic(
                code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                severity=DiagnosticSeverity.ERROR,
                message="capability crashed",
            ),
        )
        result = apply_fallback(
            field=field,
            reason="execution_error",
            diagnostics=prebuilt,
        )
        assert len(result.diagnostics) == 2
        assert result.diagnostics[0].code == DiagnosticCode.CAPABILITY_INVOKE_FAILED
        assert result.diagnostics[1].code == DiagnosticCode.CAPABILITY_OK

    def test_type_error_for_non_field(self) -> None:
        with pytest.raises(TypeError, match="field must be a CanonicalField"):
            apply_fallback(field="not-a-field", reason="x")  # type: ignore[arg-type]

    def test_type_error_for_none(self) -> None:
        with pytest.raises(TypeError, match="field must be a CanonicalField"):
            apply_fallback(field=None, reason="x")  # type: ignore[arg-type]
