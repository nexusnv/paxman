"""Sample Pydantic contracts for the backend service example."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    """A single line item on an invoice."""

    description: str = Field(..., description="Description of the item or service.")
    quantity: int = Field(..., ge=1, description="Quantity ordered.")
    unit_price: Decimal = Field(..., description="Price per unit.")


class Invoice(BaseModel):
    """A simple invoice contract."""

    supplier_name: str = Field(..., description="The supplier's name.")
    total_amount: Decimal = Field(..., description="Total invoice amount.")
    currency_code: str = Field(..., description="ISO-4217 currency code.")
    line_items: list[LineItem] = Field(default_factory=list)


CONTRACTS: dict[str, type[BaseModel]] = {
    "Invoice": Invoice,
}
