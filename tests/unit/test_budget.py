"""Unit tests for ``paxman.budget`` — Budget, Policy, CurrencyPolicy models.

Per V1_ACCEPTANCE_CRITERIA.md §2.2, ``errors.py`` and ``versioning.py`` must
have 100% coverage. The other cross-cutting modules (budget, clock, ids,
logging, serialization) must collectively satisfy the ≥90% project
threshold set in pyproject.toml.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from paxman.budget import Budget, CurrencyPolicy, Policy

# --- CurrencyPolicy ---------------------------------------------------------


def test_currency_policy_has_three_values() -> None:
    """CurrencyPolicy has STRICT_MATCH, ALLOW_FX, REJECT_WITHOUT_RATE."""
    names = {member.name for member in CurrencyPolicy}
    assert names == {"STRICT_MATCH", "ALLOW_FX", "REJECT_WITHOUT_RATE"}


def test_currency_policy_values_are_uppercase_strings() -> None:
    """All CurrencyPolicy values are uppercase strings (artifact JSON format)."""
    for member in CurrencyPolicy:
        assert isinstance(member.value, str)
        assert member.value == member.value.upper()


# --- Budget validation ------------------------------------------------------


def test_budget_default_is_all_none() -> None:
    """``Budget()`` with no arguments has all caps set to None (no cap)."""
    b = Budget()
    assert b.max_total_cost_usd is None
    assert b.max_total_latency_ms is None
    assert b.max_remote_inference_calls is None
    assert b.max_capability_invocations is None


def test_budget_accepts_zero_values() -> None:
    """``Budget(max_total_cost_usd=0)`` is valid (zero is not negative)."""
    b = Budget(max_total_cost_usd=0.0, max_total_latency_ms=0)
    assert b.max_total_cost_usd == Decimal("0")
    assert b.max_total_latency_ms == 0


def test_budget_accepts_float_literal_for_cost() -> None:
    """``Budget(max_total_cost_usd=0.10)`` (a float literal) coerces to Decimal.

    Backward-compat lock: existing call sites pass float literals; the
    constructor must continue to accept them and store as Decimal per
    ADR-0004 / ADR-0010 ("MONEY is Decimal, never float").
    """
    b = Budget(max_total_cost_usd=0.10)
    assert b.max_total_cost_usd == Decimal("0.10")
    assert isinstance(b.max_total_cost_usd, Decimal)


def test_budget_rejects_negative_cost() -> None:
    """``Budget(max_total_cost_usd=-0.01)`` raises ValueError."""
    with pytest.raises(ValueError, match="max_total_cost_usd must be non-negative"):
        Budget(max_total_cost_usd=-0.01)


def test_budget_rejects_negative_latency() -> None:
    """``Budget(max_total_latency_ms=-1)`` raises ValueError."""
    with pytest.raises(ValueError, match="max_total_latency_ms must be non-negative"):
        Budget(max_total_latency_ms=-1)


def test_budget_rejects_negative_remote_calls() -> None:
    """``Budget(max_remote_inference_calls=-1)`` raises ValueError."""
    with pytest.raises(ValueError, match="max_remote_inference_calls must be non-negative"):
        Budget(max_remote_inference_calls=-1)


def test_budget_rejects_negative_capability_invocations() -> None:
    """``Budget(max_capability_invocations=-1)`` raises ValueError."""
    with pytest.raises(ValueError, match="max_capability_invocations must be non-negative"):
        Budget(max_capability_invocations=-1)


def test_budget_is_frozen() -> None:
    """``Budget`` is frozen (attrs.frozen); assignment raises FrozenInstanceError."""
    b = Budget(max_total_cost_usd=1.0)
    with pytest.raises(BaseException):  # FrozenInstanceError  # noqa: B017
        b.max_total_cost_usd = Decimal("5.0")  # type: ignore[misc]


# --- Policy defaults --------------------------------------------------------


def test_policy_defaults_match_spec() -> None:
    """``Policy()`` defaults match the spec in the module docstring."""
    p = Policy()
    assert p.allow_remote_inference is True
    assert p.allow_local_inference is True
    assert p.confidence_floor == 0.80
    assert p.unresolved_acceptable is False
    assert p.currency_policy is CurrencyPolicy.STRICT_MATCH
    assert p.emit_metrics is False
    assert p.log_raw_input is False
    assert p.record_inference_io is False
    assert p.embed_evidence_payload is False


def test_policy_accepts_alternative_confidence_floor() -> None:
    """Policy accepts a different ``confidence_floor``."""
    p = Policy(confidence_floor=0.5)
    assert p.confidence_floor == 0.5


def test_policy_accepts_currency_policy_override() -> None:
    """Policy accepts an explicit ``CurrencyPolicy``."""
    p = Policy(currency_policy=CurrencyPolicy.ALLOW_FX)
    assert p.currency_policy is CurrencyPolicy.ALLOW_FX


# --- Policy validation ------------------------------------------------------


def test_policy_rejects_confidence_floor_above_one() -> None:
    """``Policy(confidence_floor=1.5)`` raises ValueError."""
    with pytest.raises(ValueError, match="confidence_floor must be in"):
        Policy(confidence_floor=1.5)


def test_policy_rejects_confidence_floor_below_zero() -> None:
    """``Policy(confidence_floor=-0.1)`` raises ValueError."""
    with pytest.raises(ValueError, match="confidence_floor must be in"):
        Policy(confidence_floor=-0.1)


def test_policy_accepts_confidence_floor_zero() -> None:
    """``Policy(confidence_floor=0.0)`` is valid (boundary)."""
    p = Policy(confidence_floor=0.0)
    assert p.confidence_floor == 0.0


def test_policy_accepts_confidence_floor_one() -> None:
    """``Policy(confidence_floor=1.0)`` is valid (boundary)."""
    p = Policy(confidence_floor=1.0)
    assert p.confidence_floor == 1.0


def test_policy_is_frozen() -> None:
    """``Policy`` is frozen (attrs.frozen)."""
    p = Policy()
    with pytest.raises(BaseException):  # FrozenInstanceError  # noqa: B017
        p.allow_remote_inference = False  # type: ignore[misc]
