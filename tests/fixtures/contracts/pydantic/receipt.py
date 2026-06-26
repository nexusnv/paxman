"""Pydantic receipt contract — the receipt use case.

Paired with ``dict_dsl/receipt.py`` and ``json_schema/receipt.json``.

Exercises:

- ``merchant_name``: STRING with ``min_length`` / ``max_length`` constraints.
- ``total``: DECIMAL with ``ge=0`` (a monetary value — uses ``Decimal`` for
  precision, per the ``Decimal``-only monetary guideline).
- ``currency_code``: ENUM (Pydantic ``str``-based ``Enum``).
- ``transaction_date``: DATE.
- ``card_last4``: optional STRING with a 4-digit ``pattern`` constraint.
- ``category``: optional ENUM with a default.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CurrencyCode(str, Enum):
    """ISO-4217 currency code subset."""

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CHF = "CHF"


class ReceiptCategory(str, Enum):
    """Spending category."""

    FOOD = "FOOD"
    TRAVEL = "TRAVEL"
    OFFICE = "OFFICE"
    OTHER = "OTHER"


class Receipt(BaseModel):
    """A point-of-sale receipt."""

    merchant_name: str = Field(..., min_length=1, max_length=200)
    total: Decimal = Field(..., ge=0)
    currency_code: CurrencyCode
    transaction_date: datetime.date
    card_last4: Optional[str] = Field(default=None, pattern=r"^\d{4}$")
    category: Optional[ReceiptCategory] = ReceiptCategory.OTHER
