"""Unit tests for :mod:`paxman.reconciler.conflict`.

Tests cover:
- :class:`ConflictInfo` validation (field_path, candidate_values,
  conflict_type, candidate_count).
- :func:`detect_conflicts`: type errors, no-conflict scenarios (single
  candidate, all agree, only None values), value-mismatch detection,
  currency-mismatch detection for MONEY fields, and edge cases with
  bare currency-code strings.
"""

from __future__ import annotations

import decimal

import pytest

from paxman.capabilities.result import Candidate
from paxman.contract.canonical import CanonicalField, MoneyValue
from paxman.reconciler.conflict import (
    CONFLICT_TYPE_CURRENCY_MISMATCH,
    CONFLICT_TYPE_VALUE_MISMATCH,
    ConflictInfo,
    detect_conflicts,
)
from paxman.types import FieldType

pytestmark = pytest.mark.unit


# ============================================================================
# Helpers
# ============================================================================


def _field(
    path: str = "total_amount",
    field_type: FieldType = FieldType.STRING,
) -> CanonicalField:
    """Build a minimal CanonicalField for testing."""
    return CanonicalField(
        id="f1",
        path=path,
        name=path.split(".")[-1],
        type=field_type,
        required=True,
    )


def _candidate(value: object) -> Candidate:
    """Build a minimal Candidate with the given value."""
    return Candidate(value=value)


# ============================================================================
# ConflictInfo — validation
# ============================================================================


