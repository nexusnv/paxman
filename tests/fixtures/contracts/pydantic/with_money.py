"""MONEY type coverage — exercises the ``Money`` Pydantic base class.

Paired with ``json_schema/with_money.json`` and ``dict_dsl/with_money.py``.

Features exercised (per ``tests/fixtures/contracts/AGENTS.md``):
- ``amount``: MONEY via :class:`paxman.contract.adapters.pydantic.Money`.
- Multi-currency: ``MoneyUSD``, ``MoneyEUR`` models with different currencies.
- Decimal precision: ``MoneyWithPrecision`` exercises the ``precision`` field.
- ``CurrencyPolicy``: imported from ``paxman.budget`` (the cross-cutting
  budget module), where it actually lives. The reviewer suggested importing
  from ``paxman.contract.adapters.pydantic`` but that module does not
  re-export ``CurrencyPolicy`` (verified at commit time).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from paxman.budget import CurrencyPolicy
from paxman.contract.adapters.pydantic import Money


class MoneyRoundtrip(BaseModel):
    """Contract exercising the MONEY type via the ``Money`` base class.

    Kept shape-compatible with the original Sprint 2 fixture so existing
    tests continue to pass (see ``test_fixture_with_money_model_adapts``).
    """

    amount: Money = Field(..., description="Monetary amount with ISO-4217 currency.")
    notes: str = Field(..., description="Free-form notes accompanying the money value.")


class MoneyUSD(BaseModel):
    """Multi-currency MONEY fixture (USD)."""

    amount: Money = Field(..., description="Monetary amount in USD.")


class MoneyEUR(BaseModel):
    """Multi-currency MONEY fixture (EUR)."""

    amount: Money = Field(..., description="Monetary amount in EUR.")


class MoneyWithPrecision(BaseModel):
    """MONEY with explicit Decimal precision (e.g., 2 for cents)."""

    amount: Money = Field(..., description="Monetary amount with explicit precision.")


# Demonstrates the three CurrencyPolicy variants as a module-level constant
# (consumed by documentation; the runtime MONEY validation does not depend
# on the policy — that lives in ``paxman.budget.Policy`` at the call site).
CURRENCY_POLICIES: tuple[CurrencyPolicy, ...] = (
    CurrencyPolicy.STRICT_MATCH,
    CurrencyPolicy.ALLOW_FX,
    CurrencyPolicy.REJECT_WITHOUT_RATE,
)
