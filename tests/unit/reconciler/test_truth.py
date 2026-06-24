"""Unit tests for :mod:`paxman.reconciler.truth`.

Tests cover:
- :class:`TruthLayer` enum values and member identity.
- :class:`ResolvedResult` valid construction (minimum, full, various combinations).
- ``__attrs_post_init__`` validation: empty strings blocked, type errors on
  every typed field, value-range violations for confidence, status/value
  invariant pairing (RESOLVED → non-None value, UNRESOLVED → 0.0 confidence).
"""

from __future__ import annotations

import pytest

from paxman.capabilities.result import Diagnostic, EvidenceRef
from paxman.reconciler.truth import ResolvedResult, TruthLayer
from paxman.types import ConfidenceBand

pytestmark = pytest.mark.unit


# ============================================================================
# TruthLayer
# ============================================================================


class TestTruthLayer:
    """Verify the three truth-layer enum members and their string values."""

    def test_members(self) -> None:
        assert TruthLayer.CONTRACT.value == "CONTRACT"
        assert TruthLayer.CANDIDATE.value == "CANDIDATE"
        assert TruthLayer.RESOLVED.value == "RESOLVED"

    def test_three_members_only(self) -> None:
        assert len(TruthLayer) == 3

    def test_members_are_unique(self) -> None:
        names = [m.name for m in TruthLayer]
        assert len(names) == len(set(names))
        values = [m.value for m in TruthLayer]
        assert len(values) == len(set(values))


# ============================================================================
# ResolvedResult — valid construction
# ============================================================================


class TestResolvedResultValid:
    """Happy-path construction of ResolvedResult with various parameter sets."""

    def test_minimal_unresolved(self) -> None:
        """Minimal valid construction: all defaults produce UNRESOLVED."""
        r = ResolvedResult(
            field_id="f1",
            field_path="supplier_name",
            field_type_name="STRING",
        )
        assert r.field_id == "f1"
        assert r.field_path == "supplier_name"
        assert r.field_type_name == "STRING"
        assert r.value is None
        assert r.confidence == 0.0
        assert r.confidence_band is ConfidenceBand.UNTRUSTED
        assert r.truth_layer is TruthLayer.RESOLVED
        assert r.evidence_refs == ()
        assert r.diagnostics == ()
        assert r.status == "UNRESOLVED"
        assert r.conflict_detected is False
        assert r.merge_strategy_used == ""

    def test_resolved_with_value(self) -> None:
        """A fully specified resolved result."""
        r = ResolvedResult(
            field_id="f1",
            field_path="supplier_name",
            field_type_name="STRING",
            value="ACME Corp",
            confidence=0.95,
            confidence_band=ConfidenceBand.CERTAIN,
            status="RESOLVED",
        )
        assert r.value == "ACME Corp"
        assert r.confidence == 0.95
        assert r.confidence_band is ConfidenceBand.CERTAIN
        assert r.status == "RESOLVED"

    def test_with_evidence_and_diagnostics(self) -> None:
        """Evidence refs and diagnostics are accepted as tuples."""
        from paxman.capabilities.result import DiagnosticCode, DiagnosticSeverity

        ev = EvidenceRef(
            capability_id="regex_extraction",
            capability_version="1.0",
            field_path="supplier_name",
        )
        diag = Diagnostic(
            code=DiagnosticCode.CAPABILITY_OK,
            severity=DiagnosticSeverity.INFO,
            message="ok",
        )
        r = ResolvedResult(
            field_id="f1",
            field_path="supplier_name",
            field_type_name="STRING",
            value="ACME Corp",
            confidence=0.85,
            confidence_band=ConfidenceBand.HIGH,
            status="RESOLVED",
            evidence_refs=(ev,),
            diagnostics=(diag,),
            conflict_detected=True,
            merge_strategy_used="PREFER_BY_EVIDENCE",
        )
        assert r.evidence_refs == (ev,)
        assert r.diagnostics == (diag,)
        assert r.conflict_detected is True
        assert r.merge_strategy_used == "PREFER_BY_EVIDENCE"

    def test_integer_confidence_accepted(self) -> None:
        """An int confidence value is accepted (converted to float)."""
        r = ResolvedResult(
            field_id="f1",
            field_path="x",
            field_type_name="STRING",
            confidence=1,
            confidence_band=ConfidenceBand.CERTAIN,
            value="ok",
            status="RESOLVED",
        )
        assert r.confidence == 1.0

    def test_confidence_zero_for_unresolved(self) -> None:
        """UNRESOLVED status with 0.0 confidence is valid."""
        r = ResolvedResult(
            field_id="f1",
            field_path="x",
            field_type_name="STRING",
            confidence=0.0,
            status="UNRESOLVED",
        )
        assert r.confidence == 0.0
        assert r.status == "UNRESOLVED"

    def test_confidence_almost_one(self) -> None:
        """Upper boundary: confidence == 1.0 is valid."""
        r = ResolvedResult(
            field_id="f1",
            field_path="x",
            field_type_name="STRING",
            confidence=1.0,
            confidence_band=ConfidenceBand.CERTAIN,
            value="x",
            status="RESOLVED",
        )
        assert r.confidence == 1.0

    def test_all_field_types_name(self) -> None:
        """field_type_name can be any non-empty string."""
        for name in ("STRING", "INTEGER", "MONEY", "custom_type"):
            r = ResolvedResult(
                field_id="f1",
                field_path="x",
                field_type_name=name,
            )
            assert r.field_type_name == name