class TestConflictInfoValidation:
    """Validate ConflictInfo __attrs_post_init__ invariants."""

    # --- field_path ---

    @pytest.mark.parametrize(
        "bad_value",
        [""],
    )
    def test_empty_field_path_raises(self, bad_value: str) -> None:
        with pytest.raises(ValueError, match="field_path must be a non-empty string"):
            ConflictInfo(
                field_path=bad_value,
                candidate_values=("a", "b"),
                conflict_type=CONFLICT_TYPE_VALUE_MISMATCH,
                candidate_count=2,
            )

    @pytest.mark.parametrize(
        "bad_value",
        [None, 0, True],
    )
    def test_non_string_field_path_raises(self, bad_value: object) -> None:
        with pytest.raises(ValueError, match="field_path must be a non-empty string"):
            ConflictInfo(
                field_path=bad_value,  # type: ignore[arg-type]
                candidate_values=("a", "b"),
                conflict_type=CONFLICT_TYPE_VALUE_MISMATCH,
                candidate_count=2,
            )

    # --- candidate_values ---

    def test_candidate_values_list_raises(self) -> None:
        with pytest.raises(TypeError, match="candidate_values must be a tuple"):
            ConflictInfo(
                field_path="x",
                candidate_values=["a", "b"],  # type: ignore[arg-type]
                conflict_type=CONFLICT_TYPE_VALUE_MISMATCH,
                candidate_count=2,
            )

    def test_candidate_values_none_raises(self) -> None:
        with pytest.raises(TypeError, match="candidate_values must be a tuple"):
            ConflictInfo(
                field_path="x",
                candidate_values=None,  # type: ignore[arg-type]
                conflict_type=CONFLICT_TYPE_VALUE_MISMATCH,
                candidate_count=2,
            )

    # --- conflict_type ---

    def test_invalid_conflict_type_raises(self) -> None:
        with pytest.raises(
            ValueError,
            match="conflict_type must be 'value_mismatch' or 'currency_mismatch'",
        ):
            ConflictInfo(
                field_path="x",
                candidate_values=("a", "b"),
                conflict_type="unknown_type",
                candidate_count=2,
            )

    def test_empty_conflict_type_raises(self) -> None:
        with pytest.raises(
            ValueError,
            match="conflict_type must be 'value_mismatch' or 'currency_mismatch'",
        ):
            ConflictInfo(
                field_path="x",
                candidate_values=("a", "b"),
                conflict_type="",
                candidate_count=2,
            )

    # --- candidate_count ---

    def test_candidate_count_bool_raises(self) -> None:
        with pytest.raises(TypeError, match="candidate_count must be an int"):
            ConflictInfo(
                field_path="x",
                candidate_values=("a", "b"),
                conflict_type=CONFLICT_TYPE_VALUE_MISMATCH,
                candidate_count=True,  # type: ignore[arg-type]
            )

    def test_candidate_count_string_raises(self) -> None:
        with pytest.raises(TypeError, match="candidate_count must be an int"):
            ConflictInfo(
                field_path="x",
                candidate_values=("a", "b"),
                conflict_type=CONFLICT_TYPE_VALUE_MISMATCH,
                candidate_count="2",  # type: ignore[arg-type]
            )

    def test_negative_candidate_count_raises(self) -> None:
        with pytest.raises(ValueError, match="candidate_count must be non-negative"):
            ConflictInfo(
                field_path="x",
                candidate_values=("a", "b"),
                conflict_type=CONFLICT_TYPE_VALUE_MISMATCH,
                candidate_count=-1,
            )

    # --- Valid construction ---

    def test_valid_value_mismatch(self) -> None:
        ci = ConflictInfo(
            field_path="supplier_name",
            candidate_values=("ACME", "Beta"),
            conflict_type=CONFLICT_TYPE_VALUE_MISMATCH,
            candidate_count=2,
        )
        assert ci.field_path == "supplier_name"
        assert ci.candidate_values == ("ACME", "Beta")
        assert ci.conflict_type == CONFLICT_TYPE_VALUE_MISMATCH
        assert ci.candidate_count == 2

    def test_valid_currency_mismatch(self) -> None:
        ci = ConflictInfo(
            field_path="total_amount",
            candidate_values=("USD", "EUR"),
            conflict_type=CONFLICT_TYPE_CURRENCY_MISMATCH,
            candidate_count=3,
        )
        assert ci.candidate_values == ("USD", "EUR")
        assert ci.conflict_type == CONFLICT_TYPE_CURRENCY_MISMATCH
        assert ci.candidate_count == 3

    def test_defaults(self) -> None:
        """Minimal ConflictInfo with only field_path uses defaults."""
        ci = ConflictInfo(field_path="x")
        assert ci.candidate_values == ()
        assert ci.conflict_type == CONFLICT_TYPE_VALUE_MISMATCH
        assert ci.candidate_count == 0

    def test_zero_candidate_count_valid(self) -> None:
        """candidate_count of 0 is valid (edge case)."""
        ci = ConflictInfo(
            field_path="x",
            candidate_values=(),
            conflict_type=CONFLICT_TYPE_VALUE_MISMATCH,
            candidate_count=0,
        )
        assert ci.candidate_count == 0


# ============================================================================
# detect_conflicts — type validation
# ============================================================================


class TestDetectConflictsTypeValidation:
    """Type errors for invalid inputs."""

    def test_candidates_not_a_tuple_raises(self) -> None:
        with pytest.raises(TypeError, match="candidates must be a tuple"):
            detect_conflicts(
                candidates=[_candidate("a"), _candidate("b")],  # type: ignore[arg-type]
                field=_field(),
            )

    def test_field_not_canonical_field_raises(self) -> None:
        with pytest.raises(TypeError, match="field must be a CanonicalField"):
            detect_conflicts(
                candidates=(_candidate("a"),),
                field="not_a_field",  # type: ignore[arg-type]
            )


# ============================================================================
# detect_conflicts — no conflict scenarios
# ============================================================================


