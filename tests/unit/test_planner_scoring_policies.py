"""Unit tests for :mod:`paxman.planner.scoring` and :mod:`paxman.planner.policies`."""

from __future__ import annotations

from decimal import Decimal

import pytest

from paxman.budget import Budget, Policy
from paxman.capabilities.spec import (
    CapabilitySpec,
    CapabilityTier,
    CostHint,
)
from paxman.contract._types import ContractPolicy
from paxman.planner.policies import (
    budget_excludes_inference,
    derive_effective_policy,
    estimated_chain_cost,
    estimated_chain_latency_ms,
)
from paxman.planner.scoring import (
    MS_WEIGHT,
    TIER_WEIGHT,
    USD_WEIGHT,
    score_capability,
)

pytestmark = pytest.mark.unit


def _spec(
    id: str = "cap",
    version: str = "1.0",
    cost: CostHint | None = None,
    tier: CapabilityTier = CapabilityTier.LOCAL_DETERMINISTIC,
) -> CapabilitySpec:
    return CapabilitySpec(
        id=id,
        version=version,
        cost_estimate=cost or CostHint(),
        tier=tier,
    )


# --- score_capability -----------------------------------------------------


def test_score_weights_constants() -> None:
    """The V1 weights match the cost-model spec."""
    assert TIER_WEIGHT == 10_000
    assert USD_WEIGHT == 1_000_000
    assert MS_WEIGHT == 1


def test_score_local_deterministic_free() -> None:
    """A free LOCAL_DETERMINISTIC capability scores 10,001."""
    s = _spec(tier=CapabilityTier.LOCAL_DETERMINISTIC, cost=CostHint(0, 1, 0.0))
    assert score_capability(s) == 10_001.0


def test_score_text_extraction() -> None:
    """text_extraction (5 ms, free) scores 10,005."""
    s = _spec(tier=CapabilityTier.LOCAL_DETERMINISTIC, cost=CostHint(0, 5, 0.0))
    assert score_capability(s) == 10_005.0


def test_score_inference_tier_dominates() -> None:
    """A free LOCAL_DETERMINISTIC always scores lower than REMOTE_INFERENCE."""
    free_local = _spec(
        id="free_local",
        tier=CapabilityTier.LOCAL_DETERMINISTIC,
        cost=CostHint(0, 1, 0.0),
    )
    paid_remote = _spec(
        id="paid_remote",
        tier=CapabilityTier.REMOTE_INFERENCE,
        cost=CostHint(500, 1500, 0.001),
    )
    assert score_capability(free_local) < score_capability(paid_remote)


def test_score_usd_dominates_ms() -> None:
    """Within a tier, USD cost is the primary differentiator.

    Two capabilities in the same tier: ``slow_free`` (0 usd, 100 ms)
    and ``fast_paid`` (0.0001 usd, 0 ms).  The paid one scores
    higher by 100 ms * 1 = 100 points but lower by 0.0001 * 1_000_000 =
    100 points; net difference is 0 — but with ms equal, the paid
    one always scores higher.
    """
    slow_free = _spec(id="slow_free", cost=CostHint(0, 100, 0.0))
    fast_paid = _spec(id="fast_paid", cost=CostHint(0, 100, 0.001))
    # Both have ms=100 → 100 points. fast_paid has +0.001 * 1_000_000 = 1000
    # → fast_paid is 1000 higher.
    assert score_capability(fast_paid) - score_capability(slow_free) == 1000.0


def test_score_documented_example() -> None:
    """Per cost-model §4.4 example: regex_extraction scores 10,001."""
    s = _spec(
        id="regex_extraction",
        cost=CostHint(tokens=0, ms=1, usd=0.0),
    )
    assert score_capability(s) == 10_001.0


# --- derive_effective_policy ---------------------------------------------


def test_default_policy_uses_Policy_defaults() -> None:
    eff = derive_effective_policy(None, None)
    assert eff.allow_remote_inference is True
    assert eff.allow_local_inference is True
    assert eff.confidence_floor == 0.80
    assert eff.unresolved_acceptable is False


def test_policy_with_disabled_inference() -> None:
    eff = derive_effective_policy(
        Policy(allow_remote_inference=False, allow_local_inference=False),
        None,
    )
    assert eff.allow_remote_inference is False
    assert eff.allow_local_inference is False


def test_contract_policy_overrides_confidence_floor() -> None:
    """The contract policy's confidence_floor wins when set."""
    eff = derive_effective_policy(
        Policy(confidence_floor=0.7),
        ContractPolicy(confidence_floor=0.95),
    )
    assert eff.confidence_floor == 0.95


def test_call_site_policy_used_when_contract_unset() -> None:
    eff = derive_effective_policy(
        Policy(confidence_floor=0.7),
        ContractPolicy(),  # no override
    )
    assert eff.confidence_floor == 0.7


# --- budget_excludes_inference -------------------------------------------


def test_no_budget_does_not_exclude() -> None:
    assert budget_excludes_inference(None) is False


def test_unlimited_budget_does_not_exclude() -> None:
    assert budget_excludes_inference(Budget(max_total_cost_usd=None)) is False


def test_zero_budget_excludes_inference() -> None:
    """Per cost-model §7 EC6: a zero-cost budget excludes inference."""
    assert budget_excludes_inference(Budget(max_total_cost_usd=0.0)) is True


def test_sub_inference_cost_excludes() -> None:
    assert budget_excludes_inference(Budget(max_total_cost_usd=0.0001)) is True


def test_above_inference_cost_does_not_exclude() -> None:
    assert budget_excludes_inference(Budget(max_total_cost_usd=0.01)) is False


# --- estimated_chain_* ---------------------------------------------------


def test_estimated_chain_cost_sums_usd() -> None:
    """estimated_chain_cost sums the 3rd element (usd) of each tuple.

    Returns ``Decimal`` per ADR-0004 / ADR-0010 (MONEY is Decimal,
    never float). Floats in the input are coerced via
    ``Decimal(str(x))`` to preserve exact precision.

    The chain below mixes a ``float`` (which exercises the
    ``float → Decimal`` coercion path) with a pre-built ``Decimal``
    (which exercises the ``Decimal`` passthrough path). Both
    contribute to the summed result.
    """
    chain = [
        (0, 1, 0.0),  # float → Decimal coercion
        (0, 1, Decimal("0.0005")),  # Decimal passthrough
        (500, 1500, 0.001),  # float → Decimal coercion
    ]
    assert estimated_chain_cost(chain) == Decimal("0.0015")


def test_estimated_chain_cost_empty() -> None:
    assert estimated_chain_cost([]) == Decimal("0")


def test_estimated_chain_latency_ms_sums_ms() -> None:
    chain = [
        (0, 1, 0.0),
        (0, 1, 0.0),
        (500, 1500, 0.001),
    ]
    assert estimated_chain_latency_ms(chain) == 1502


def test_estimated_chain_latency_ms_empty() -> None:
    assert estimated_chain_latency_ms([]) == 0


# --- Misc ---------------------------------------------------------------


def test_effective_policy_rejects_invalid_confidence_floor() -> None:
    from paxman.planner.policies import EffectivePolicy

    with pytest.raises(ValueError, match="confidence_floor must be in"):
        EffectivePolicy(confidence_floor=1.5)
