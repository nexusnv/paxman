"""Unit tests for :mod:`paxman.reconciler.confidence`.

Tests cover:
- :func:`float_to_band`: type/range validation and boundary mapping for
  all five :class:`ConfidenceBand` values.
- :func:`assign_confidence`: type and value validation, rubric math
  (base + per-candidate + per-evidence + validation + conflict +
  capability-source bonus), clamping, and capping behaviour.
"""

from __future__ import annotations

import pytest

from paxman.reconciler.confidence import assign_confidence, float_to_band
from paxman.types import ConfidenceBand

pytestmark = pytest.mark.unit


# ============================================================================
# float_to_band — type validation
# ============================================================================


class TestFloatToBandTypeValidation:
    """float_to_band rejects non-numeric and bool inputs."""

    def test_bool_rejected(self) -> None:
        with pytest.raises(TypeError, match="confidence must be a number"):
            float_to_band(True)  # type: ignore[arg-type]

    def test_string_rejected(self) -> None:
        with pytest.raises(TypeError, match="confidence must be a number"):
            float_to_band("0.5")  # type: ignore[arg-type]

    def test_none_rejected(self) -> None:
        with pytest.raises(TypeError, match="confidence must be a number"):
            float_to_band(None)  # type: ignore[arg-type]

    def test_list_rejected(self) -> None:
        with pytest.raises(TypeError, match="confidence must be a number"):
            float_to_band([0.5])  # type: ignore[arg-type]


class TestFloatToBandRangeValidation:
    """float_to_band rejects values outside [0.0, 1.0]."""

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError, match=r"confidence must be in \[0.0, 1.0\]"):
            float_to_band(-0.01)

    def test_above_one_raises(self) -> None:
        with pytest.raises(ValueError, match=r"confidence must be in \[0.0, 1.0\]"):
            float_to_band(1.0001)

    def test_large_positive_raises(self) -> None:
        with pytest.raises(ValueError, match=r"confidence must be in \[0.0, 1.0\]"):
            float_to_band(100.0)


# ============================================================================
# float_to_band — band boundary mapping
# ============================================================================


class TestFloatToBandMapping:
    """Map confidence values to the correct ConfidenceBand at every boundary."""

    # CERTAIN: [0.95, 1.00]
    @pytest.mark.parametrize(
        "value",
        [0.95, 0.96, 0.99, 1.0, 0.951],
    )
    def test_certain(self, value: float) -> None:
        assert float_to_band(value) is ConfidenceBand.CERTAIN

    # HIGH: [0.80, 0.95)
    @pytest.mark.parametrize(
        "value",
        [0.80, 0.85, 0.90, 0.949, 0.801],
    )
    def test_high(self, value: float) -> None:
        assert float_to_band(value) is ConfidenceBand.HIGH

    # MEDIUM: [0.60, 0.80)
    @pytest.mark.parametrize(
        "value",
        [0.60, 0.65, 0.70, 0.75, 0.799, 0.601],
    )
    def test_medium(self, value: float) -> None:
        assert float_to_band(value) is ConfidenceBand.MEDIUM

    # LOW: [0.30, 0.60)
    @pytest.mark.parametrize(
        "value",
        [0.30, 0.35, 0.40, 0.50, 0.55, 0.599, 0.301],
    )
    def test_low(self, value: float) -> None:
        assert float_to_band(value) is ConfidenceBand.LOW

    # UNTRUSTED: [0.00, 0.30)
    @pytest.mark.parametrize(
        "value",
        [0.0, 0.05, 0.10, 0.20, 0.25, 0.299, 0.001],
    )
    def test_untrusted(self, value: float) -> None:
        assert float_to_band(value) is ConfidenceBand.UNTRUSTED

    # --- Just below boundaries (should map to NEXT lower band) ---

    def test_just_below_certain(self) -> None:
        assert float_to_band(0.949) is ConfidenceBand.HIGH

    def test_just_below_high(self) -> None:
        assert float_to_band(0.799) is ConfidenceBand.MEDIUM

    def test_just_below_medium(self) -> None:
        assert float_to_band(0.599) is ConfidenceBand.LOW

    def test_just_below_low(self) -> None:
        assert float_to_band(0.299) is ConfidenceBand.UNTRUSTED

    def test_int_confidence(self) -> None:
        """An int value is accepted (converted to float internally)."""
        assert float_to_band(1) is ConfidenceBand.CERTAIN
        assert float_to_band(0) is ConfidenceBand.UNTRUSTED


# ============================================================================
# assign_confidence — type validation
# ============================================================================


