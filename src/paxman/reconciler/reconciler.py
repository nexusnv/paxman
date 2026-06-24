"""Top-level Reconciler — the truth-resolution orchestrator.

The :func:`reconcile` function is the **sole entry point** for the
Reconciler subsystem. It takes the per-field
:class:`~paxman.executor.field_runner.CandidateResult` records
produced by the Executor and a :class:`~paxman.contract.canonical.CanonicalContract`,
and produces one :class:`~paxman.reconciler.truth.ResolvedResult` per
field in the contract (in declaration order).

Per-field pipeline
------------------

For each :class:`~paxman.contract.canonical.CanonicalField` in the
contract, the :func:`reconcile` function executes the following steps:

1. **Look up the field's** ``CandidateResult`` (by ``field_id``).
2. **No candidates?** → :func:`~paxman.reconciler.unresolved.apply_fallback`.
3. **Filter prompt-injection candidates** via
   :func:`~paxman.reconciler.validation.validate_inference_candidates`.
   If all candidates are filtered, fall back to
   :func:`~paxman.reconciler.unresolved.apply_fallback`.
4. **Detect conflicts** via
   :func:`~paxman.reconciler.conflict.detect_conflicts`.
5. **Merge candidates** via
   :func:`~paxman.reconciler.merge.merge_candidates` with the default
   strategy (``PREFER_BY_EVIDENCE``).
6. **Assign confidence float** via
   :func:`~paxman.reconciler.confidence.assign_confidence` (the
   Reconciler is the **sole** authority per `ADR-0005`).
7. **Map float to** :class:`ConfidenceBand` via
   :func:`~paxman.reconciler.confidence.float_to_band`.
8. **Threshold check.** If the confidence is below the field's
   ``confidence_threshold``, mark the field ``UNRESOLVED`` via
   :func:`~paxman.reconciler.unresolved.apply_fallback`.
9. **Validate constraints** (if the field has any) via
   :func:`~paxman.reconciler.validation.validate_candidate` and
   record a constraint-pass / constraint-fail diagnostic. The
   ``has_validation_pass`` flag is set for the confidence assignment.
10. **Produce** :class:`~paxman.reconciler.truth.ResolvedResult`.

Boundary rules (per `ADR-0003` and ``PACKAGE_STRUCTURE.md`` §7.4):

- The Reconciler **never** executes capabilities. It calls
  :func:`paxman.capabilities.v1.validation._check_constraint`
  directly (a pure helper, not a capability invocation).
- The Reconciler **never** reads the raw input.
- The Reconciler **never** sees external schemas — only
  :class:`CanonicalContract`.
- The Reconciler is the **only** subsystem that assigns confidence.
"""

from __future__ import annotations

from paxman.budget import CurrencyPolicy
from paxman.capabilities.result import Candidate, Diagnostic, DiagnosticCode, DiagnosticSeverity
from paxman.contract.canonical import CanonicalContract, CanonicalField
from paxman.errors import ReconciliationError
from paxman.executor.field_runner import CandidateResult
from paxman.reconciler.confidence import assign_confidence, float_to_band
from paxman.reconciler.conflict import (
    detect_conflicts,
)
from paxman.reconciler.merge import MergeStrategy, merge_candidates
from paxman.reconciler.truth import ResolvedResult
from paxman.reconciler.unresolved import apply_fallback
from paxman.reconciler.validation import validate_candidate, validate_inference_candidates

__all__ = ["reconcile"]


