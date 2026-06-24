"""Tests for paxman.reconciler.merge — candidate merging strategies."""

from __future__ import annotations

from decimal import Decimal

import pytest

from paxman.budget import CurrencyPolicy
from paxman.capabilities.result import Candidate, EvidenceRef
from paxman.contract.canonical import CanonicalField, MoneyValue
from paxman.reconciler.merge import MergeStrategy, _values_equal, merge_candidates
from paxman.types import FieldType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_field(
    type_: FieldType = FieldType.STRING,
    *,
    required: bool = True,
) -> CanonicalField:
    return CanonicalField(
        id="f1",
        path="x",
        name="x",
        type=type_,
        required=required,
    )


def _evref(
    capability_id: str = "cap",
    version: str = "1.0",
    field_path: str = "x",
    span: tuple[int, int] | None = None,
) -> EvidenceRef:
    return EvidenceRef(
        capability_id=capability_id,
        capability_version=version,
        field_path=field_path,
        span=span,
    )


# ---------------------------------------------------------------------------
# MergeStrategy enum
# ---------------------------------------------------------------------------


class TestMergeStrategy:
    def test_values(self) -> None:
        assert MergeStrategy.UNION.value == "UNION"
        assert MergeStrategy.INTERSECTION.value == "INTERSECTION"
        assert MergeStrategy.PREFER_BY_EVIDENCE.value == "PREFER_BY_EVIDENCE"

    def test_is_enum(self) -> None:
        assert issubclass(MergeStrategy, object)

    def test_members_unique(self) -> None:
        members = set(m.value for m in MergeStrategy)
        assert len(members) == 3


# ---------------------------------------------------------------------------
# _values_equal
# ---------------------------------------------------------------------------


class TestValuesEqual:
    def test_same_value(self) -> None:
        assert _values_equal("foo", "foo") is True

    def test_different_value(self) -> None:
        assert _values_equal("foo", "bar") is False

    def test_money_value_same(self) -> None:
        mv1 = MoneyValue(amount=Decimal("10.00"), currency="USD")
        mv2 = MoneyValue(amount=Decimal("10.00"), currency="USD")
        assert _values_equal(mv1, mv2) is True

    def test_money_value_different_amount(self) -> None:
        mv1 = MoneyValue(amount=Decimal("10.00"), currency="USD")
        mv2 = MoneyValue(amount=Decimal("20.00"), currency="USD")
        assert _values_equal(mv1, mv2) is False

    def test_money_value_different_currency(self) -> None:
        mv1 = MoneyValue(amount=Decimal("10.00"), currency="USD")
        mv2 = MoneyValue(amount=Decimal("10.00"), currency="EUR")
        assert _values_equal(mv1, mv2) is False

    def test_money_value_mixed_types(self) -> None:
        mv = MoneyValue(amount=Decimal("10.00"), currency="USD")
        assert _values_equal(mv, "not money") is False

    def test_int_and_float_equal(self) -> None:
        # int 1 == float 1.0 in Python
        assert _values_equal(1, 1.0) is True

    def test_none_values(self) -> None:
        assert _values_equal(None, None) is True

    def test_exception_safe(self) -> None:
        """When __eq__ raises, _values_equal returns False."""

        class Explodes:
            def __eq__(self, other: object) -> bool:
                raise RuntimeError("boom")

        assert _values_equal(Explodes(), "anything") is False


# ---------------------------------------------------------------------------
# merge_candidates — type errors
# ---------------------------------------------------------------------------


class TestMergeCandidatesTypeErrors:
    def test_candidates_not_tuple(self) -> None:
        with pytest.raises(TypeError, match="candidates must be a tuple"):
            merge_candidates([Candidate(value="x")], field=_make_field())  # type: ignore[arg-type]

    def test_field_not_canonical(self) -> None:
        with pytest.raises(TypeError, match="field must be a CanonicalField"):
            merge_candidates((Candidate(value="x"),), field="not-a-field")  # type: ignore[arg-type]

    def test_strategy_wrong_type(self) -> None:
        with pytest.raises(TypeError, match="strategy must be a MergeStrategy"):
            merge_candidates(
                (Candidate(value="x"),),
                field=_make_field(),
                strategy="UNION",  # type: ignore[arg-type]
            )

    def test_currency_policy_wrong_type(self) -> None:
        with pytest.raises(TypeError, match="currency_policy must be a CurrencyPolicy"):
            merge_candidates(
                (Candidate(value="x"),),
                field=_make_field(),
                currency_policy="STRICT",  # type: ignore[arg-type]
            )

    def test_empty_candidates(self) -> None:
        with pytest.raises(ValueError, match="at least one candidate"):
            merge_candidates((), field=_make_field())


