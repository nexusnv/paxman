"""Planner policies — budget / accuracy / fallback policy application.

The :mod:`paxman.planner.policies` module applies the call-site
:class:`~paxman.budget.Policy` and the contract-level
:class:`~paxman.contract._types.ContractPolicy` to derive the
**effective policy** for a single ``paxman.normalize()`` call.

This module does **not** decide which capabilities to invoke — that
is the heuristic chain's job (:mod:`paxman.planner.heuristics`).
It decides which capabilities are **eligible** under the current
budget and policy.

The effective policy is a frozen :class:`EffectivePolicy` (a
subset of :class:`~paxman.budget.Policy` + per-call exclusions
derived from the contract's :class:`ContractPolicy`). The planner
reads this and the heuristic chain together.

Per ``docs/specs/capability-cost-model.md`` §6, the planner
estimates cost by summing ``CostHint.usd`` over the planned chain
and compares against ``Budget.max_total_cost_usd``. The same
downgrade-or-raise logic applies to latency.
"""

from __future__ import annotations

import typing
from decimal import Decimal

import attrs

from paxman.budget import Budget, Policy
from paxman.contract._types import ContractPolicy

__all__ = [
    "EffectivePolicy",
    "derive_effective_policy",
    "estimated_chain_cost",
    "estimated_chain_latency_ms",
]


@attrs.frozen(slots=True)
class EffectivePolicy:
    """The combined :class:`Budget` + :class:`Policy` for one call.

    The :class:`EffectivePolicy` collapses the call-site
    :class:`~paxman.budget.Policy` and the contract-level
    :class:`ContractPolicy` into a single set of flags the planner
    uses to filter capabilities.

    Attributes:
        allow_remote_inference: Whether the planner may select
            remote-inference capabilities (tier 5). Defaults to
            ``True``.
        allow_local_inference: Whether the planner may select
            local-inference capabilities (tier 4). Defaults to
            ``True``.
        confidence_floor: Minimum confidence to mark a field
            ``SUCCESS`` (otherwise ``PARTIAL_SUCCESS``). Defaults
            to ``0.80``.
        unresolved_acceptable: If ``True``, an unresolved required
            field yields ``PARTIAL_SUCCESS`` instead of
            ``UNRESOLVED``. Defaults to ``False``.
    """

    allow_remote_inference: bool = True
    allow_local_inference: bool = True
    confidence_floor: float = 0.80
    unresolved_acceptable: bool = False

    def __attrs_post_init__(self) -> None:
        """Validate ``confidence_floor`` range."""
        if not 0.0 <= self.confidence_floor <= 1.0:
            raise ValueError(f"confidence_floor must be in [0.0, 1.0], got {self.confidence_floor}")


def derive_effective_policy(
    policy: Policy | None,
    contract_policy: ContractPolicy | None,
) -> EffectivePolicy:
    """Derive the effective policy for one ``paxman.normalize()`` call.

    Args:
        policy: The call-site :class:`Policy`. ``None`` means "use
            defaults".
        contract_policy: The contract-level
            :class:`~paxman.contract._types.ContractPolicy`. ``None``
            means "no overrides".

    Returns:
        The combined :class:`EffectivePolicy`. Contract-level
        overrides win when set; call-site policy fills the rest.
    """
    p = policy or Policy()
    cp = contract_policy
    confidence = p.confidence_floor
    if cp is not None and cp.confidence_floor is not None:
        confidence = cp.confidence_floor
    unresolved = p.unresolved_acceptable
    if cp is not None and cp.unresolved_acceptable is not None:
        unresolved = cp.unresolved_acceptable
    return EffectivePolicy(
        allow_remote_inference=p.allow_remote_inference,
        allow_local_inference=p.allow_local_inference,
        confidence_floor=confidence,
        unresolved_acceptable=unresolved,
    )


def estimated_chain_cost(
    cost_estimates: typing.Iterable[tuple[typing.Any, ...]],
) -> Decimal:
    """Sum the USD cost over a chain of capability invocations.

    Args:
        cost_estimates: An iterable of ``(usd,)`` tuples or
            :class:`CostHint` tuples. For simplicity the function
            takes 3-tuples ``(tokens, ms, usd)``.

    Returns:
        The total estimated USD cost as a :class:`decimal.Decimal`
        (MONEY is Decimal, per ADR-0004 / ADR-0010).
    """
    total = Decimal("0")
    for tup in cost_estimates:
        if len(tup) < 3:
            continue
        usd = tup[2]
        if isinstance(usd, Decimal):
            total += usd
        else:
            total += Decimal(str(usd))
    return total


def estimated_chain_latency_ms(
    cost_estimates: typing.Iterable[tuple[int, ...]],
) -> int:
    """Sum the latency in ms over a chain of capability invocations.

    Args:
        cost_estimates: An iterable of ``(tokens, ms, usd)`` tuples.

    Returns:
        The total estimated latency in milliseconds.
    """
    total = 0
    for tup in cost_estimates:
        if len(tup) < 2:
            continue
        total += int(tup[1])
    return total


def budget_excludes_inference(
    budget: Budget | None,
) -> bool:
    """Return ``True`` if the budget excludes the ``inference`` capability.

    Per ``docs/specs/capability-cost-model.md`` §7 EC6: a
    ``Budget(max_total_cost_usd=0)`` excludes the ``inference``
    capability (whose ``CostHint.usd = 0.001``). The planner emits
    a ``BUDGET_EXCLUDES_INFERENCE`` diagnostic and proceeds with
    non-inference capabilities only.

    Args:
        budget: The :class:`Budget`. ``None`` means "no cap".

    Returns:
        ``True`` if the budget excludes the ``inference``
        capability, ``False`` otherwise.
    """
    if budget is None:
        return False
    if budget.max_total_cost_usd is None:
        return False
    # Inference's usd cost is 0.001 (per the spec). MONEY is Decimal
    # (ADR-0004 / ADR-0010), so compare against ``Decimal("0.001")``
    # rather than a float literal.
    return budget.max_total_cost_usd < Decimal("0.001")