class TestAssignConfidenceTypeValidation:
    """assign_confidence rejects wrong argument types."""

    def test_candidate_count_bool(self) -> None:
        with pytest.raises(TypeError, match="candidate_count must be an int"):
            assign_confidence(
                candidate_count=True,  # type: ignore[arg-type]
                evidence_count=0,
                capability_ids=(),
                has_validation_pass=False,
                has_conflict=False,
            )

    def test_candidate_count_string(self) -> None:
        with pytest.raises(TypeError, match="candidate_count must be an int"):
            assign_confidence(
                candidate_count="2",  # type: ignore[arg-type]
                evidence_count=0,
                capability_ids=(),
                has_validation_pass=False,
                has_conflict=False,
            )

    def test_evidence_count_bool(self) -> None:
        with pytest.raises(TypeError, match="evidence_count must be an int"):
            assign_confidence(
                candidate_count=0,
                evidence_count=True,  # type: ignore[arg-type]
                capability_ids=(),
                has_validation_pass=False,
                has_conflict=False,
            )

    def test_evidence_count_string(self) -> None:
        with pytest.raises(TypeError, match="evidence_count must be an int"):
            assign_confidence(
                candidate_count=0,
                evidence_count="3",  # type: ignore[arg-type]
                capability_ids=(),
                has_validation_pass=False,
                has_conflict=False,
            )

    def test_has_validation_pass_non_bool(self) -> None:
        with pytest.raises(TypeError, match="has_validation_pass must be a bool"):
            assign_confidence(
                candidate_count=0,
                evidence_count=0,
                capability_ids=(),
                has_validation_pass="True",  # type: ignore[arg-type]  # noqa: S106
                has_conflict=False,
            )

    def test_has_validation_pass_none(self) -> None:
        with pytest.raises(TypeError, match="has_validation_pass must be a bool"):
            assign_confidence(
                candidate_count=0,
                evidence_count=0,
                capability_ids=(),
                has_validation_pass=None,  # type: ignore[arg-type]
                has_conflict=False,
            )

    def test_has_conflict_non_bool(self) -> None:
        with pytest.raises(TypeError, match="has_conflict must be a bool"):
            assign_confidence(
                candidate_count=0,
                evidence_count=0,
                capability_ids=(),
                has_validation_pass=False,
                has_conflict=1,  # type: ignore[arg-type]
            )

    def test_base_confidence_bool(self) -> None:
        with pytest.raises(TypeError, match="base_confidence must be a number"):
            assign_confidence(
                candidate_count=0,
                evidence_count=0,
                capability_ids=(),
                has_validation_pass=False,
                has_conflict=False,
                base_confidence=True,  # type: ignore[arg-type]
            )

    def test_base_confidence_string(self) -> None:
        with pytest.raises(TypeError, match="base_confidence must be a number"):
            assign_confidence(
                candidate_count=0,
                evidence_count=0,
                capability_ids=(),
                has_validation_pass=False,
                has_conflict=False,
                base_confidence="0.5",  # type: ignore[arg-type]
            )

    def test_capability_ids_non_iterable(self) -> None:
        with pytest.raises(TypeError, match="capability_ids must be iterable"):
            assign_confidence(
                candidate_count=0,
                evidence_count=0,
                capability_ids=None,  # type: ignore[arg-type]
                has_validation_pass=False,
                has_conflict=False,
            )

    def test_capability_ids_entry_non_string(self) -> None:
        with pytest.raises(TypeError, match="capability_ids entries must be str"):
            assign_confidence(
                candidate_count=0,
                evidence_count=0,
                capability_ids=[42],  # type: ignore[list-item]
                has_validation_pass=False,
                has_conflict=False,
            )

    def test_capability_ids_entry_none(self) -> None:
        with pytest.raises(TypeError, match="capability_ids entries must be str"):
            assign_confidence(
                candidate_count=0,
                evidence_count=0,
                capability_ids=[None],  # type: ignore[list-item]
                has_validation_pass=False,
                has_conflict=False,
            )


# ============================================================================
# assign_confidence — value validation
# ============================================================================


class TestAssignConfidenceValueValidation:
    """assign_confidence rejects negative counts."""

    def test_negative_candidate_count(self) -> None:
        with pytest.raises(ValueError, match="candidate_count must be non-negative"):
            assign_confidence(
                candidate_count=-1,
                evidence_count=0,
                capability_ids=(),
                has_validation_pass=False,
                has_conflict=False,
            )

    def test_negative_evidence_count(self) -> None:
        with pytest.raises(ValueError, match="evidence_count must be non-negative"):
            assign_confidence(
                candidate_count=0,
                evidence_count=-5,
                capability_ids=(),
                has_validation_pass=False,
                has_conflict=False,
            )


