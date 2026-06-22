"""MONEY type coverage — exercises the ``Money`` Pydantic base class.

Paired with ``json_schema/with_money.json`` and ``dict_dsl/with_money.py``.

Features exercised:
- ``amount``: MONEY — uses :class:`paxman.contract.adapters.pydantic.Money`,
  which the adapter detects via subclass check and maps to
  ``FieldType.MONEY``. Exercises Decimal ``amount``, ISO-4217 ``currency``,
  and optional ``precision``.
- ``notes``: STRING — a simple accompanying string field.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from paxman.contract.adapters.pydantic import Money


class MoneyRoundtrip(BaseModel):
    """Contract exercising the MONEY type via the ``Money`` base class."""

    amount: Money = Field(..., description="Monetary amount with ISO-4217 currency.")
    notes: str = Field(..., description="Free-form notes accompanying the money value.")
