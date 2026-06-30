"""Top-level :func:`normalize` orchestration.

The :func:`normalize` function is the primary entry point for the Paxman
library. It orchestrates the full pipeline:

1. **Adapt** — detect the caller's contract format and translate to a
   :class:`~paxman.contract.canonical.CanonicalContract`.
2. **Profile** — derive an :class:`~paxman.planner.input_profile.InputProfile`
   from the raw input.
3. **Plan** — synthesize a deterministic
   :class:`~paxman.planner.field_plan.ExecutionPlan` via the Planner.
4. **Execute** — run the plan through the Executor to produce per-field
   :class:`~paxman.executor.field_runner.CandidateResult` records.
5. **Reconcile** — merge candidates into
   :class:`~paxman.reconciler.truth.ResolvedResult` via the Reconciler.
6. **Assemble** — build the
   :class:`~paxman.artifact.artifact.ExecutionArtifact`.
7. **Hash** — compute the deterministic ``replay_hash``.
"""

from __future__ import annotations

import typing

import attrs

from paxman.artifact._hash import compute_replay_hash
from paxman.artifact.artifact import ExecutionArtifact, FieldResult
from paxman.artifact.statistics import Statistics
from paxman.budget import Budget, CurrencyPolicy, Policy
from paxman.capabilities.result import Diagnostic, DiagnosticCode, DiagnosticSeverity, EvidenceRef
from paxman.contract.canonical import CanonicalContract
from paxman.contract.registry import adapt as _adapt_contract
from paxman.contract.registry import get_adapter
from paxman.errors import (
    BudgetExceededError,
    ExecutionError,
    InvalidContractError,
    ReconciliationError,
)
from paxman.executor.executor import run as _run_executor
from paxman.planner.input_profile import InputProfile, make_profile
from paxman.planner.planner import plan as _plan
from paxman.reconciler.reconciler import reconcile as _reconcile
from paxman.reconciler.truth import ResolvedResult
from paxman.types import Status

__all__ = [
    "normalize",
]


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


# JSON Schema structural markers used to disambiguate a `dict` contract
# (see ADR-0011). The dict surface of JSON Schema and Dict DSL is disjoint
# in these markers: JSON Schema uses ``$schema``, ``$defs``, ``properties``,
# etc.; Dict DSL uses ``id`` and ``fields``.
_JSON_SCHEMA_DICT_MARKERS: typing.Final[frozenset[str]] = frozenset(
    {
        "$schema",
        "openapi",
        "$defs",
        "definitions",
        "properties",
        "patternProperties",
        "additionalProperties",
        "propertyNames",
        "required",
        "allOf",
        "anyOf",
        "oneOf",
        "not",
        "items",
        "prefixItems",
        "contains",
        "minProperties",
        "maxProperties",
        "minItems",
        "maxItems",
        "uniqueItems",
        "pattern",
        "const",
        "enum",
        "multipleOf",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "minLength",
        "maxLength",
        "format",
        "$id",
        "$ref",
        "$comment",
        "$anchor",
        "title",
        "description",
        "default",
        "examples",
        "readOnly",
        "writeOnly",
        "deprecated",
        "contentEncoding",
        "contentMediaType",
    }
)


def _looks_like_json_schema_dict(contract: dict[str, typing.Any]) -> bool:
    """Return True if *contract* has JSON Schema structural markers (ADR-0011)."""
    return any(key in contract for key in _JSON_SCHEMA_DICT_MARKERS)


def _detect_format(contract: object) -> str:
    """Auto-detect the contract adapter ``format_id`` for *contract*.

    Detection order:

    1. Pydantic ``BaseModel`` (duck-typed via ``model_fields``).
    2. :class:`dict` — JSON Schema if it has JSON Schema structural
       markers (``$schema``, ``openapi``, ``properties``, ``$defs``,
       etc.; see ADR-0011); otherwise Dict DSL.
    3. :class:`str` — JSON Schema (``json_schema:draft-2020-12``) then
       OpenAPI (``openapi:3.0``).

    Args:
        contract: The external contract object.

    Returns:
        A ``format_id`` string recognised by a registered adapter.

    Raises:
        InvalidContractError: If no adapter can be determined.
    """
    # Pydantic BaseModel (duck-type: v2+ has ``model_fields``).
    if hasattr(contract, "model_fields"):
        return "pydantic"
    if isinstance(contract, dict):
        if _looks_like_json_schema_dict(contract):
            if "openapi" in contract:
                return "openapi:3.0"
            return "json_schema:draft-2020-12"
        return "dict_dsl"
    # String: try JSON Schema then OpenAPI.
    if isinstance(contract, str):
        for candidate in ("json_schema:draft-2020-12", "openapi:3.0"):
            try:
                get_adapter(candidate)
                return candidate
            except InvalidContractError:
                continue
        raise InvalidContractError(
            "Cannot determine format for str contract; no JSON Schema or "
            "OpenAPI adapter registered",
            error_code="ADAPTER_NOT_FOUND",
            context={"contract_type": "str"},
        )
    raise InvalidContractError(
        f"Cannot determine contract format for type {type(contract).__name__}",
        error_code="ADAPTER_NOT_FOUND",
        context={"contract_type": type(contract).__name__},
    )