def _result_for_field(
    field: CanonicalField,
    candidates: tuple[Candidate, ...],
    *,
    strategy: MergeStrategy,
    currency_policy: CurrencyPolicy,
) -> ResolvedResult:
    """Produce a :class:`ResolvedResult` for one field with candidates.

    The candidates are assumed to be already filtered for prompt-injection
    (the caller does that). This function is the inner per-field pipeline
    (steps 4-10 of the module docstring).
    """
    if not isinstance(field, CanonicalField):
        raise TypeError(f"field must be a CanonicalField, got {type(field).__name__}")
    if not isinstance(candidates, tuple):
        raise TypeError(f"candidates must be a tuple, got {type(candidates).__name__}")

    # Step 4: detect conflicts.
    conflict = detect_conflicts(candidates, field=field)
    has_conflict = conflict is not None

    # Step 5: merge candidates.
    merged_value, merged_evidence, strategy_name = merge_candidates(
        candidates,
        field=field,
        strategy=strategy,
        currency_policy=currency_policy,
    )

    # Step 9: validate constraints (if the field has any) before assigning confidence.
    has_validation_pass = True
    validation_diagnostics: list[Diagnostic] = []
    if field.constraints and merged_value is not None:
        # Find the first candidate whose value matches the merged value and
        # validate it. If the merged value was produced by a non-Candidate
        # path (e.g., MONEY sum), we still validate the resulting value
        # against the constraints by constructing a synthetic Candidate.
        # For V1, only validate if we can find a real candidate to use as
        # the validation context.
        primary_candidate: Candidate | None = None
        for c in candidates:
            if isinstance(c, Candidate) and c.value == merged_value:
                primary_candidate = c
                break
        if primary_candidate is None:
            # Fall back: build a synthetic Candidate so we can reuse
            # `validate_candidate`. This path is hit for MONEY merges
            # where the merged value was synthesized by money.py.
            primary_candidate = Candidate(value=merged_value)
        result = validate_candidate(primary_candidate, field=field)
        has_validation_pass = result.passed
        if not result.passed:
            validation_diagnostics.append(
                Diagnostic(
                    code=DiagnosticCode.VALIDATION_FAILED,
                    severity=DiagnosticSeverity.WARNING,
                    message=(f"validation: {len(result.failures)} constraint(s) failed"),
                    context={
                        "field_path": field.path,
                        "failures": list(result.failures),
                    },
                )
            )

    # Step 6: assign confidence.
    unique_capability_ids: list[str] = []
    seen_ids: set[str] = set()
    for c in candidates:
        if not isinstance(c, Candidate):
            continue
        for ref in c.evidence_refs:
            if not isinstance(ref, type(c.evidence_refs[0]) if c.evidence_refs else object):
                continue
            # ref is an EvidenceRef (we trust the type from capabilities.result)
            cap_id = getattr(ref, "capability_id", None)
            if isinstance(cap_id, str) and cap_id not in seen_ids:
                seen_ids.add(cap_id)
                unique_capability_ids.append(cap_id)
    total_evidence = sum(len(c.evidence_refs) for c in candidates if isinstance(c, Candidate))
    confidence = assign_confidence(
        candidate_count=sum(
            1 for c in candidates if isinstance(c, Candidate) and c.value is not None
        ),
        evidence_count=total_evidence,
        capability_ids=tuple(unique_capability_ids),
        has_validation_pass=has_validation_pass,
        has_conflict=has_conflict,
    )

    # Step 7: map to band.
    band = float_to_band(confidence)

    # Step 8: threshold check.
    if confidence < field.confidence_threshold or merged_value is None:
        diags = list(validation_diagnostics)
        if has_conflict and conflict is not None:
            diags.append(
                Diagnostic(
                    code=DiagnosticCode.CAPABILITY_OK,
                    severity=DiagnosticSeverity.INFO,
                    message=(
                        f"field unresolved: confidence {confidence:.3f} "
                        f"< threshold {field.confidence_threshold:.3f}"
                    ),
                    context={
                        "field_path": field.path,
                        "confidence": confidence,
                        "threshold": field.confidence_threshold,
                        "conflict_type": conflict.conflict_type,
                    },
                )
            )
        return apply_fallback(
            field=field,
            reason=(
                "below_threshold"
                if confidence < field.confidence_threshold
                else "no_mergeable_value"
            ),
            diagnostics=tuple(diags),
        )

    # Step 10: produce the ResolvedResult.
    return ResolvedResult(
        field_id=field.id,
        field_path=field.path,
        field_type_name=field.type.name,
        value=merged_value,
        confidence=confidence,
        confidence_band=band,
        evidence_refs=merged_evidence,
        diagnostics=tuple(validation_diagnostics),
        status="RESOLVED",
        conflict_detected=has_conflict,
        merge_strategy_used=strategy_name,
    )