class TestDetectConflictsNoConflict:
    """Cases where detect_conflicts returns None."""

    def test_single_candidate(self) -> None:
        """A single candidate never creates a conflict."""
        result = detect_conflicts(
            candidates=(_candidate("ACME Corp"),),
            field=_field(),
        )
        assert result is None

    def test_all_values_agree(self) -> None:
        """Two candidates with the same value → no conflict."""
        result = detect_conflicts(
            candidates=(_candidate("ACME Corp"), _candidate("ACME Corp")),
            field=_field(),
        )
        assert result is None

    def test_multiple_candidates_all_same(self) -> None:
        """Three candidates all with the same value → no conflict."""
        result = detect_conflicts(
            candidates=(
                _candidate("ACME Corp"),
                _candidate("ACME Corp"),
                _candidate("ACME Corp"),
            ),
            field=_field(),
        )
        assert result is None

    def test_all_none_values(self) -> None:
        """All candidates have None values → no conflict (all filtered out)."""
        result = detect_conflicts(
            candidates=(_candidate(None), _candidate(None)),
            field=_field(),
        )
        assert result is None

    def test_one_none_one_value(self) -> None:
        """Only one concrete value → no conflict (need >= 2 non-None)."""
        result = detect_conflicts(
            candidates=(_candidate(None), _candidate("ACME Corp")),
            field=_field(),
        )
        assert result is None

    def test_empty_candidates(self) -> None:
        """Empty tuple → no conflict."""
        result = detect_conflicts(
            candidates=(),
            field=_field(),
        )
        assert result is None

    def test_money_same_currency_different_amount(self) -> None:
        """MONEY candidates with same currency but different amounts → no conflict.

        Amount disagreement is handled by the merge strategy, not conflict detection.
        """
        mv1 = MoneyValue(amount=decimal.Decimal("100.00"), currency="USD")
        mv2 = MoneyValue(amount=decimal.Decimal("200.00"), currency="USD")
        result = detect_conflicts(
            candidates=(_candidate(mv1), _candidate(mv2)),
            field=_field(field_type=FieldType.MONEY),
        )
        assert result is None

    def test_money_same_currency_same_amount(self) -> None:
        """MONEY candidates with same currency and amount → no conflict."""
        mv1 = MoneyValue(amount=decimal.Decimal("100.00"), currency="USD")
        mv2 = MoneyValue(amount=decimal.Decimal("100.00"), currency="USD")
        result = detect_conflicts(
            candidates=(_candidate(mv1), _candidate(mv2)),
            field=_field(field_type=FieldType.MONEY),
        )
        assert result is None

    def test_money_single_candidate(self) -> None:
        """Single MONEY candidate → no conflict."""
        mv = MoneyValue(amount=decimal.Decimal("100.00"), currency="USD")
        result = detect_conflicts(
            candidates=(_candidate(mv),),
            field=_field(field_type=FieldType.MONEY),
        )
        assert result is None


# ============================================================================
# detect_conflicts — value mismatch
# ============================================================================