# ============================================================================
# assign_confidence — rubric math
# ============================================================================


class TestAssignConfidenceRubric:
    """Verify the deterministic scoring rubric with various inputs."""

    # --- Base only (no bonuses, no penalties) ---

    def test_base_only_default(self) -> None:
        """With no candidates, no evidence, no validation, no conflict, base=0.50."""
        result = assign_confidence(
            candidate_count=0,
            evidence_count=0,
            capability_ids=(),
            has_validation_pass=False,
            has_conflict=False,
        )
        assert result == 0.50

    def test_base_only_custom(self) -> None:
        """With a custom base_confidence."""
        result = assign_confidence(
            candidate_count=0,
            evidence_count=0,
            capability_ids=(),
            has_validation_pass=False,
            has_conflict=False,
            base_confidence=0.30,
        )
        assert result == 0.30

    def test_base_only_custom_int(self) -> None:
        """An int base_confidence is accepted."""
        result = assign_confidence(
            candidate_count=0,
            evidence_count=0,
            capability_ids=(),
            has_validation_pass=False,
            has_conflict=False,
            base_confidence=1,
        )
        assert result == 1.0

    # --- Candidate bonus ---

    @pytest.mark.parametrize(
        "candidate_count, expected_bonus",
        [
            (0, 0.0),  # 0 * 0.10
            (1, 0.10),  # 1 * 0.10
            (2, 0.20),  # 2 * 0.10
            (3, 0.30),  # 3 * 0.10 (cap not reached yet)
            (4, 0.30),  # cap at 3 → 0.30
            (10, 0.30),  # cap at 3 → 0.30
        ],
    )
    def test_candidate_bonus(self, candidate_count: int, expected_bonus: float) -> None:
        result = assign_confidence(
            candidate_count=candidate_count,
            evidence_count=0,
            capability_ids=(),
            has_validation_pass=False,
            has_conflict=False,
            base_confidence=0.0,
        )
        assert result == pytest.approx(expected_bonus)

    # --- Evidence bonus ---

    @pytest.mark.parametrize(
        "evidence_count, expected_bonus",
        [
            (0, 0.0),
            (1, 0.05),
            (2, 0.10),
            (3, 0.15),
            (4, 0.20),
            (5, 0.25),
            (6, 0.25),  # cap at 5
            (100, 0.25),  # cap at 5
        ],
    )
    def test_evidence_bonus(self, evidence_count: int, expected_bonus: float) -> None:
        result = assign_confidence(
            candidate_count=0,
            evidence_count=evidence_count,
            capability_ids=(),
            has_validation_pass=False,
            has_conflict=False,
            base_confidence=0.0,
        )
        assert result == pytest.approx(expected_bonus)

    # --- Validation pass bonus ---

    @pytest.mark.parametrize(
        "has_validation_pass, expected_bonus",
        [
            (False, 0.0),
            (True, 0.10),
        ],
    )
    def test_validation_bonus(self, has_validation_pass: bool, expected_bonus: float) -> None:
        result = assign_confidence(
            candidate_count=0,
            evidence_count=0,
            capability_ids=(),
            has_validation_pass=has_validation_pass,
            has_conflict=False,
            base_confidence=0.0,
        )
        assert result == pytest.approx(expected_bonus)

    # --- Conflict penalty ---

    @pytest.mark.parametrize(
        "has_conflict, base, expected",
        [
            (False, 0.50, 0.50),
            (True, 0.50, 0.35),  # 0.50 - 0.15 = 0.35
            (False, 0.0, 0.0),
            (True, 0.20, 0.05),  # 0.20 - 0.15 = 0.05
        ],
    )
    def test_conflict_penalty(self, has_conflict: bool, base: float, expected: float) -> None:
        result = assign_confidence(
            candidate_count=0,
            evidence_count=0,
            capability_ids=(),
            has_validation_pass=False,
            has_conflict=has_conflict,
            base_confidence=base,
        )
        assert result == pytest.approx(expected)

    # --- Capability source bonus ---

    @pytest.mark.parametrize(
        "capability_ids, expected_bonus",
        [
            ((), 0.0),
            (("regex_extraction",), 0.05),
            (("regex_extraction", "validation"), 0.10),
            (("regex_extraction", "validation", "lookup"), 0.15),
            (("regex_extraction", "validation", "lookup", "inference"), 0.15),  # cap at 3
            (("a", "a", "a"), 0.05),  # duplicates → 1 unique
        ],
    )
    def test_capability_source_bonus(
        self, capability_ids: tuple[str, ...], expected_bonus: float
    ) -> None:
        result = assign_confidence(
            candidate_count=0,
            evidence_count=0,
            capability_ids=capability_ids,
            has_validation_pass=False,
            has_conflict=False,
            base_confidence=0.0,
        )
        assert result == pytest.approx(expected_bonus)


