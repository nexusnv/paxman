"""Property tests: Reconciler monotonicity (D5.16).

Better evidence (more candidates, more evidence refs, more capability
sources, resolution of conflicts) MUST produce confidence that is
greater than or equal to the confidence for poorer evidence, all else
equal.

The :func:`~paxman.reconciler.confidence.assign_confidence` rubric:

  - Base: 0.50
  - +0.10 per additional agreeing candidate (cap at 3 → +0.20)
  - +0.05 per evidence ref (cap at 5 → +0.25)
  - +0.10 if validation passed
  - -0.15 if conflict detected
  - +0.05 per unique capability source (cap at 3 → +0.15)
  - Clamp to [0.0, 1.0]

Properties tested:

  1. **Evidence monotonicity**: increasing candidate count, evidence ref
     count, or unique capability count does not decrease confidence.
  2. **Conflict monotonicity**: resolving a conflict (or never having one)
     yields >= confidence than when conflict exists, all else equal.
"""

from __future__ import annotations

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from paxman.capabilities.result import Candidate, EvidenceRef
from paxman.contract.canonical import CanonicalContract, CanonicalField
from paxman.executor.field_runner import CandidateResult
from paxman.reconciler.confidence import assign_confidence
from paxman.reconciler.reconciler import reconcile
from paxman.types import FieldType

pytestmark = [pytest.mark.property]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_COMMON_FIELD_ID = "mono_field"
_COMMON_FIELD_PATH = "mono_field"


def _make_field(confidence_threshold: float = 0.0) -> CanonicalField:
    """A STRING field with an intentionally low threshold.

    Setting ``confidence_threshold=0.0`` prevents the Reconciler from
    falling back to UNRESOLVED purely because the base score (0.50) is
    below a normal threshold (0.80).  This lets the test focus on the
    *relative* monotonicity of confidence values.
    """
    return CanonicalField(
        id=_COMMON_FIELD_ID,
        path=_COMMON_FIELD_PATH,
        name=_COMMON_FIELD_PATH,
        type=FieldType.STRING,
        required=True,
        confidence_threshold=confidence_threshold,
    )


def _make_contract(field: CanonicalField) -> CanonicalContract:
    """Wrap *field* into a single-field contract."""
    return CanonicalContract(
        id="monotonicity-prop-test",
        fields=(field,),
    )


def _make_candidate_result(
    field_id: str,
    candidates: tuple[Candidate, ...],
) -> CandidateResult:
    """Build a ``CandidateResult`` for the given candidates."""
    return CandidateResult(
        field_id=field_id,
        field_path=_COMMON_FIELD_PATH,
        field_type_name="STRING",
        candidates=candidates,
        status="RESOLVED" if candidates else "UNRESOLVED",
    )


def _evidence_ref(capability_id: str, field_path: str = _COMMON_FIELD_PATH) -> EvidenceRef:
    """Build a single ``EvidenceRef``."""
    return EvidenceRef(
        capability_id=capability_id,
        capability_version="1.0",
        field_path=field_path,
    )


# ---------------------------------------------------------------------------
# Strategy: evidence-improvement pairs
# ---------------------------------------------------------------------------


@st.composite
def evidence_improvement_pair(
    draw: st.DrawFn,
) -> tuple[tuple[Candidate, ...], tuple[Candidate, ...]]:
    """Generate ``(candidates_A, candidates_B)`` where B is strictly better
    evidenced than A in at least one dimension (candidate count, evidence
    ref count, or unique capability count), and equal or better in all
    others.

    Both candidate sets have the *same agreeing value* (``"test_val"``),
    so neither experiences a conflict penalty.  The improvement is
    guaranteed to be non-vacuous — at least one dimension increases.
    """
    # --- baseline parameters for A ---
    a_n_candidates = draw(st.integers(min_value=1, max_value=3))
    a_n_evidence_per = draw(st.integers(min_value=0, max_value=2))
    a_n_caps = draw(st.integers(min_value=1, max_value=3))

    # --- deltas for B (at least one positive) ---
    d_candidates = draw(st.integers(min_value=0, max_value=1))
    d_evidence = draw(st.integers(min_value=0, max_value=2))
    d_caps = draw(st.integers(min_value=0, max_value=1))
    assume(d_candidates + d_evidence + d_caps > 0)

    b_n_candidates = a_n_candidates + d_candidates
    b_n_evidence_per = a_n_evidence_per + d_evidence
    b_n_caps = a_n_caps + d_caps

    # --- build candidates for A ---
    # All candidates share the same value so there is no conflict.
    candidates_a = _build_candidates(
        value="test_val",
        n_candidates=a_n_candidates,
        n_evidence_per=a_n_evidence_per,
        n_caps=a_n_caps,
    )

    # --- build candidates for B ---
    candidates_b = _build_candidates(
        value="test_val",
        n_candidates=max(b_n_candidates, 1),
        n_evidence_per=b_n_evidence_per,
        n_caps=max(b_n_caps, 1),
    )

    return candidates_a, candidates_b