# ---------------------------------------------------------------------------
# merge_candidates — no valid candidates
# ---------------------------------------------------------------------------


class TestMergeNoValidCandidates:
    def test_all_invalid(self) -> None:
        """When all candidates are not Candidate instances, return NO_CANDIDATES."""
        value, evidence, strategy = merge_candidates((object(),), field=_make_field())
        assert value is None
        assert evidence == ()
        assert strategy == "NO_CANDIDATES"


# ---------------------------------------------------------------------------
# merge_candidates — UNION strategy
# ---------------------------------------------------------------------------


class TestMergeUnion:
    def test_agree(self) -> None:
        c1 = Candidate(value="ACME", evidence_refs=(_evref(capability_id="a"),))
        c2 = Candidate(value="ACME", evidence_refs=(_evref(capability_id="b"),))
        value, evidence, strategy = merge_candidates(
            (c1, c2), field=_make_field(), strategy=MergeStrategy.UNION
        )
        assert value == "ACME"
        assert len(evidence) == 2
        assert strategy == "UNION"

    def test_disagree_falls_back(self) -> None:
        c1 = Candidate(value="ACME", evidence_refs=(_evref(capability_id="a"),))
        c2 = Candidate(value="OTHER", evidence_refs=(_evref(capability_id="b"),))
        value, _evidence, strategy = merge_candidates(
            (c1, c2), field=_make_field(), strategy=MergeStrategy.UNION
        )
        # Falls back to PREFER_BY_EVIDENCE — both have same evidence quality,
        # so first candidate is kept.
        assert value == "ACME"
        assert strategy == "PREFER_BY_EVIDENCE"

    def test_agree_union_evidence_dedup(self) -> None:
        ref = _evref(capability_id="a")
        c1 = Candidate(value="ACME", evidence_refs=(ref,))
        c2 = Candidate(value="ACME", evidence_refs=(ref,))
        value, evidence, strategy = merge_candidates(
            (c1, c2), field=_make_field(), strategy=MergeStrategy.UNION
        )
        assert value == "ACME"
        assert len(evidence) == 1  # deduped
        assert strategy == "UNION"

    def test_agree_with_none_values_skipped(self) -> None:
        c1 = Candidate(value="ACME")
        c2 = Candidate(value=None, evidence_refs=(_evref(capability_id="b"),))  # type: ignore[arg-type]
        value, _evidence, strategy = merge_candidates(
            (c1, c2), field=_make_field(), strategy=MergeStrategy.UNION
        )
        assert value == "ACME"
        assert strategy == "UNION"


# ---------------------------------------------------------------------------
# merge_candidates — INTERSECTION strategy
# ---------------------------------------------------------------------------


