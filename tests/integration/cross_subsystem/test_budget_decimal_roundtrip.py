"""Roundtrip: ``Budget(max_total_cost_usd=Decimal)`` and ``Budget(max_total_cost_usd=float)`` produce the same artifact.

Per [ADR-0010](../../adr/0010-budget-money-decimal.md), the cost pipeline
switched from ``float`` to ``Decimal`` per the project's
``"MONEY is Decimal, never float"`` directive (ADR-0004). For backward
compatibility, the ``Budget`` constructor accepts ``float | int | Decimal``
and coerces to ``Decimal`` (via ``attrs.field(converter=_to_decimal_optional)``).

This test pins the contract:

- ``paxman.normalize(..., budget=Budget(max_total_cost_usd=0.10))`` (a
  ``float`` literal) and
- ``paxman.normalize(..., budget=Budget(max_total_cost_usd=Decimal("0.10")))``

must produce the same artifact (same fields, same statuses, same
replay_hash), because the float is coerced to ``Decimal("0.10")`` at
construction and the rest of the pipeline is type-agnostic.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

import paxman

# Trigger auto-registration.
import paxman.contract.adapters.dict_dsl
import paxman.contract.adapters.pydantic
import paxman.testing
from paxman.budget import Budget
from tests.fixtures.contracts.dict_dsl.invoice import DICT_DSL_INVOICE

pytestmark = pytest.mark.integration


_INPUT = "ACME Corp\nInvoice #1234\nTotal: $1,234.56\nDate: 2026-06-22\nCurrency: USD"


def _normalize(budget: Budget):
    return paxman.normalize(
        input_data=_INPUT,
        contract=DICT_DSL_INVOICE,
        budget=budget,
    )


def test_budget_decimal_and_float_produce_same_artifact() -> None:
    """``Budget(max_total_cost_usd=Decimal("0.10"))`` and
    ``Budget(max_total_cost_usd=0.10)`` produce byte-equal artifacts.

    Locks the backward-compat contract: the float-literal call site
    pattern (``Budget(max_total_cost_usd=0.10)``) is preserved per
    ADR-0010 §Decision Outcome.
    """
    a = _normalize(Budget(max_total_cost_usd=Decimal("0.10")))
    b = _normalize(Budget(max_total_cost_usd=0.10))

    # Same identity, same statuses, same replay hash.
    assert a.replay_hash == b.replay_hash
    assert a.status == b.status
    assert a.normalized_data == b.normalized_data
    assert a.unresolved_fields == b.unresolved_fields
    assert a.field_results == b.field_results


def test_budget_decimal_internal_type_is_decimal() -> None:
    """After construction, ``Budget.max_total_cost_usd`` is ``Decimal`` regardless of input type."""
    b_float = Budget(max_total_cost_usd=0.10)
    b_decimal = Budget(max_total_cost_usd=Decimal("0.10"))
    b_int = Budget(max_total_cost_usd=0)  # int literal, V1 boundary

    assert isinstance(b_float.max_total_cost_usd, Decimal)
    assert isinstance(b_decimal.max_total_cost_usd, Decimal)
    assert isinstance(b_int.max_total_cost_usd, Decimal)
    assert b_float.max_total_cost_usd == Decimal("0.10")
    assert b_decimal.max_total_cost_usd == Decimal("0.10")
    assert b_int.max_total_cost_usd == Decimal("0")