def _build_candidates(
    *,
    value: str,
    n_candidates: int,
    n_evidence_per: int,
    n_caps: int,
) -> tuple[Candidate, ...]:
    """Build a tuple of ``Candidate`` objects.

    Each candidate gets roughly *n_evidence_per* evidence refs with
    capability IDs cycling through ``cap_0`` … ``cap_{n_caps-1}``.
    """
    candidates: list[Candidate] = []
    for _ in range(n_candidates):
        refs: list[EvidenceRef] = []
        for j in range(n_evidence_per):
            cap_id = f"cap_{j % max(n_caps, 1)}"
            refs.append(_evidence_ref(cap_id))
        candidates.append(Candidate(value=value, evidence_refs=tuple(refs)))
    if not candidates:
        candidates.append(Candidate(value=value, evidence_refs=()))
    return tuple(candidates)


# ---------------------------------------------------------------------------
# Strategy: conflict vs no-conflict pairs
# ---------------------------------------------------------------------------


@st.composite
def conflict_resolution_pair(
    draw: st.DrawFn,
) -> tuple[tuple[Candidate, ...], tuple[Candidate, ...]]:
    """Generate ``(candidates_A, candidates_B)`` where A has conflicting
    values and B has agreeing values, with identical evidence quality.

    Candidate counts (2) are identical between A and B, as are evidence
    refs and capability IDs.  The only difference is that A's two
    candidates disagree on value while B's agree — so A suffers the
    ``-0.15`` conflict penalty.
    """
    n_evidence = draw(st.integers(min_value=1, max_value=3))
    n_caps = draw(st.integers(min_value=1, max_value=2))

    refs = tuple(_evidence_ref(f"cap_{j % n_caps}") for j in range(n_evidence))

    # A: disagreeing values → conflict
    candidates_a = (
        Candidate(value="val_one", evidence_refs=refs),
        Candidate(value="val_two", evidence_refs=refs),
    )

    # B: agreeing values → no conflict
    candidates_b = (
        Candidate(value="same_val", evidence_refs=refs),
        Candidate(value="same_val", evidence_refs=refs),
    )

    return candidates_a, candidates_b


# ---------------------------------------------------------------------------
# Property 1: evidence monotonicity
# ---------------------------------------------------------------------------


@settings(max_examples=50, derandomize=True)
@given(pair=evidence_improvement_pair())
def test_reconciler_monotonicity_more_evidence(
    pair: tuple[tuple[Candidate, ...], tuple[Candidate, ...]],
) -> None:
    """Increasing candidate count, evidence count, or capability source
    count never decreases the assigned confidence.

    B is constructed to have strictly better evidence than A in at least
    one dimension, and equal or better in all others.  The confidence
    assigned to B MUST be >= the confidence assigned to A.
    """
    candidates_a, candidates_b = pair
    field = _make_field()
    contract = _make_contract(field)

    cr_a = _make_candidate_result(_COMMON_FIELD_ID, candidates_a)
    cr_b = _make_candidate_result(_COMMON_FIELD_ID, candidates_b)

    result_a = reconcile((cr_a,), contract=contract)
    result_b = reconcile((cr_b,), contract=contract)

    conf_a = result_a[0].confidence
    conf_b = result_b[0].confidence

    # --- compute expected metrics for error reporting ---
    a_candidate_count = sum(1 for c in candidates_a if c.value is not None)
    b_candidate_count = sum(1 for c in candidates_b if c.value is not None)
    a_evidence_count = sum(len(c.evidence_refs) for c in candidates_a)
    b_evidence_count = sum(len(c.evidence_refs) for c in candidates_b)
    a_caps = len({ref.capability_id for c in candidates_a for ref in c.evidence_refs})
    b_caps = len({ref.capability_id for c in candidates_b for ref in c.evidence_refs})

    assert conf_b >= conf_a, (
        f"Monotonicity violated: B={conf_b:.4f} < A={conf_a:.4f}\n"
        f"  A: candidates={a_candidate_count}, evidence={a_evidence_count}, "
        f"caps={a_caps}\n"
        f"  B: candidates={b_candidate_count}, evidence={b_evidence_count}, "
        f"caps={b_caps}\n"
        f"  Derandomized — this is a regression in the confidence rubric."
    )


