"""The top-level :func:`plan` function — planner entry point.

Per `ADR-0002` and ``ARCHITECTURE.md`` §4.2, the planner is a
**pure function**:

    plan(
        canonical: CanonicalContract,
        profile: InputProfile,
        budget: Budget,
        policy: Policy,
        registry: Mapping[tuple[str, str], Capability],
    ) -> ExecutionPlan

No clock, no random, no I/O. Given the same inputs, the planner
always produces the same :class:`ExecutionPlan` byte-for-byte.

Sprint 3 does **not** execute the plan. The Executor (Sprint 4)
walks the plan. This module's only output is the
:class:`ExecutionPlan`.

Pipeline
--------

1. **Derive the effective policy** — combine the call-site
   :class:`~paxman.budget.Policy` with the contract's
   :class:`~paxman.contract._types.ContractPolicy` (per
   :mod:`paxman.planner.policies`).
2. **Walk the contract's required fields** — for each required
   :class:`~paxman.contract.canonical.CanonicalField`, build a
   :class:`FieldPlan` via the 7-step heuristic chain (per
   :mod:`paxman.planner.heuristics`).
3. **Collect diagnostics** — emit one diagnostic per excluded tier
   (e.g., ``BUDGET_EXCLUDES_INFERENCE`` if the budget caps USD
   below the inference cost floor).
4. **Build the :class:`ExecutionPlan`** — return the ordered tuple
   of :class:`FieldPlan` records.

Public surface (per ``PACKAGE_STRUCTURE.md`` §4.3):

- :class:`ExecutionPlan` — re-exported from :mod:`paxman.planner.field_plan`.
- :class:`FieldPlan` — re-exported.
- :class:`Heuristic` Protocol — re-exported in ``paxman.api.protocols``
  (post-V1).
- :func:`register_heuristic` — ``paxman.api`` (post-V1).
"""

from __future__ import annotations

import typing

from paxman.budget import Budget, Policy
from paxman.capabilities.base import Capability
from paxman.contract._types import ContractPolicy
from paxman.contract.canonical import CanonicalContract
from paxman.planner._registry import get_global_registry
from paxman.planner.field_plan import (
    ExecutionPlan,
    FieldPlan,
    PlanDiagnostic,
)
from paxman.planner.heuristics import build_field_plan
from paxman.planner.input_profile import InputProfile
from paxman.planner.policies import (
    budget_excludes_inference,
    derive_effective_policy,
)

__all__ = ["plan"]


def plan(
    canonical: CanonicalContract,
    profile: InputProfile,
    budget: Budget | None = None,
    policy: Policy | None = None,
    registry: typing.Mapping[tuple[str, str], Capability] | None = None,
) -> ExecutionPlan:
    """Synthesize a deterministic :class:`ExecutionPlan` for *canonical*.

    The planner is a **pure function** (per `ADR-0002`). Given the
    same canonical contract, input profile, budget, policy, and
    capability registry, it always produces the same plan.

    Args:
        canonical: The :class:`CanonicalContract` to plan against.
        profile: The :class:`InputProfile` derived from the raw
            input (per :func:`paxman.planner.input_profile.make_profile`).
        budget: The :class:`Budget` (optional; ``None`` means no cap).
        policy: The :class:`Policy` (optional; ``None`` means
            defaults).
        registry: An optional capability registry. ``None`` (the
            default) uses the global
            :func:`paxman.capabilities.registry.all_capabilities`.

    Returns:
        The :class:`ExecutionPlan`: one :class:`FieldPlan` per
        required field, in declaration order.

    Examples:
        >>> from paxman.contract.canonical import CanonicalContract, CanonicalField
        >>> from paxman.types import FieldType
        >>> canonical = CanonicalContract(
        ...     id="invoice",
        ...     fields=(
        ...         CanonicalField(
        ...             id="f1",
        ...             path="supplier_name",
        ...             name="supplier_name",
        ...             type=FieldType.STRING,
        ...             required=True,
        ...         ),
        ...     ),
        ... )
        >>> from paxman.planner.input_profile import make_profile
        >>> profile = make_profile(b"ACME Corp\\nInvoice #1234")
        >>> p = plan(canonical, profile)
        >>> len(p.field_plans)
        1
    """
    if registry is None:
        registry = get_global_registry()

    p = policy or Policy()
    cp: ContractPolicy | None = canonical.policies
    # Combine call-site and contract policies so that contract-level
    # overrides (e.g. ``ContractPolicy.confidence_floor``) are
    # honored downstream.
    effective = derive_effective_policy(p, cp)

    field_plans: list[FieldPlan] = []
    diagnostics: list[PlanDiagnostic] = []

    # Diagnostic: budget excludes inference.
    if budget_excludes_inference(budget):
        diagnostics.append(
            PlanDiagnostic(
                code="BUDGET_EXCLUDES_INFERENCE",
                message=(
                    "Budget max_total_cost_usd excludes inference capabilities; "
                    "fields requiring inference will be UNRESOLVED"
                ),
                context={
                    "max_total_cost_usd": budget.max_total_cost_usd if budget is not None else None,
                },
            )
        )

    # Diagnostic: policy excludes remote inference.
    if not p.allow_remote_inference:
        diagnostics.append(
            PlanDiagnostic(
                code="POLICY_EXCLUDES_REMOTE_INFERENCE",
                message=(
                    "Policy.allow_remote_inference=False; "
                    "heuristic step 6 (remote inference) is dropped"
                ),
            )
        )

    # Diagnostic: policy excludes local inference.
    if not p.allow_local_inference:
        diagnostics.append(
            PlanDiagnostic(
                code="POLICY_EXCLUDES_LOCAL_INFERENCE",
                message=(
                    "Policy.allow_local_inference=False; "
                    "heuristic step 5 (local inference) is dropped"
                ),
            )
        )

    # Walk the contract's required fields and build a plan for each.
    for field in canonical.required_fields():
        # Pass the **effective** policy (call-site + contract) so the
        # heuristic chain applies contract-level overrides
        # (e.g. ``ContractPolicy.confidence_floor``).
        fp = build_field_plan(field, profile, effective, budget, registry)
        field_plans.append(fp)
        # Per-field UNRESOLVED diagnostic if the chain is empty.
        if not fp.capability_chain:
            diagnostics.append(
                PlanDiagnostic(
                    code="FIELD_UNRESOLVED",
                    message=(
                        f"Field {field.name!r} ({field.id}) has no eligible "
                        f"capability under the current policy and budget; "
                        f"will be UNRESOLVED"
                    ),
                    field_id=field.id,
                    context={
                        "field_path": field.path,
                        "field_type": field.type.name,
                    },
                )
            )

    return ExecutionPlan(
        field_plans=tuple(field_plans),
        diagnostics=tuple(diagnostics),
        input_content_hash=profile.content_hash,
        contract_id=canonical.id,
    )
