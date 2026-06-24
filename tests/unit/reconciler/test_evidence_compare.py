"""Unit tests for :mod:`paxman.reconciler.evidence_compare`.

Tests cover:
- :func:`evidence_has_span`: type errors, True/False for various evidence sets.
- :func:`compare_evidence_quality`: all five ordering criteria (count,
  span, determinism, tier rank, lexicographic tiebreak), type errors,
  edge cases.
- :func:`best_candidate_by_evidence`: empty input, single candidate,
  ranking by evidence, tiebreak, type errors.
"""

from __future__ import annotations

import pytest

from paxman.capabilities.base import CapabilityContext
from paxman.capabilities.registry import register, reset
from paxman.capabilities.result import Candidate, CapabilityResult, EvidenceRef
from paxman.capabilities.spec import CapabilitySpec, CapabilityTier
from paxman.reconciler.evidence_compare import (
    best_candidate_by_evidence,
    compare_evidence_quality,
    evidence_has_span,
)

pytestmark = pytest.mark.unit


# ============================================================================
# Helpers
# ============================================================================


def _ref(
    capability_id: str = "regex_extraction",
    capability_version: str = "1.0",
    field_path: str = "x",
    span: tuple[int, int] | None = None,
) -> EvidenceRef:
    """Build a minimal EvidenceRef."""
    return EvidenceRef(
        capability_id=capability_id,
        capability_version=capability_version,
        field_path=field_path,
        span=span,
    )


def _candidate(value: object = "val", evidence_refs: tuple[EvidenceRef, ...] = ()) -> Candidate:
    """Build a minimal Candidate."""
    return Candidate(value=value, evidence_refs=evidence_refs)


class _StubCapability:
    """Minimal capability stub for registry tests."""

    def __init__(self, spec: CapabilitySpec) -> None:
        self._spec = spec

    @property
    def spec(self) -> CapabilitySpec:
        return self._spec

    def invoke(self, ctx: CapabilityContext) -> CapabilityResult:  # pragma: no cover
        return CapabilityResult()


# ---------------------------------------------------------------------------
# Registry fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    """Reset the global capability registry before and after each test."""
    reset()
    yield
    reset()


@pytest.fixture
def deterministic_cap() -> None:
    """Register a LOCAL_DETERMINISTIC (tier 1) capability."""
    register(
        _StubCapability(
            CapabilitySpec(
                id="regex_extraction",
                version="1.0",
                tier=CapabilityTier.LOCAL_DETERMINISTIC,
                deterministic=True,
            )
        )
    )


@pytest.fixture
def structured_lookup_cap() -> None:
    """Register a STRUCTURED_LOOKUP (tier 2) capability."""
    register(
        _StubCapability(
            CapabilitySpec(
                id="lookup",
                version="1.0",
                tier=CapabilityTier.STRUCTURED_LOOKUP,
                deterministic=True,
            )
        )
    )


@pytest.fixture
def local_inference_cap() -> None:
    """Register a LOCAL_INFERENCE (tier 4, non-deterministic) capability."""
    register(
        _StubCapability(
            CapabilitySpec(
                id="inference_local",
                version="1.0",
                tier=CapabilityTier.LOCAL_INFERENCE,
                deterministic=False,
            )
        )
    )


@pytest.fixture
def remote_inference_cap() -> None:
    """Register a REMOTE_INFERENCE (tier 5, non-deterministic) capability."""
    register(
        _StubCapability(
            CapabilitySpec(
                id="inference_remote",
                version="1.0",
                tier=CapabilityTier.REMOTE_INFERENCE,
                deterministic=False,
            )
        )
    )


# ============================================================================
# evidence_has_span
# ============================================================================