def _detect_and_adapt(contract: object) -> CanonicalContract:
    """Detect format and adapt *contract* to a :class:`CanonicalContract`.

    Args:
        contract: The external contract (Pydantic ``BaseModel``,
            :class:`dict`, or :class:`str`).

    Returns:
        The adapted :class:`CanonicalContract`.

    Raises:
        InvalidContractError: If detection or adaptation fails.
    """
    format_id = _detect_format(contract)
    return _adapt_contract(contract, format_id=format_id)


def _resolved_to_field_result(rr: ResolvedResult) -> FieldResult:
    """Convert a :class:`ResolvedResult` to a :class:`FieldResult`.

    Args:
        rr: The resolved result from the Reconciler.

    Returns:
        A :class:`FieldResult` suitable for inclusion in the
        :class:`ExecutionArtifact`.
    """
    return FieldResult(
        field_path=rr.field_path,
        value=rr.value,
        confidence=rr.confidence_band,
        evidence_refs=rr.evidence_refs,
        status=Status.SUCCESS if rr.status == "RESOLVED" else Status.UNRESOLVED,
    )


def _compute_overall_status(
    resolved_results: tuple[ResolvedResult, ...],
    canonical: CanonicalContract,
    policy: Policy | None,
) -> Status:
    """Determine the overall artifact :class:`Status` from per-field results.

    Args:
        resolved_results: Per-field resolved results from the Reconciler.
        canonical: The canonical contract (used to identify required fields).
        policy: The call-site :class:`Policy` (may be ``None``).

    Returns:
        The overall :class:`Status` for the artifact.
    """
    required_paths: set[str] = {f.path for f in canonical.required_fields()}
    has_unresolved_required = False
    has_any_unresolved = False

    for rr in resolved_results:
        if rr.status == "UNRESOLVED":
            has_any_unresolved = True
            if rr.field_path in required_paths:
                has_unresolved_required = True

    if not has_any_unresolved:
        return Status.SUCCESS
    if has_unresolved_required:
        if policy is not None and policy.unresolved_acceptable:
            return Status.PARTIAL_SUCCESS
        return Status.UNRESOLVED
    return Status.PARTIAL_SUCCESS


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def normalize(
    input_data: str | bytes,
    contract: object,
    budget: Budget | None = None,
    policy: Policy | None = None,
) -> ExecutionArtifact:
    """Normalize *input_data* against *contract*.

    Orchestrates the full Paxman pipeline: contract adaptation, input
    profiling, planning, execution, reconciliation, and artifact
    assembly. The returned
    :class:`~paxman.artifact.artifact.ExecutionArtifact` carries
    resolved fields, evidence, diagnostics, and a deterministic
    ``replay_hash`` for later verification.

    Args:
        input_data: The raw input to normalise. Accepts ``str`` or
            ``bytes``. ``str`` values are UTF-8 encoded with
            ``errors="replace"``.
        contract: The caller-owned contract. Accepts a Pydantic
            ``BaseModel`` class, a :class:`dict` (Dict DSL per
            ``docs/specs/dict-dsl-spec.md``), or a :class:`str`
            (JSON Schema or OpenAPI).
        budget: Optional :class:`~paxman.budget.Budget` capping
            cost and latency. ``None`` means no cap.
        policy: Optional :class:`~paxman.budget.Policy` for
            behavioural configuration. ``None`` means safe defaults.

    Returns:
        A completed :class:`~paxman.artifact.artifact.ExecutionArtifact`
        with resolved fields, evidence, diagnostics, and a deterministic
        ``replay_hash``.

    Raises:
        ExecutionError: If an unrecoverable error occurs during
            execution (e.g. a :class:`ReconciliationError` that cannot
            be encoded as a field-level diagnostic).

    Examples:
        >>> from paxman.budget import Budget
        >>> result = normalize(
        ...     input_data=b"ACME Corp\nTotal: 1,234.56",
        ...     contract={
        ...         "type": "object",
        ...         "properties": {"name": {"type": "string"}},
        ...         "required": ["name"],
        ...     },
        ...     budget=Budget(max_total_cost_usd="0.10"),
        ... )
        >>> result.status  # doctest: +SKIP
        <Status.PARTIAL_SUCCESS: 'PARTIAL_SUCCESS'>
    """
    # ------------------------------------------------------------------
    # Step 1: Adapt contract
    # ------------------------------------------------------------------
    try:
        canonical = _detect_and_adapt(contract)
    except InvalidContractError:
        return ExecutionArtifact(
            status=Status.INVALID_CONTRACT,
            normalized_data={},
            field_results={},
            unresolved_fields=[],
            evidence=(),
            diagnostics=(),
            execution_plan=None,
            statistics=Statistics(status=Status.INVALID_CONTRACT),
            contract_id="",
        )

    # ------------------------------------------------------------------
    # Step 2: Build InputProfile
    # ------------------------------------------------------------------
    profile: InputProfile = make_profile(input_data)

    # ------------------------------------------------------------------
    # Step 3: Plan
    # ------------------------------------------------------------------
    try:
        execution_plan = _plan(
            canonical=canonical,
            profile=profile,
            budget=budget,
            policy=policy,
        )
    except InvalidContractError:
        return ExecutionArtifact(
            status=Status.INVALID_CONTRACT,
            normalized_data={},
            field_results={},
            unresolved_fields=[],
            evidence=(),
            diagnostics=(),
            execution_plan=None,
            statistics=Statistics(status=Status.INVALID_CONTRACT),
            contract_id=canonical.id,
        )

    # ------------------------------------------------------------------
    # Step 4: Execute
    # ------------------------------------------------------------------
    raw_bytes: bytes = (
        input_data.encode("utf-8", errors="replace") if isinstance(input_data, str) else input_data
    )

    try:
        candidate_results = _run_executor(
            plan=execution_plan,
            raw_input=raw_bytes,
            input_profile=profile,
            budget=budget,
        )
    except BudgetExceededError:
        # Partial results: proceed with an empty candidate list.
        # The Reconciler will mark every field as UNRESOLVED, which
        # is the correct behaviour when the budget was exhausted
        # before any capability ran.
        candidate_results = []
    except ExecutionError:
        raise

    # ------------------------------------------------------------------
    # Step 5: Reconcile
    # ------------------------------------------------------------------
    try:
        resolved_results = _reconcile(
            tuple(candidate_results),
            canonical,
            currency_policy=(
                policy.currency_policy if policy is not None else CurrencyPolicy.STRICT_MATCH
            ),
        )
    except ReconciliationError as e:
        raise ExecutionError(
            f"Reconciliation failed: {e}",
            error_code="RECONCILIATION_ERROR",
            context=e.context,
        ) from e

    # ------------------------------------------------------------------
    # Step 6: Build FieldResults dict
    # ------------------------------------------------------------------
    field_results: dict[str, FieldResult] = {}
    for rr in resolved_results:
        field_results[rr.field_path] = _resolved_to_field_result(rr)

    # ------------------------------------------------------------------
    # Step 7: Assemble ExecutionArtifact
    # ------------------------------------------------------------------
    normalized_data: dict[str, object] = {
        rr.field_path: rr.value for rr in resolved_results if rr.status == "RESOLVED"
    }

    unresolved_fields: list[str] = [
        rr.field_path for rr in resolved_results if rr.status == "UNRESOLVED"
    ]

    evidence: list[EvidenceRef] = []
    for rr in resolved_results:
        evidence.extend(rr.evidence_refs)

    diagnostics: list[Diagnostic] = []
    for rr in resolved_results:
        diagnostics.extend(rr.diagnostics)
    # Include plan-level diagnostics as INFO diagnostics.
    for pd in execution_plan.diagnostics:
        diagnostics.append(
            Diagnostic(
                code=DiagnosticCode.CAPABILITY_OK,
                severity=DiagnosticSeverity.INFO,
                message=f"[{pd.code}] {pd.message}",
                context=pd.context,
            )
        )

    # Collect capability versions from candidate evidence.
    capability_versions: dict[str, str] = {}
    for cr in candidate_results:
        for ev in cr.evidence:
            if isinstance(ev, EvidenceRef):
                capability_versions[ev.capability_id] = ev.capability_version

    overall_status = _compute_overall_status(resolved_results, canonical, policy)

    resolved_count = sum(1 for rr in resolved_results if rr.status == "RESOLVED")
    unresolved_count = sum(1 for rr in resolved_results if rr.status == "UNRESOLVED")

    artifact = ExecutionArtifact(
        status=overall_status,
        normalized_data=normalized_data,
        field_results=field_results,
        unresolved_fields=unresolved_fields,
        evidence=tuple(evidence),
        diagnostics=tuple(diagnostics),
        execution_plan=execution_plan,
        statistics=Statistics(
            status=overall_status,
            total_fields=len(canonical.fields),
            resolved_fields=resolved_count,
            unresolved_fields=unresolved_count,
        ),
        contract_id=canonical.id,
        capability_versions=capability_versions,
    )

    # ------------------------------------------------------------------
    # Step 8: Compute replay hash
    # ------------------------------------------------------------------
    artifact = attrs.evolve(artifact, replay_hash=compute_replay_hash(artifact))

    return artifact
