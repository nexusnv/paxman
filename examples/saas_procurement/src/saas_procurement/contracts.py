"""Sample Pydantic contracts for invoice and quotation normalization."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    """A single line item on an invoice or quotation."""

    description: str = Field(..., description="Description of the item or service.")
    quantity: int = Field(..., ge=1, description="Quantity ordered.")
    unit_price: Decimal = Field(..., description="Price per unit.")


class Invoice(BaseModel):
    """A simple invoice contract."""

    invoice_id: str = Field(..., description="Unique invoice identifier.")
    supplier_name: str = Field(..., description="The supplier's name.")
    total_amount: Decimal = Field(..., description="Total invoice amount.")
    currency_code: str = Field(..., description="ISO-4217 currency code.")
    line_items: list[LineItem] = Field(default_factory=list)


class Quotation(BaseModel):
    """A simple quotation contract."""

    quotation_id: str = Field(..., description="Unique quotation identifier.")
    vendor_name: str = Field(..., description="The vendor's name.")
    quoted_amount: Decimal = Field(..., description="Total quoted amount.")
    currency_code: str = Field(..., description="ISO-4217 currency code.")
    valid_until: str = Field(..., description="ISO-8601 date string.")


CONTRACTS: dict[str, type[BaseModel]] = {
    "Invoice": Invoice,
    "Quotation": Quotation,
}