class TestEvidenceHasSpan:
    """Validate evidence_has_span behaviour."""

    def test_type_error_for_non_tuple(self) -> None:
        with pytest.raises(TypeError, match="refs must be a tuple"):
            evidence_has_span(None)  # type: ignore[arg-type]

    def test_type_error_for_list(self) -> None:
        with pytest.raises(TypeError, match="refs must be a tuple"):
            evidence_has_span([_ref()])  # type: ignore[arg-type]

    def test_empty_tuple_has_no_span(self) -> None:
        assert evidence_has_span(()) is False

    def test_no_refs_with_span(self) -> None:
        refs = (_ref(span=None), _ref(span=None))
        assert evidence_has_span(refs) is False

    def test_one_ref_with_span(self) -> None:
        refs = (_ref(span=(0, 10)),)
        assert evidence_has_span(refs) is True

    def test_some_refs_with_span(self) -> None:
        refs = (_ref(span=None), _ref(span=(5, 15)))
        assert evidence_has_span(refs) is True

    def test_all_with_span(self) -> None:
        refs = (_ref(span=(0, 5)), _ref(span=(6, 10)))
        assert evidence_has_span(refs) is True


# ============================================================================
# compare_evidence_quality — type validation
# ============================================================================


class TestCompareEvidenceQualityTypeValidation:
    """compare_evidence_quality rejects non-tuple inputs."""

    def test_a_refs_not_tuple(self) -> None:
        with pytest.raises(TypeError, match="a_refs must be a tuple"):
            compare_evidence_quality(None, ())  # type: ignore[arg-type]

    def test_b_refs_not_tuple(self) -> None:
        with pytest.raises(TypeError, match="b_refs must be a tuple"):
            compare_evidence_quality((), None)  # type: ignore[arg-type]

    def test_a_refs_is_list(self) -> None:
        with pytest.raises(TypeError, match="a_refs must be a tuple"):
            compare_evidence_quality([_ref()], ())  # type: ignore[arg-type]


# ============================================================================
# compare_evidence_quality — criterion 1: count
# ============================================================================


class TestCompareEvidenceQualityCount:
    """More evidence refs > fewer refs."""

    def test_a_has_more(self) -> None:
        a = (_ref(), _ref())
        b = (_ref(),)
        assert compare_evidence_quality(a, b) == -1

    def test_b_has_more(self) -> None:
        a = (_ref(),)
        b = (_ref(), _ref())
        assert compare_evidence_quality(a, b) == 1

    def test_both_empty_equal(self) -> None:
        assert compare_evidence_quality((), ()) == 0

    def test_equal_count(self) -> None:
        a = (_ref(), _ref())
        b = (_ref(), _ref())
        # Same count, so falls through to subsequent criteria
        result = compare_evidence_quality(a, b)
        assert result in (-1, 0, 1)  # just ensure no exception

    def test_a_has_many_more(self) -> None:
        a = (_ref(), _ref(), _ref(), _ref(), _ref())
        b = (_ref(),)
        assert compare_evidence_quality(a, b) == -1


# ============================================================================
# compare_evidence_quality — criterion 2: span
# ============================================================================


class TestCompareEvidenceQualitySpan:
    """When counts are equal, evidence with span > without span."""

    def test_a_has_span_b_does_not(self) -> None:
        a = (_ref(span=(0, 10)),)
        b = (_ref(span=None),)
        assert compare_evidence_quality(a, b) == -1

    def test_b_has_span_a_does_not(self) -> None:
        a = (_ref(span=None),)
        b = (_ref(span=(0, 10)),)
        assert compare_evidence_quality(a, b) == 1

    def test_both_have_span(self) -> None:
        a = (_ref(span=(0, 10)),)
        b = (_ref(span=(5, 15)),)
        # Both have span, falls through to next criteria
        result = compare_evidence_quality(a, b)
        assert result in (-1, 0, 1)

    def test_neither_has_span(self) -> None:
        a = (_ref(span=None), _ref(span=None))
        b = (_ref(span=None), _ref(span=None))
        result = compare_evidence_quality(a, b)
        assert result in (-1, 0, 1)

    def test_mixed_refs_a_has_span(self) -> None:
        """A has some refs with span, B has none — A should win."""
        a = (_ref(span=None), _ref(span=(0, 10)))
        b = (_ref(span=None), _ref(span=None))
        assert compare_evidence_quality(a, b) == -1


# ============================================================================
# compare_evidence_quality — criterion 3: determinism
# ============================================================================