class TestDetectConflictsValueMismatch:
    """Non-MONEY value-mismatch conflicts."""

    def test_two_different_string_values(self) -> None:
        result = detect_conflicts(
            candidates=(_candidate("ACME Corp"), _candidate("Beta Inc")),
            field=_field(),
        )
        assert result is not None
        assert result.conflict_type == CONFLICT_TYPE_VALUE_MISMATCH
        assert result.field_path == "total_amount"
        assert len(result.candidate_values) == 2
        assert result.candidate_count == 2

    def test_three_values_two_distinct(self) -> None:
        """3 candidates, 2 distinct values → conflict with 2 distinct values."""
        result = detect_conflicts(
            candidates=(
                _candidate("ACME Corp"),
                _candidate("ACME Corp"),
                _candidate("Beta Inc"),
            ),
            field=_field(),
        )
        assert result is not None
        assert result.conflict_type == CONFLICT_TYPE_VALUE_MISMATCH
        assert len(result.candidate_values) == 2

    def test_three_values_all_distinct(self) -> None:
        """3 candidates, 3 distinct values → conflict."""
        result = detect_conflicts(
            candidates=(
                _candidate("Alpha"),
                _candidate("Beta"),
                _candidate("Gamma"),
            ),
            field=_field(),
        )
        assert result is not None
        assert len(result.candidate_values) == 3

    def test_integer_values_mismatch(self) -> None:
        result = detect_conflicts(
            candidates=(_candidate(100), _candidate(200)),
            field=_field(),
        )
        assert result is not None
        assert result.conflict_type == CONFLICT_TYPE_VALUE_MISMATCH

    def test_boolean_values_mismatch(self) -> None:
        result = detect_conflicts(
            candidates=(_candidate(True), _candidate(False)),
            field=_field(),
        )
        assert result is not None
        assert result.conflict_type == CONFLICT_TYPE_VALUE_MISMATCH

    def test_none_and_different_values(self) -> None:
        """None values are filtered out, the remaining concrete values conflict."""
        result = detect_conflicts(
            candidates=(
                _candidate(None),
                _candidate("ACME Corp"),
                _candidate("Beta Inc"),
            ),
            field=_field(),
        )
        assert result is not None
        assert result.conflict_type == CONFLICT_TYPE_VALUE_MISMATCH
        assert result.candidate_count == 3  # total candidates, not filtered

    def test_candidate_count_reflects_total(self) -> None:
        """candidate_count in ConflictInfo is the total, not just concrete."""
        result = detect_conflicts(
            candidates=(
                _candidate("ACME"),
                _candidate("Beta"),
                _candidate(None),
                _candidate(None),
            ),
            field=_field(),
        )
        assert result is not None
        assert result.candidate_count == 4


# ============================================================================
# detect_conflicts — currency mismatch
# ============================================================================


class TestDetectConflictsCurrencyMismatch:
    """MONEY currency-mismatch conflicts."""

    def test_different_currencies(self) -> None:
        mv1 = MoneyValue(amount=decimal.Decimal("100.00"), currency="USD")
        mv2 = MoneyValue(amount=decimal.Decimal("200.00"), currency="EUR")
        result = detect_conflicts(
            candidates=(_candidate(mv1), _candidate(mv2)),
            field=_field(field_type=FieldType.MONEY),
        )
        assert result is not None
        assert result.conflict_type == CONFLICT_TYPE_CURRENCY_MISMATCH
        assert "USD" in result.candidate_values
        assert "EUR" in result.candidate_values
        assert result.candidate_count == 2

    def test_three_currencies(self) -> None:
        mv1 = MoneyValue(amount=decimal.Decimal("100"), currency="USD")
        mv2 = MoneyValue(amount=decimal.Decimal("200"), currency="EUR")
        mv3 = MoneyValue(amount=decimal.Decimal("300"), currency="JPY")
        result = detect_conflicts(
            candidates=(_candidate(mv1), _candidate(mv2), _candidate(mv3)),
            field=_field(field_type=FieldType.MONEY),
        )
        assert result is not None
        assert result.conflict_type == CONFLICT_TYPE_CURRENCY_MISMATCH
        assert len(result.candidate_values) == 3

    def test_mixed_with_none_values(self) -> None:
        """None values are ignored; only MoneyValue currencies are compared."""
        mv1 = MoneyValue(amount=decimal.Decimal("100"), currency="USD")
        mv2 = MoneyValue(amount=decimal.Decimal("200"), currency="EUR")
        result = detect_conflicts(
            candidates=(_candidate(None), _candidate(mv1), _candidate(mv2), _candidate(None)),
            field=_field(field_type=FieldType.MONEY),
        )
        assert result is not None
        assert result.conflict_type == CONFLICT_TYPE_CURRENCY_MISMATCH
        assert result.candidate_count == 4

    def test_bare_currency_code_strings(self) -> None:
        """Bare 3-letter currency code strings are detected as currency mismatch."""
        result = detect_conflicts(
            candidates=(_candidate("USD"), _candidate("EUR")),
            field=_field(field_type=FieldType.MONEY),
        )
        assert result is not None
        assert result.conflict_type == CONFLICT_TYPE_CURRENCY_MISMATCH
        assert "USD" in result.candidate_values
        assert "EUR" in result.candidate_values

    def test_bare_currency_code_with_money_value(self) -> None:
        """Mixed bare string and MoneyValue currencies are detected."""
        mv = MoneyValue(amount=decimal.Decimal("100"), currency="USD")
        result = detect_conflicts(
            candidates=(_candidate(mv), _candidate("EUR")),
            field=_field(field_type=FieldType.MONEY),
        )
        assert result is not None
        assert result.conflict_type == CONFLICT_TYPE_CURRENCY_MISMATCH

    def test_non_currency_string_not_tolerated(self) -> None:
        """A non-3-letter string is not added as a currency, so no conflict."""
        result = detect_conflicts(
            candidates=(_candidate("USD"), _candidate("not_a_currency")),
            field=_field(field_type=FieldType.MONEY),
        )
        # "not_a_currency" is not a 3-char string, so only "USD" is collected → no conflict
        assert result is None

    def test_money_field_without_money_values(self) -> None:
        """If no MoneyValue or currency-code string exists, no conflict."""
        result = detect_conflicts(
            candidates=(_candidate(100), _candidate(200)),
            field=_field(field_type=FieldType.MONEY),
        )
        assert result is None