# ============================================================================
# ResolvedResult — validation failures
# ============================================================================


class TestResolvedResultFieldIdValidation:
    """field_id must be a non-empty string."""

    @pytest.mark.parametrize(
        "bad_value",
        [""],
    )
    def test_empty_string(self, bad_value: str) -> None:
        with pytest.raises(ValueError, match="field_id must be a non-empty string"):
            ResolvedResult(
                field_id=bad_value,
                field_path="x",
                field_type_name="STRING",
            )

    @pytest.mark.parametrize(
        "bad_value",
        [None, 0, 1, [], {}],
    )
    def test_non_string_type(self, bad_value: object) -> None:
        with pytest.raises(ValueError, match="field_id must be a non-empty string"):
            ResolvedResult(
                field_id=bad_value,  # type: ignore[arg-type]
                field_path="x",
                field_type_name="STRING",
            )


class TestResolvedResultFieldPathValidation:
    """field_path must be a non-empty string."""

    @pytest.mark.parametrize(
        "bad_value",
        [""],
    )
    def test_empty_string(self, bad_value: str) -> None:
        with pytest.raises(ValueError, match="field_path must be a non-empty string"):
            ResolvedResult(
                field_id="f1",
                field_path=bad_value,
                field_type_name="STRING",
            )

    @pytest.mark.parametrize(
        "bad_value",
        [None, 0, True, [], {}],
    )
    def test_non_string_type(self, bad_value: object) -> None:
        with pytest.raises(ValueError, match="field_path must be a non-empty string"):
            ResolvedResult(
                field_id="f1",
                field_path=bad_value,  # type: ignore[arg-type]
                field_type_name="STRING",
            )


class TestResolvedResultFieldTypeNameValidation:
    """field_type_name must be a non-empty string."""

    @pytest.mark.parametrize(
        "bad_value",
        [""],
    )
    def test_empty_string(self, bad_value: str) -> None:
        with pytest.raises(ValueError, match="field_type_name must be a non-empty string"):
            ResolvedResult(
                field_id="f1",
                field_path="x",
                field_type_name=bad_value,
            )

    @pytest.mark.parametrize(
        "bad_value",
        [None, 0, True],
    )
    def test_non_string_type(self, bad_value: object) -> None:
        with pytest.raises(ValueError, match="field_type_name must be a non-empty string"):
            ResolvedResult(
                field_id="f1",
                field_path="x",
                field_type_name=bad_value,  # type: ignore[arg-type]
            )


class TestResolvedResultConfidenceTypeValidation:
    """confidence must be a number (bool rejected, non-numeric rejected)."""

    def test_bool_rejected(self) -> None:
        with pytest.raises(TypeError, match="confidence must be a number"):
            ResolvedResult(
                field_id="f1",
                field_path="x",
                field_type_name="STRING",
                confidence=True,  # type: ignore[arg-type]
            )

    def test_string_rejected(self) -> None:
        with pytest.raises(TypeError, match="confidence must be a number"):
            ResolvedResult(
                field_id="f1",
                field_path="x",
                field_type_name="STRING",
                confidence="0.5",  # type: ignore[arg-type]
            )

    def test_none_rejected(self) -> None:
        with pytest.raises(TypeError, match="confidence must be a number"):
            ResolvedResult(
                field_id="f1",
                field_path="x",
                field_type_name="STRING",
                confidence=None,  # type: ignore[arg-type]
            )