class TestCompareEvidenceQualityDeterminism:
    """When counts and spans are equal, deterministic > non-deterministic."""

    def test_a_deterministic_b_not(self, deterministic_cap: None) -> None:
        a = (_ref(capability_id="regex_extraction", capability_version="1.0"),)
        # B has an unknown capability → treated as non-deterministic
        b = (_ref(capability_id="unknown_cap", capability_version="1.0"),)
        assert compare_evidence_quality(a, b) == -1

    def test_b_deterministic_a_not(self, deterministic_cap: None) -> None:
        a = (_ref(capability_id="unknown_cap", capability_version="1.0"),)
        b = (_ref(capability_id="regex_extraction", capability_version="1.0"),)
        assert compare_evidence_quality(a, b) == 1

    def test_both_deterministic(self, deterministic_cap: None, structured_lookup_cap: None) -> None:
        """Both deterministic → falls through to tier rank."""
        a = (_ref(capability_id="regex_extraction", capability_version="1.0"),)
        b = (_ref(capability_id="lookup", capability_version="1.0"),)
        result = compare_evidence_quality(a, b)
        assert result in (-1, 0, 1)

    def test_both_non_deterministic(self, remote_inference_cap: None) -> None:
        a = (_ref(capability_id="inference_remote", capability_version="1.0"),)
        b = (_ref(capability_id="unknown_cap", capability_version="1.0"),)
        result = compare_evidence_quality(a, b)
        assert result in (-1, 0, 1)

    def test_deterministic_beats_non_deterministic_with_same_count_and_no_span(
        self, deterministic_cap: None, local_inference_cap: None
    ) -> None:
        """Deterministic capability ref outranks non-deterministic when count/span equal."""
        a = (_ref(capability_id="regex_extraction", capability_version="1.0"),)
        b = (_ref(capability_id="inference_local", capability_version="1.0"),)
        assert compare_evidence_quality(a, b) == -1


# ============================================================================
# compare_evidence_quality — criterion 4: tier rank
# ============================================================================


class TestCompareEvidenceQualityTierRank:
    """When count, span, and determinism are equal, lower tier rank is better."""

    def test_a_lower_tier(self, deterministic_cap: None, structured_lookup_cap: None) -> None:
        """Both deterministic, A has tier 1, B has tier 2 → A wins."""
        a = (_ref(capability_id="regex_extraction", capability_version="1.0"),)
        b = (_ref(capability_id="lookup", capability_version="1.0"),)
        assert compare_evidence_quality(a, b) == -1

    def test_b_lower_tier(self, deterministic_cap: None, structured_lookup_cap: None) -> None:
        a = (_ref(capability_id="lookup", capability_version="1.0"),)
        b = (_ref(capability_id="regex_extraction", capability_version="1.0"),)
        assert compare_evidence_quality(a, b) == 1

    def test_unknown_tier_is_worst(self, deterministic_cap: None) -> None:
        """An unknown capability (tier sentinel 10) ranks below known tiers."""
        a = (_ref(capability_id="regex_extraction", capability_version="1.0"),)
        b = (_ref(capability_id="unknown_cap", capability_version="1.0"),)
        assert compare_evidence_quality(a, b) == -1  # A has lower tier rank

    def test_both_unknown(self) -> None:
        """Two unknown capabilities with same count/span/no det → tiebreak on capability_id."""
        a = (_ref(capability_id="alpha", capability_version="1.0"),)
        b = (_ref(capability_id="beta", capability_version="1.0"),)
        assert compare_evidence_quality(a, b) == -1  # "alpha" < "beta"


# ============================================================================
# compare_evidence_quality — criterion 5: lexicographic tiebreak
# ============================================================================


