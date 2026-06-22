"""Capability scoring — cost-based ranking for planner selection.

Per ``docs/specs/capability-cost-model.md`` §4, the planner ranks
capabilities within each tier of the heuristic chain by **ascending
score**. The score is a weighted sum of the capability's tier rank
(per :class:`~paxman.capabilities.spec.CapabilityTier`), its
:attr:`~paxman.capabilities.spec.CostHint.usd`, and its
:attr:`~paxman.capabilities.spec.CostHint.ms`.

The scoring formula is **input-independent** (per
``docs/specs/capability-cost-model.md`` §4.5). It depends only on
the capability's static metadata. This property is what underwrites
planner determinism (per `ADR-0002`).

V1 weights (per ``docs/specs/capability-cost-model.md`` §4.3):

- ``TIER_WEIGHT = 10_000`` — tier dominates.
- ``USD_WEIGHT = 1_000_000`` — within a tier, USD cost is primary.
- ``MS_WEIGHT = 1`` — latency is the tiebreaker.

Per ``docs/specs/capability-cost-model.md`` §4.6, V1 weights are
defaults; per-contract overrides are V2.
"""

from __future__ import annotations

import typing

from paxman.capabilities.spec import CapabilitySpec, CostHint

__all__ = [
    "MS_WEIGHT",
    "TIER_WEIGHT",
    "USD_WEIGHT",
    "score_capability",
]


#: Tier weight (per ``docs/specs/capability-cost-model.md`` §4.3). A
#: capability in tier N always scores lower than any capability in
#: tier N+1, regardless of cost.
TIER_WEIGHT: typing.Final[int] = 10_000

#: USD weight (per ``docs/specs/capability-cost-model.md`` §4.3). A
#: $1 capability ranks 1,000,000 points above a free one within the
#: same tier.
USD_WEIGHT: typing.Final[int] = 1_000_000

#: Latency weight (per ``docs/specs/capability-cost-model.md`` §4.3).
#: Latency is the tiebreaker within a tier and USD cost.
MS_WEIGHT: typing.Final[int] = 1


def score_capability(spec: CapabilitySpec) -> float:
    """Compute the planner score for a capability.

    Per ``docs/specs/capability-cost-model.md`` §4.2:

    ```text
    score(capability) = (
        tier_rank * TIER_WEIGHT
        + capability.cost_estimate.usd * USD_WEIGHT
        + capability.cost_estimate.ms * MS_WEIGHT
    )
    ```

    where ``tier_rank`` is the integer value of
    :attr:`CapabilityTier.value` for the spec's tier.

    The formula is **input-independent**; it depends only on the
    capability's static metadata. This is the foundation of planner
    determinism (per `ADR-0002`).

    Args:
        spec: The :class:`CapabilitySpec`.

    Returns:
        A float score. **Lower is better**: the planner picks the
        lowest-scoring capability in each tier.

    Examples:
        >>> from paxman.capabilities.spec import CapabilitySpec, CostHint, CapabilityTier
        >>> s = CapabilitySpec(
        ...     id="regex_extraction",
        ...     version="1.0",
        ...     cost_estimate=CostHint(tokens=0, ms=1, usd=0.0),
        ...     tier=CapabilityTier.LOCAL_DETERMINISTIC,
        ... )
        >>> score_capability(s)
        10001.0
    """
    tier_rank = spec.tier.value
    cost: CostHint = spec.cost_estimate
    return float(tier_rank * TIER_WEIGHT + cost.usd * USD_WEIGHT + cost.ms * MS_WEIGHT)