# ============================================================================
# assign_confidence — combined scenarios
# ============================================================================


class TestAssignConfidenceCombined:
    """Integration-style tests that combine multiple rubric components."""

    def test_typical_good_case(self) -> None:
        """2 candidates, 3 evidence refs, validation passed, no conflict, 2 capabilities."""
        result = assign_confidence(
            candidate_count=2,
            evidence_count=3,
            capability_ids=("regex_extraction", "validation"),
            has_validation_pass=True,
            has_conflict=False,
            base_confidence=0.50,
        )
        # 0.50 + 0.20 + 0.15 + 0.10 + 0.10 = 1.0
        assert result == pytest.approx(1.0)

    def test_typical_good_case_no_conflict(self) -> None:
        """Same as above but without validation pass."""
        result = assign_confidence(
            candidate_count=2,
            evidence_count=3,
            capability_ids=("regex_extraction", "validation"),
            has_validation_pass=False,
            has_conflict=False,
            base_confidence=0.50,
        )
        # 0.50 + 0.20 + 0.15 + 0.0 + 0.10 = 0.95
        assert result == pytest.approx(0.95)

    def test_conflict_penalty_applied(self) -> None:
        """Conflict subtracts 0.15 from the running total."""
        result = assign_confidence(
            candidate_count=2,
            evidence_count=3,
            capability_ids=("regex_extraction",),
            has_validation_pass=True,
            has_conflict=True,
            base_confidence=0.50,
        )
        # 0.50 + 0.20 + 0.15 + 0.10 - 0.15 + 0.05 = 0.85
        assert result == pytest.approx(0.85)

    def test_everything_maximized(self) -> None:
        """All bonuses maxed, no conflict."""
        result = assign_confidence(
            candidate_count=5,
            evidence_count=10,
            capability_ids=("a", "b", "c", "d"),
            has_validation_pass=True,
            has_conflict=False,
            base_confidence=0.50,
        )
        # 0.50 + 0.30 + 0.25 + 0.10 + 0.0 + 0.15 = 1.30 → clamped to 1.0
        assert result == pytest.approx(1.0)

    def test_everything_minimal(self) -> None:
        """All penalties, nothing positive."""
        result = assign_confidence(
            candidate_count=0,
            evidence_count=0,
            capability_ids=(),
            has_validation_pass=False,
            has_conflict=True,
            base_confidence=0.50,
        )
        # 0.50 + 0.0 + 0.0 + 0.0 - 0.15 + 0.0 = 0.35
        assert result == pytest.approx(0.35)

    def test_conflict_with_low_base_drives_to_zero(self) -> None:
        """Clamp at 0.0 when penalties exceed positive contributions."""
        result = assign_confidence(
            candidate_count=0,
            evidence_count=0,
            capability_ids=(),
            has_validation_pass=False,
            has_conflict=True,
            base_confidence=0.10,
        )
        # 0.10 - 0.15 = -0.05 → clamped to 0.0
        assert result == pytest.approx(0.0)

    def test_clamp_at_one(self) -> None:
        """Clamp at 1.0 when bonuses push above."""
        result = assign_confidence(
            candidate_count=10,
            evidence_count=10,
            capability_ids=("a", "b", "c", "d"),
            has_validation_pass=True,
            has_conflict=False,
            base_confidence=0.90,
        )
        # 0.90 + 0.30 + 0.25 + 0.10 + 0.15 = 1.70 → clamped to 1.0
        assert result == pytest.approx(1.0)

    def test_empty_capability_ids_iterable(self) -> None:
        """A generator is accepted as capability_ids."""
        result = assign_confidence(
            candidate_count=1,
            evidence_count=1,
            capability_ids=(x for x in []),
            has_validation_pass=False,
            has_conflict=False,
            base_confidence=0.0,
        )
        # 0.0 + 0.10 + 0.05 + 0.0 + 0.0 + 0.0 = 0.15
        assert result == pytest.approx(0.15)

    def test_capability_ids_with_duplicates(self) -> None:
        """Duplicate capability IDs count as one unique source."""
        result = assign_confidence(
            candidate_count=0,
            evidence_count=0,
            capability_ids=("same", "same", "same"),
            has_validation_pass=False,
            has_conflict=False,
            base_confidence=0.0,
        )
        # 0.0 + 0.0 + 0.0 + 0.0 + 0.0 + 0.05 = 0.05
        assert result == pytest.approx(0.05)