class TestCompareEvidenceQualityLexicographic:
    """Final tiebreak: sorted capability_id comparison."""

    def test_a_earlier_lexicographically(self) -> None:
        """All else equal: 'alpha' < 'beta'."""
        a = (_ref(capability_id="alpha", capability_version="1.0"),)
        b = (_ref(capability_id="beta", capability_version="1.0"),)
        assert compare_evidence_quality(a, b) == -1

    def test_b_earlier_lexicographically(self) -> None:
        a = (_ref(capability_id="zebra", capability_version="1.0"),)
        b = (_ref(capability_id="alpha", capability_version="1.0"),)
        assert compare_evidence_quality(a, b) == 1

    def test_identical_refs(self) -> None:
        """Identical refs → tie (0)."""
        ref = _ref(capability_id="regex_extraction", capability_version="1.0")
        assert compare_evidence_quality((ref,), (ref,)) == 0

    def test_identical_multiple_refs(self) -> None:
        r1 = _ref(capability_id="a", capability_version="1.0")
        r2 = _ref(capability_id="b", capability_version="1.0")
        assert compare_evidence_quality((r1, r2), (r1, r2)) == 0

    def test_sorted_ids_not_insertion_order(self) -> None:
        """The tiebreak uses sorted ids, not insertion order."""
        a = (
            _ref(capability_id="z", capability_version="1.0"),
            _ref(capability_id="a", capability_version="1.0"),
        )
        b = (
            _ref(capability_id="a", capability_version="1.0"),
            _ref(capability_id="z", capability_version="1.0"),
        )
        # After sorting, both produce ["a", "z"] → tie
        assert compare_evidence_quality(a, b) == 0


# ============================================================================
# compare_evidence_quality — empty edge cases
# ============================================================================


class TestCompareEvidenceQualityEmpty:
    """Edge cases with empty tuples."""

    def test_both_empty(self) -> None:
        assert compare_evidence_quality((), ()) == 0

    def test_a_empty_b_nonempty(self) -> None:
        b = (_ref(),)
        assert compare_evidence_quality((), b) == 1  # B has more refs

    def test_b_empty_a_nonempty(self) -> None:
        a = (_ref(),)
        assert compare_evidence_quality(a, ()) == -1  # A has more refs


# ============================================================================
# best_candidate_by_evidence
# ============================================================================


class TestBestCandidateByEvidence:
    """Select the candidate with the best evidence quality."""

    def test_empty_candidates_returns_none(self) -> None:
        assert best_candidate_by_evidence(()) is None

    def test_single_candidate(self) -> None:
        c = _candidate(value="x")
        result = best_candidate_by_evidence((c,))
        assert result is c

    def test_two_candidates_first_better(self) -> None:
        """First candidate has more evidence refs than second."""
        c1 = _candidate(value="better", evidence_refs=(_ref(), _ref()))
        c2 = _candidate(value="worse", evidence_refs=(_ref(),))
        result = best_candidate_by_evidence((c1, c2))
        assert result is c1

    def test_two_candidates_second_better(self) -> None:
        """Second candidate has more evidence refs than first."""
        c1 = _candidate(value="worse", evidence_refs=(_ref(),))
        c2 = _candidate(value="better", evidence_refs=(_ref(), _ref()))
        result = best_candidate_by_evidence((c1, c2))
        assert result is c2

    def test_tie_preserves_first(self) -> None:
        """Tied evidence quality → first candidate wins (deterministic)."""
        c1 = _candidate(value="first", evidence_refs=(_ref(),))
        c2 = _candidate(value="second", evidence_refs=(_ref(),))
        result = best_candidate_by_evidence((c1, c2))
        assert result is c1

    def test_tie_among_many(self) -> None:
        """Multiple tied candidates: first is returned."""
        c1 = _candidate(value="first", evidence_refs=(_ref(),))
        c2 = _candidate(value="second", evidence_refs=(_ref(),))
        c3 = _candidate(value="third", evidence_refs=(_ref(),))
        result = best_candidate_by_evidence((c1, c2, c3))
        assert result is c1

    def test_ordered_by_evidence_span_over_count_tie(self, deterministic_cap: None) -> None:
        """When counts equal, span beats no span."""
        c1 = _candidate(value="no_span", evidence_refs=(_ref(span=None),))
        c2 = _candidate(value="has_span", evidence_refs=(_ref(span=(0, 10)),))
        result = best_candidate_by_evidence((c1, c2))
        assert result is c2

    def test_ordered_by_determinism(
        self, deterministic_cap: None, local_inference_cap: None
    ) -> None:
        """When counts and spans equal, deterministic beats non-deterministic."""
        c1 = _candidate(
            value="non_det",
            evidence_refs=(_ref(capability_id="inference_local", capability_version="1.0"),),
        )
        c2 = _candidate(
            value="det",
            evidence_refs=(_ref(capability_id="regex_extraction", capability_version="1.0"),),
        )
        result = best_candidate_by_evidence((c1, c2))
        assert result is c2

    def test_mixed_evidence_refs(self) -> None:
        """Candidates with multiple evidence refs are compared correctly."""
        c1 = _candidate(value="a", evidence_refs=(_ref(capability_id="x"), _ref(capability_id="y")))
        c2 = _candidate(value="b", evidence_refs=(_ref(capability_id="x"),))
        result = best_candidate_by_evidence((c1, c2))
        assert result is c1  # c1 has 2 refs, c2 has 1