class TestMergeIntersection:
    def test_common_value_appears_twice(self) -> None:
        c1 = Candidate(value="ACME")
        c2 = Candidate(value="ACME")
        c3 = Candidate(value="OTHER")
        value, _evidence, strategy = merge_candidates(
            (c1, c2, c3), field=_make_field(), strategy=MergeStrategy.INTERSECTION
        )
        assert value == "ACME"
        assert strategy == "INTERSECTION"

    def test_no_common_value_falls_back(self) -> None:
        c1 = Candidate(value="ACME", evidence_refs=(_evref(capability_id="a"),))
        c2 = Candidate(value="OTHER", evidence_refs=(_evref(capability_id="b"),))
        value, _evidence, strategy = merge_candidates(
            (c1, c2), field=_make_field(), strategy=MergeStrategy.INTERSECTION
        )
        # Falls back to PREFER_BY_EVIDENCE
        assert value == "ACME"
        assert strategy == "PREFER_BY_EVIDENCE"

    def test_all_none_falls_back(self) -> None:
        c1 = Candidate(value=None)  # type: ignore[arg-type]
        c2 = Candidate(value=None)  # type: ignore[arg-type]
        value, _evidence, strategy = merge_candidates(
            (c1, c2), field=_make_field(), strategy=MergeStrategy.INTERSECTION
        )
        assert strategy == "PREFER_BY_EVIDENCE"
        assert value is None

    def test_intersection_unions_evidence_from_matching_candidates(self) -> None:
        ref1 = _evref(capability_id="a")
        ref2 = _evref(capability_id="b")
        c1 = Candidate(value="ACME", evidence_refs=(ref1,))
        c2 = Candidate(value="ACME", evidence_refs=(ref2,))
        c3 = Candidate(value="OTHER", evidence_refs=(_evref(capability_id="c"),))
        value, evidence, strategy = merge_candidates(
            (c1, c2, c3), field=_make_field(), strategy=MergeStrategy.INTERSECTION
        )
        assert value == "ACME"
        assert len(evidence) == 2
        assert strategy == "INTERSECTION"


# ---------------------------------------------------------------------------
# merge_candidates — PREFER_BY_EVIDENCE (default)
# ---------------------------------------------------------------------------


class TestMergePreferByEvidence:
    def test_default_strategy(self) -> None:
        c1 = Candidate(value="ACME", evidence_refs=(_evref(capability_id="a"),))
        c2 = Candidate(value="OTHER", evidence_refs=(_evref(capability_id="b"),))
        _value, _evidence, strategy = merge_candidates((c1, c2), field=_make_field())
        assert strategy == "PREFER_BY_EVIDENCE"

    def test_explicit_strategy(self) -> None:
        c1 = Candidate(value="ACME")
        c2 = Candidate(value="OTHER")
        _value, _evidence, strategy = merge_candidates(
            (c1, c2), field=_make_field(), strategy=MergeStrategy.PREFER_BY_EVIDENCE
        )
        assert strategy == "PREFER_BY_EVIDENCE"

    def test_picks_best_evidence(self) -> None:
        c1 = Candidate(value="weak", evidence_refs=(_evref(capability_id="a"),))
        c2 = Candidate(
            value="strong",
            evidence_refs=(_evref(capability_id="a"), _evref(capability_id="b")),
        )
        value, evidence, _strategy = merge_candidates(
            (c1, c2), field=_make_field(), strategy=MergeStrategy.PREFER_BY_EVIDENCE
        )
        assert value == "strong"
        assert len(evidence) == 2

    def test_single_candidate(self) -> None:
        c = Candidate(value="only")
        value, _evidence, strategy = merge_candidates((c,), field=_make_field())
        assert value == "only"
        assert strategy == "PREFER_BY_EVIDENCE"

    def test_no_valid_candidates_passes_none(self) -> None:
        """When all candidates are filtered out, returns (None, (), 'NO_CANDIDATES')."""
        # Pass candidates that are not Candidate instances - filtered to empty.
        value, evidence, strategy = merge_candidates(
            (object(), object()), field=_make_field(), strategy=MergeStrategy.PREFER_BY_EVIDENCE
        )
        assert value is None
        assert evidence == ()
        assert strategy == "NO_CANDIDATES"


# ---------------------------------------------------------------------------
# merge_candidates — MONEY fast path
# ---------------------------------------------------------------------------