class TestResolvedResultConfidenceRangeValidation:
    """confidence must be in [0.0, 1.0]."""

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError, match=r"confidence must be in \[0\.0, 1\.0\]"):
            ResolvedResult(
                field_id="f1",
                field_path="x",
                field_type_name="STRING",
                confidence=-0.01,
            )

    def test_greater_than_one_raises(self) -> None:
        with pytest.raises(ValueError, match=r"confidence must be in \[0\.0, 1\.0\]"):
            ResolvedResult(
                field_id="f1",
                field_path="x",
                field_type_name="STRING",
                confidence=1.0001,
            )

    def test_just_above_one_raises(self) -> None:
        with pytest.raises(ValueError, match=r"confidence must be in \[0\.0, 1\.0\]"):
            ResolvedResult(field_id="f1", field_path="x", field_type_name="STRING", confidence=1.01)

    def test_negative_int_raises(self) -> None:
        with pytest.raises(ValueError, match=r"confidence must be in \[0\.0, 1\.0\]"):
            ResolvedResult(
                field_id="f1",
                field_path="x",
                field_type_name="STRING",
                confidence=-1,
            )


class TestResolvedResultConfidenceBandValidation:
    """confidence_band must be a ConfidenceBand enum member."""

    def test_none_raises(self) -> None:
        with pytest.raises(TypeError, match="confidence_band must be a ConfidenceBand"):
            ResolvedResult(
                field_id="f1",
                field_path="x",
                field_type_name="STRING",
                confidence_band=None,  # type: ignore[arg-type]
            )

    def test_string_raises(self) -> None:
        with pytest.raises(TypeError, match="confidence_band must be a ConfidenceBand"):
            ResolvedResult(
                field_id="f1",
                field_path="x",
                field_type_name="STRING",
                confidence_band="CERTAIN",  # type: ignore[arg-type]
            )


class TestResolvedResultTruthLayerValidation:
    """truth_layer must be a TruthLayer enum member."""

    def test_none_raises(self) -> None:
        with pytest.raises(TypeError, match="truth_layer must be a TruthLayer"):
            ResolvedResult(
                field_id="f1",
                field_path="x",
                field_type_name="STRING",
                truth_layer=None,  # type: ignore[arg-type]
            )

    def test_string_raises(self) -> None:
        with pytest.raises(TypeError, match="truth_layer must be a TruthLayer"):
            ResolvedResult(
                field_id="f1",
                field_path="x",
                field_type_name="STRING",
                truth_layer="RESOLVED",  # type: ignore[arg-type]
            )


class TestResolvedResultEvidenceRefsValidation:
    """evidence_refs must be a tuple."""

    @pytest.mark.parametrize(
        "bad_value",
        [None, [EvidenceRef("r", "1.0", "x")], (EvidenceRef("r", "1.0", "x"),)],  # list
    )
    def test_list_or_none_raises(self, bad_value: object) -> None:
        if isinstance(bad_value, list):
            with pytest.raises(TypeError, match="evidence_refs must be a tuple"):
                ResolvedResult(
                    field_id="f1",
                    field_path="x",
                    field_type_name="STRING",
                    evidence_refs=bad_value,  # type: ignore[arg-type]
                )
        else:
            # tuple is actually fine — test non-tuple values
            pass

    def test_none_raises(self) -> None:
        with pytest.raises(TypeError, match="evidence_refs must be a tuple"):
            ResolvedResult(
                field_id="f1",
                field_path="x",
                field_type_name="STRING",
                evidence_refs=None,  # type: ignore[arg-type]
            )

    def test_list_raises(self) -> None:
        ev = EvidenceRef(
            capability_id="regex_extraction",
            capability_version="1.0",
            field_path="x",
        )
        with pytest.raises(TypeError, match="evidence_refs must be a tuple"):
            ResolvedResult(
                field_id="f1",
                field_path="x",
                field_type_name="STRING",
                evidence_refs=[ev],  # type: ignore[arg-type]
            )