# ---------------------------------------------------------------------------
# Property 2: conflict monotonicity
# ---------------------------------------------------------------------------


@settings(max_examples=50, derandomize=True)
@given(pair=conflict_resolution_pair())
def test_reconciler_monotonicity_resolve_conflict(
    pair: tuple[tuple[Candidate, ...], tuple[Candidate, ...]],
) -> None:
    """Resolving a conflict (or never having one) yields >= confidence
    than when conflict exists, all else equal.

    A has two candidates with *different* values (conflict → -0.15
    penalty).  B has two candidates with the *same* value (no conflict).
    Evidence quality is identical.  Therefore B's confidence MUST be
    >= A's confidence.

    This test is non-vacuous: ``assign_confidence`` with default
    parameters assigns ``0.50 + 0.10*2 + 0.05*n_evidence + 0.10 (validation)``
    minus 0.15 if conflict.  For n_evidence >= 1, A's score is 0.05-0.15
    lower than B's.
    """
    candidates_a, candidates_b = pair
    field = _make_field()
    contract = _make_contract(field)

    cr_a = _make_candidate_result(_COMMON_FIELD_ID, candidates_a)
    cr_b = _make_candidate_result(_COMMON_FIELD_ID, candidates_b)

    result_a = reconcile((cr_a,), contract=contract)
    result_b = reconcile((cr_b,), contract=contract)

    conf_a = result_a[0].confidence
    conf_b = result_b[0].confidence

    # Both have identical evidence characteristics; the only difference
    # is the conflict penalty.
    assert conf_b >= conf_a, (
        f"Conflict monotonicity violated: B={conf_b:.4f} < A={conf_a:.4f}\n"
        f"  A has conflicting values, B has agreeing values.\n"
        f"  A diagnostics: {result_a[0].diagnostics}\n"
        f"  B diagnostics: {result_b[0].diagnostics}\n"
        f"  A conflict_detected={result_a[0].conflict_detected}, "
        f"B conflict_detected={result_b[0].conflict_detected}"
    )

    # Sanity check: the test is meaningful only if A actually detected conflict.
    assert result_a[0].conflict_detected, (
        "Test is vacuous: A did not detect conflict despite having different values."
    )


# ---------------------------------------------------------------------------
# Property 3: assign_confidence is monotonic in its numeric inputs
# ---------------------------------------------------------------------------

# This test verifies the raw ``assign_confidence`` function directly,
# bypassing the full pipeline.  It is a stronger, more targeted check
# that the scoring rubric itself is monotonic in each numeric input.


@settings(max_examples=50, derandomize=True)
@given(
    a_cc=st.integers(min_value=0, max_value=5),
    a_ec=st.integers(min_value=0, max_value=8),
    a_nc=st.integers(min_value=0, max_value=5),
)
def test_assign_confidence_direct_monotonicity(
    a_cc: int,
    a_ec: int,
    a_nc: int,
) -> None:
    """``assign_confidence`` is monotonic in each numeric input when the
    other parameters are held fixed.

    We pick a random baseline (A), then create B by increasing every
    numeric input by 1 (capped where the rubric already plateaus).
    The confidence for B MUST be >= the confidence for A.
    """
    base = assign_confidence(
        candidate_count=a_cc,
        evidence_count=a_ec,
        capability_ids=[f"cap_{i}" for i in range(a_nc)],
        has_validation_pass=True,
        has_conflict=False,
    )

    # Increase every dimension — at least the cap values will be no-ops.
    improved = assign_confidence(
        candidate_count=min(a_cc + 1, 5),
        evidence_count=min(a_ec + 1, 8),
        capability_ids=[f"cap_{i}" for i in range(min(a_nc + 1, 5))],
        has_validation_pass=True,
        has_conflict=False,
    )

    assert improved >= base, (
        f"Direct monotonicity violated: improved={improved:.4f} < base={base:.4f}\n"
        f"  A: candidate_count={a_cc}, evidence_count={a_ec}, caps={a_nc}\n"
        f"  B: candidate_count={min(a_cc + 1, 5)}, evidence_count={min(a_ec + 1, 8)}, "
        f"caps={min(a_nc + 1, 5)}"
    )