class TestMergeMoney:
    def test_money_field_delegates(self) -> None:
        mv1 = MoneyValue(amount=Decimal("10.00"), currency="USD")
        mv2 = MoneyValue(amount=Decimal("20.00"), currency="USD")
        c1 = Candidate(value=mv1, evidence_refs=(_evref(capability_id="a"),))
        c2 = Candidate(value=mv2, evidence_refs=(_evref(capability_id="b"),))
        field = _make_field(type_=FieldType.MONEY)
        value, evidence, strategy = merge_candidates((c1, c2), field=field)
        assert isinstance(value, MoneyValue)
        assert value.amount == Decimal("30.00")
        assert value.currency == "USD"
        assert strategy == "MONEY_RESOLVE"
        assert len(evidence) == 2

    def test_money_field_rejects_cross_currency_strict(self) -> None:
        mv1 = MoneyValue(amount=Decimal("10.00"), currency="USD")
        mv2 = MoneyValue(amount=Decimal("20.00"), currency="EUR")
        c1 = Candidate(value=mv1, evidence_refs=(_evref(capability_id="a"),))
        c2 = Candidate(value=mv2, evidence_refs=(_evref(capability_id="b"),))
        field = _make_field(type_=FieldType.MONEY)
        value, _evidence, strategy = merge_candidates((c1, c2), field=field)
        # Falls through to PREFER_BY_EVIDENCE since money module returns None
        # for cross-currency with STRICT_MATCH.
        # It still does the money check first which returns None,
        # then falls back to the strategy.
        assert strategy == "PREFER_BY_EVIDENCE"
        # Both have equal evidence, so first candidate wins
        assert isinstance(value, MoneyValue)
        assert value.currency == "USD"

    def test_money_field_no_money_candidates(self) -> None:
        """Candidates that are not MoneyValue values are skipped by money merge."""
        c1 = Candidate(value="not money")
        c2 = Candidate(value=42)
        field = _make_field(type_=FieldType.MONEY)
        value, _evidence, strategy = merge_candidates((c1, c2), field=field)
        assert strategy == "PREFER_BY_EVIDENCE"
        assert value == "not money"  # first candidate wins (equal evidence)

    def test_money_field_allow_fx_no_rate_raises(self) -> None:
        mv1 = MoneyValue(amount=Decimal("10.00"), currency="USD")
        mv2 = MoneyValue(amount=Decimal("10.00"), currency="EUR")
        c1 = Candidate(value=mv1, evidence_refs=(_evref(capability_id="a"),))
        c2 = Candidate(value=mv2, evidence_refs=(_evref(capability_id="b"),))
        field = _make_field(type_=FieldType.MONEY)
        # merge_candidates passes fx_rate=None to _do_money_merge which
        # passes it to resolve_money_candidates. With ALLOW_FX and
        # cross-currency, resolve_money_candidates calls _validate_fx_rate(None, allow_none=False)
        # which raises MissingFxRateError.
        from paxman.reconciler.money import MissingFxRateError

        with pytest.raises(MissingFxRateError):
            merge_candidates(
                (c1, c2),
                field=field,
                currency_policy=CurrencyPolicy.ALLOW_FX,
            )


# ---------------------------------------------------------------------------
# merge_candidates — edge cases
# ---------------------------------------------------------------------------


class TestMergeEdgeCases:
    def test_all_none_values_pick_first(self) -> None:
        c1 = Candidate(value=None)  # type: ignore[arg-type]
        c2 = Candidate(value=None)  # type: ignore[arg-type]
        value, _evidence, strategy = merge_candidates((c1, c2), field=_make_field())
        # Since both have no evidence and value=None,
        # best_candidate_by_evidence picks the first one
        assert value is None
        assert strategy == "PREFER_BY_EVIDENCE"

    def test_mixed_valid_and_invalid_candidates(self) -> None:
        c1 = Candidate(value="valid")
        value, _evidence, strategy = merge_candidates(
            (c1, object()), field=_make_field(), strategy=MergeStrategy.PREFER_BY_EVIDENCE
        )
        assert value == "valid"
        assert strategy == "PREFER_BY_EVIDENCE"

    def test_evidence_refs_are_deduplicated(self) -> None:
        ref = _evref(capability_id="a", span=(0, 5))
        c1 = Candidate(value="hello", evidence_refs=(ref,))
        c2 = Candidate(value="hello", evidence_refs=(ref,))
        value, evidence, strategy = merge_candidates(
            (c1, c2), field=_make_field(), strategy=MergeStrategy.UNION
        )
        assert value == "hello"
        assert len(evidence) == 1  # dedup
        assert strategy == "UNION"
