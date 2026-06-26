"""Unit tests for :mod:`paxman.executor.budget_tracker`.

Per Sprint 4 D4.4: ``BudgetTracker`` is the Executor's gate
for ``Budget`` enforcement. The tests pin the gate's
simulate-then-book protocol and the four short-circuit reasons.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from paxman.budget import Budget
from paxman.errors import InvalidBudgetError
from paxman.executor.budget_tracker import (
    EXCEEDED_REASON_COST,
    EXCEEDED_REASON_INVOCATIONS,
    EXCEEDED_REASON_LATENCY,
    EXCEEDED_REASON_REMOTE,
    BudgetTracker,
)

pytestmark = pytest.mark.unit


# --- construction ------------------------------------------------------


def test_no_budget_means_no_cap() -> None:
    t = BudgetTracker(budget=None)
    assert t.budget is None
    assert t.exceeded_reason() is None
    assert t.is_exceeded() is False


def test_construction_rejects_non_budget() -> None:
    with pytest.raises(TypeError, match="budget must be a Budget or None"):
        BudgetTracker(budget="not a budget")  # type: ignore[arg-type]


def test_from_budget_helper() -> None:
    t = BudgetTracker.from_budget(Budget(max_total_cost_usd=0.10))
    assert t.budget is not None
    # ``max_total_cost_usd`` is stored as ``Decimal`` (MONEY is
    # Decimal, per ADR-0004 / ADR-0010). The constructor accepts
    # the float literal ``0.10`` and coerces via ``Decimal(str(x))``.
    assert t.budget.max_total_cost_usd == Decimal("0.10")


def test_from_budget_none() -> None:
    t = BudgetTracker.from_budget(None)
    assert t.budget is None


def test_from_budget_rejects_non_budget() -> None:
    with pytest.raises(InvalidBudgetError, match="budget must be a Budget"):
        BudgetTracker.from_budget("nope")  # type: ignore[arg-type]


# --- record -----------------------------------------------------------


def test_record_increments_counters() -> None:
    t = BudgetTracker(budget=Budget(max_total_cost_usd=0.10))
    t.record(cost_usd=0.05, latency_ms=10)
    # ``total_cost_usd`` is ``Decimal`` (MONEY is Decimal per
    # ADR-0004 / ADR-0010). ``pytest.approx`` is float-only; use
    # exact ``Decimal`` comparison.
    assert t.total_cost_usd == Decimal("0.05")
    assert t.total_latency_ms == 10
    assert t.invocation_count == 1
    assert t.remote_inference_count == 0


def test_record_remote_inference_increments_remote_counter() -> None:
    t = BudgetTracker()
    t.record(cost_usd=0.001, latency_ms=100, is_remote_inference=True)
    assert t.remote_inference_count == 1


def test_record_rejects_negative_cost() -> None:
    t = BudgetTracker()
    with pytest.raises(ValueError, match="cost_usd must be non-negative"):
        t.record(cost_usd=-0.01)


def test_record_rejects_negative_latency() -> None:
    t = BudgetTracker()
    with pytest.raises(ValueError, match="latency_ms must be non-negative"):
        t.record(latency_ms=-1)


def test_record_rejects_bool_latency() -> None:
    t = BudgetTracker()
    with pytest.raises(TypeError, match="latency_ms must be an int"):
        t.record(latency_ms=True)  # type: ignore[arg-type]


# --- would_exceed ----------------------------------------------------


def test_would_exceed_cost() -> None:
    t = BudgetTracker(budget=Budget(max_total_cost_usd=0.10))
    assert t.would_exceed(cost_usd=0.05) is False
    t.record(cost_usd=0.05)
    assert t.would_exceed(cost_usd=0.06) is True


def test_would_exceed_latency() -> None:
    t = BudgetTracker(budget=Budget(max_total_latency_ms=1000))
    assert t.would_exceed(latency_ms=500) is False
    t.record(latency_ms=500)
    assert t.would_exceed(latency_ms=600) is True


def test_would_exceed_remote_inference_count() -> None:
    t = BudgetTracker(budget=Budget(max_remote_inference_calls=2))
    assert t.would_exceed(is_remote_inference=True) is False
    t.record(is_remote_inference=True)
    assert t.would_exceed(is_remote_inference=True) is False
    t.record(is_remote_inference=True)
    # Now the next remote call would exceed.
    assert t.would_exceed(is_remote_inference=True) is True


def test_would_exceed_remote_only_counts_when_remote() -> None:
    t = BudgetTracker(budget=Budget(max_remote_inference_calls=0))
    # A non-remote invocation should not be blocked.
    assert t.would_exceed(is_remote_inference=False) is False
    # A remote invocation should be blocked.
    assert t.would_exceed(is_remote_inference=True) is True


def test_would_exceed_invocations() -> None:
    t = BudgetTracker(budget=Budget(max_capability_invocations=2))
    assert t.would_exceed() is False
    t.record()
    assert t.would_exceed() is False
    t.record()
    assert t.would_exceed() is True


def test_would_exceed_no_budget_always_false() -> None:
    t = BudgetTracker(budget=None)
    assert t.would_exceed(cost_usd=999_999.0) is False


# --- exceeded_reason -------------------------------------------------


def test_exceeded_reason_returns_cost() -> None:
    t = BudgetTracker(budget=Budget(max_total_cost_usd=0.10))
    t.record(cost_usd=0.11)
    assert t.exceeded_reason() == EXCEEDED_REASON_COST
    assert t.is_exceeded() is True


def test_exceeded_reason_returns_latency() -> None:
    t = BudgetTracker(budget=Budget(max_total_latency_ms=100))
    t.record(latency_ms=101)
    assert t.exceeded_reason() == EXCEEDED_REASON_LATENCY


def test_exceeded_reason_returns_remote() -> None:
    t = BudgetTracker(budget=Budget(max_remote_inference_calls=1))
    t.record(is_remote_inference=True)
    t.record(is_remote_inference=True)
    assert t.exceeded_reason() == EXCEEDED_REASON_REMOTE


def test_exceeded_reason_returns_invocations() -> None:
    t = BudgetTracker(budget=Budget(max_capability_invocations=1))
    t.record()
    t.record()
    assert t.exceeded_reason() == EXCEEDED_REASON_INVOCATIONS


def test_exceeded_reason_none_when_within_budget() -> None:
    t = BudgetTracker(budget=Budget(max_total_cost_usd=1.0))
    t.record(cost_usd=0.5)
    assert t.exceeded_reason() is None
    assert t.is_exceeded() is False


def test_exceeded_reason_priority_cost_first() -> None:
    """When multiple caps are exceeded, ``max_total_cost_usd`` wins."""
    t = BudgetTracker(
        budget=Budget(
            max_total_cost_usd=0.10,
            max_total_latency_ms=10,
        )
    )
    t.record(cost_usd=0.20, latency_ms=20)
    assert t.exceeded_reason() == EXCEEDED_REASON_COST
