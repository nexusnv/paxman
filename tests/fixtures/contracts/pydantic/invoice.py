"""Canonical invoice contract — the primary happy-path Pydantic fixture.

Paired with ``json_schema/invoice.json`` and ``dict_dsl/invoice.py``.

Features exercised:
- ``supplier_name``: STRING with ``min_length`` + ``max_length`` constraints.
- ``currency``: STRING with a ``pattern`` constraint (ISO-4217 3-letter regex).
- ``total``: DECIMAL with a ``ge=0`` (min_value, inclusive) constraint.
- ``paid``: BOOLEAN with a default (``False``) — exercises optional fields.
- ``invoice_date``: DATE — ``datetime.date`` maps to ``FieldType.DATE``.
  V1 represents dates as ISO 8601 strings in the canonical model.
- ``line_items``: ARRAY of nested ``LineItem`` objects (OBJECT via BaseModel).
"""

from __future__ import annotations

import datetime

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    """A single line item on an invoice."""

    description: str = Field(..., description="Description of the goods or service.")
    quantity: int = Field(..., description="Quantity ordered.", ge=0)
    unit_price: float = Field(..., description="Per-unit price in the invoice currency.", ge=0)


class Invoice(BaseModel):
    """Canonical invoice exercising STRING, DECIMAL, BOOLEAN, DATE, ARRAY, and nested OBJECT."""

    supplier_name: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Legal name of the supplier.",
    )
    currency: str = Field(
        ...,
        pattern=r"^[A-Z]{3}$",
        description="ISO-4217 currency code for the invoice.",
    )
    total: float = Field(..., ge=0, description="Total invoice amount.")
    paid: bool = Field(False, description="Whether the invoice has been paid.")
    invoice_date: datetime.date = Field(..., description="Invoice issue date (ISO 8601).")
    line_items: list[LineItem] = Field(
        default_factory=list,
        description="Individual line items on the invoice.",
    )