class TestResolvedResultDiagnosticsValidation:
    """diagnostics must be a tuple."""

    def test_none_raises(self) -> None:
        with pytest.raises(TypeError, match="diagnostics must be a tuple"):
            ResolvedResult(
                field_id="f1",
                field_path="x",
                field_type_name="STRING",
                diagnostics=None,  # type: ignore[arg-type]
            )

    def test_list_raises(self) -> None:
        from paxman.capabilities.result import DiagnosticCode

        d = Diagnostic(code=DiagnosticCode.CAPABILITY_OK, message="ok")
        with pytest.raises(TypeError, match="diagnostics must be a tuple"):
            ResolvedResult(
                field_id="f1",
                field_path="x",
                field_type_name="STRING",
                diagnostics=[d],  # type: ignore[arg-type]
            )


class TestResolvedResultStatusValidation:
    """status must be 'RESOLVED' or 'UNRESOLVED'."""

    @pytest.mark.parametrize(
        "bad_status",
        ["", "resolved", "UNRESOLVED ", "PARTIAL", "SUCCESS", None, 0],
    )
    def test_invalid_status_raises(self, bad_status: object) -> None:
        with pytest.raises(ValueError, match="status must be 'RESOLVED' or 'UNRESOLVED'"):
            ResolvedResult(
                field_id="f1",
                field_path="x",
                field_type_name="STRING",
                status=bad_status,  # type: ignore[arg-type]
            )


class TestResolvedResultStatusValueInvariants:
    """Status/value pairing invariants."""

    def test_resolved_with_none_value_raises(self) -> None:
        """RESOLVED status requires a non-None value."""
        with pytest.raises(ValueError, match="status='RESOLVED' requires value to be not None"):
            ResolvedResult(
                field_id="f1",
                field_path="x",
                field_type_name="STRING",
                value=None,
                confidence=0.9,
                confidence_band=ConfidenceBand.HIGH,
                status="RESOLVED",
            )

    def test_unresolved_with_nonzero_confidence_raises(self) -> None:
        """UNRESOLVED status requires confidence == 0.0."""
        with pytest.raises(ValueError, match=r"status='UNRESOLVED' requires confidence to be 0\.0"):
            ResolvedResult(
                field_id="f1",
                field_path="x",
                field_type_name="STRING",
                confidence=0.5,
                status="UNRESOLVED",
            )

    def test_unresolved_with_small_positive_confidence_raises(self) -> None:
        """Even a tiny non-zero confidence is rejected for UNRESOLVED."""
        with pytest.raises(ValueError, match=r"status='UNRESOLVED' requires confidence to be 0\.0"):
            ResolvedResult(
                field_id="f1",
                field_path="x",
                field_type_name="STRING",
                confidence=0.001,
                status="UNRESOLVED",
            )


class TestResolvedResultConflictDetectedValidation:
    """conflict_detected must be a bool."""

    @pytest.mark.parametrize(
        "bad_value",
        [None, 0, 1, "True", "false"],
    )
    def test_non_bool_raises(self, bad_value: object) -> None:
        with pytest.raises(TypeError, match="conflict_detected must be a bool"):
            ResolvedResult(
                field_id="f1",
                field_path="x",
                field_type_name="STRING",
                conflict_detected=bad_value,  # type: ignore[arg-type]
            )


class TestResolvedResultMergeStrategyValidation:
    """merge_strategy_used must be a str."""

    @pytest.mark.parametrize(
        "bad_value",
        [None, 0, True, [], {}],
    )
    def test_non_string_raises(self, bad_value: object) -> None:
        with pytest.raises(TypeError, match="merge_strategy_used must be a str"):
            ResolvedResult(
                field_id="f1",
                field_path="x",
                field_type_name="STRING",
                merge_strategy_used=bad_value,  # type: ignore[arg-type]
            )


class TestResolvedResultDefaultTruthLayer:
    """truth_layer defaults to TruthLayer.RESOLVED (per design)."""

    def test_default_is_resolved(self) -> None:
        r = ResolvedResult(field_id="f1", field_path="x", field_type_name="STRING")
        assert r.truth_layer is TruthLayer.RESOLVED

    def test_explicit_contract(self) -> None:
        r = ResolvedResult(
            field_id="f1",
            field_path="x",
            field_type_name="STRING",
            truth_layer=TruthLayer.CONTRACT,
        )
        assert r.truth_layer is TruthLayer.CONTRACT

    def test_explicit_candidate(self) -> None:
        r = ResolvedResult(
            field_id="f1",
            field_path="x",
            field_type_name="STRING",
            truth_layer=TruthLayer.CANDIDATE,
        )
        assert r.truth_layer is TruthLayer.CANDIDATE