class TestBestCandidateByEvidenceTypeValidation:
    """best_candidate_by_evidence rejects non-Candidate elements."""

    def test_non_candidate_element_raises(self) -> None:
        with pytest.raises(TypeError, match="all candidates must be Candidate"):
            best_candidate_by_evidence((_candidate(), "not_a_candidate"))  # type: ignore[arg-type]

    def test_none_element_raises(self) -> None:
        with pytest.raises(TypeError, match="all candidates must be Candidate"):
            best_candidate_by_evidence((_candidate(), None))  # type: ignore[arg-type]


# ============================================================================
# Full evidence quality pipeline — integration-style
# ============================================================================


class TestEvidenceQualityPipeline:
    """Combined scenarios exercising multiple criteria at once."""

    def test_three_candidates_with_varying_quality(
        self, deterministic_cap: None, remote_inference_cap: None
    ) -> None:
        """Rank candidates by combined criteria: count, span, determinism."""
        c1 = _candidate(
            value="weak",
            evidence_refs=(_ref(span=None, capability_id="regex_extraction"),),
        )
        c2 = _candidate(
            value="medium",
            evidence_refs=(
                _ref(span=(0, 10), capability_id="regex_extraction"),
                _ref(span=(0, 10), capability_id="regex_extraction"),
            ),
        )
        c3 = _candidate(
            value="strong",
            evidence_refs=(
                _ref(span=(0, 10), capability_id="regex_extraction"),
                _ref(span=(11, 20), capability_id="regex_extraction"),
                _ref(span=(21, 30), capability_id="regex_extraction"),
            ),
        )
        result = best_candidate_by_evidence((c1, c2, c3))
        assert result is c3  # most refs → wins

    def test_unknown_capability_ranks_low(self, deterministic_cap: None) -> None:
        """Candidates using unknown capabilities rank below known ones."""
        c1 = _candidate(
            value="known",
            evidence_refs=(_ref(capability_id="regex_extraction", capability_version="1.0"),),
        )
        c2 = _candidate(
            value="unknown",
            evidence_refs=(_ref(capability_id="completely_unknown", capability_version="0.1"),),
        )
        result = best_candidate_by_evidence((c1, c2))
        assert result is c1

    def test_count_dominates_span(self) -> None:
        """A candidate with more refs (even without span) beats fewer refs (with span)."""
        c1 = _candidate(
            value="more_refs_no_span",
            evidence_refs=(_ref(span=None), _ref(span=None)),
        )
        c2 = _candidate(
            value="fewer_refs_with_span",
            evidence_refs=(_ref(span=(0, 10)),),
        )
        result = best_candidate_by_evidence((c1, c2))
        assert result is c1  # 2 refs beat 1 ref, regardless of span

    def test_count_dominates_determinism(self) -> None:
        """A candidate with more refs beats fewer refs even if non-deterministic."""
        c1 = _candidate(
            value="two_refs",
            evidence_refs=(_ref(), _ref()),
        )
        c2 = _candidate(
            value="one_ref",
            evidence_refs=(_ref(),),
        )
        result = best_candidate_by_evidence((c1, c2))
        assert result is c1