def reconcile(
    candidate_results: tuple[CandidateResult, ...],
    contract: CanonicalContract,
    *,
    strategy: MergeStrategy = MergeStrategy.PREFER_BY_EVIDENCE,
    currency_policy: CurrencyPolicy = CurrencyPolicy.STRICT_MATCH,
) -> tuple[ResolvedResult, ...]:
    """Reconcile executor output into resolved truth.

    The sole entry point of the Reconciler subsystem. Takes the
    per-field :class:`~paxman.executor.field_runner.CandidateResult`
    records from the Executor and the :class:`CanonicalContract`, and
    produces one :class:`ResolvedResult` per field in the contract
    (in declaration order).

    The Reconciler is the **sole** confidence authority (`ADR-0005`).
    No other subsystem may assign a confidence float or band to a
    :class:`ResolvedResult`.

    Args:
        candidate_results: Per-field output from the Executor. May
            be empty (all fields will be unresolved). Each entry
            must reference a ``field_id`` in *contract*.
        contract: The :class:`CanonicalContract` being resolved.
            All fields in the contract are processed in declaration
            order; the output is one :class:`ResolvedResult` per
            field.
        strategy: The :class:`~paxman.reconciler.merge.MergeStrategy`
            to apply per field. Defaults to ``PREFER_BY_EVIDENCE``.
        currency_policy: The :class:`~paxman.budget.CurrencyPolicy`
            for cross-currency MONEY candidates. Defaults to
            ``STRICT_MATCH``.

    Returns:
        A tuple of :class:`ResolvedResult`, one per field in
        *contract*, in the contract's declaration order.

    Raises:
        ReconciliationError: If a ``CandidateResult`` references a
            field_id that is not in *contract* (defensive).
        TypeError: If inputs are of the wrong type.

    Examples:
        >>> from paxman.reconciler.truth import ResolvedResult
        >>> from paxman.types import ConfidenceBand
        >>> isinstance(ResolvedResult(
        ...     field_id="f1", field_path="x", field_type_name="STRING",
        ...     value="hi", confidence=0.95, confidence_band=ConfidenceBand.CERTAIN,
        ...     status="RESOLVED",
        ... ), ResolvedResult)
        True
    """
    if not isinstance(candidate_results, tuple):
        raise TypeError(
            f"candidate_results must be a tuple, got {type(candidate_results).__name__}"
        )
    if not isinstance(contract, CanonicalContract):
        raise TypeError(f"contract must be a CanonicalContract, got {type(contract).__name__}")
    if not isinstance(strategy, MergeStrategy):
        raise TypeError(f"strategy must be a MergeStrategy, got {type(strategy).__name__}")
    if not isinstance(currency_policy, CurrencyPolicy):
        raise TypeError(
            f"currency_policy must be a CurrencyPolicy, got {type(currency_policy).__name__}"
        )

    # Index candidate results by field_id.
    by_id: dict[str, CandidateResult] = {}
    for result in candidate_results:
        if not isinstance(result, CandidateResult):
            raise TypeError(
                f"candidate_results entries must be CandidateResult, got {type(result).__name__}"
            )
        if result.field_id in by_id:
            # Defensive: duplicate field_id in the executor output.
            # The Executor should never produce this, but if it does,
            # we surface it as a ReconciliationError (the contract is
            # the source of truth for field uniqueness).
            raise ReconciliationError(
                f"duplicate field_id in candidate_results: {result.field_id!r}",
                error_code="DUPLICATE_FIELD_ID",
                context={"field_id": result.field_id},
            )
        by_id[result.field_id] = result

    # Validate that every candidate_result's field_id is in the contract.
    contract_field_ids = {f.id for f in contract.fields}
    extra = set(by_id.keys()) - contract_field_ids
    if extra:
        raise ReconciliationError(
            f"candidate_results reference field_ids not in contract: {sorted(extra)}",
            error_code="UNKNOWN_FIELD_ID",
            context={"unknown_field_ids": sorted(extra)},
        )

    out: list[ResolvedResult] = []
    for field in contract.fields:
        cr: CandidateResult | None = by_id.get(field.id)
        if cr is None or not cr.candidates:
            # No candidates for this field: explicit UNRESOLVED via fallback.
            out.append(apply_fallback(field=field, reason="no_candidates"))
            continue

        # Step 3: filter prompt-injection candidates.
        filtered = validate_inference_candidates(cr.candidates, field=field)
        if not filtered:
            # All candidates were prompt-injection: explicit UNRESOLVED.
            out.append(apply_fallback(field=field, reason="prompt_injection"))
            continue

        out.append(
            _result_for_field(
                field,
                filtered,
                strategy=strategy,
                currency_policy=currency_policy,
            )
        )

    return tuple(out)