# ============================================================================
# detect_conflicts — edge cases with _values_equal
# ============================================================================


class TestDetectConflictsEdgeCases:
    """Edge cases in the _values_equal comparison logic."""

    def test_money_value_equal_amount_and_currency(self) -> None:
        """Two MoneyValue objects with same amount and currency → no conflict."""
        mv1 = MoneyValue(amount=decimal.Decimal("100.00"), currency="USD")
        mv2 = MoneyValue(amount=decimal.Decimal("100.00"), currency="USD")
        result = detect_conflicts(
            candidates=(_candidate(mv1), _candidate(mv2)),
            field=_field(),
        )
        assert result is None

    def test_money_value_same_amount_different_currency(self) -> None:
        """Two MoneyValues with same amount but different currency → conflict for non-MONEY."""
        mv1 = MoneyValue(amount=decimal.Decimal("100.00"), currency="USD")
        mv2 = MoneyValue(amount=decimal.Decimal("100.00"), currency="EUR")
        result = detect_conflicts(
            candidates=(_candidate(mv1), _candidate(mv2)),
            field=_field(),  # STRING type → uses generic ==, MoneyValue __eq__
        )
        assert result is not None
        assert result.conflict_type == CONFLICT_TYPE_VALUE_MISMATCH

    def test_equal_floats(self) -> None:
        """Equal float values → no conflict."""
        result = detect_conflicts(
            candidates=(_candidate(1.0), _candidate(1.0)),
            field=_field(),
        )
        assert result is None

    def test_nan_values_compared(self) -> None:
        """NaN != NaN in Python, so two NaN values should be a conflict."""
        result = detect_conflicts(
            candidates=(_candidate(float("nan")), _candidate(float("nan"))),
            field=_field(),
        )
        # NaN != NaN, so they should be distinct → conflict
        assert result is not None
        assert result.conflict_type == CONFLICT_TYPE_VALUE_MISMATCH

    def test_none_in_money_values_not_filtered_incorrectly(self) -> None:
        """MONEY field with some None candidates doesn't affect non-None checks."""
        mv1 = MoneyValue(amount=decimal.Decimal("100"), currency="USD")
        mv2 = MoneyValue(amount=decimal.Decimal("200"), currency="EUR")
        result = detect_conflicts(
            candidates=(_candidate(None), _candidate(mv1), _candidate(mv2)),
            field=_field(field_type=FieldType.MONEY),
        )
        assert result is not None
        assert result.conflict_type == CONFLICT_TYPE_CURRENCY_MISMATCH
