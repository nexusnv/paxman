"""Contract definitions for the AI agent ingest example."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class ExtractedDocument(BaseModel):
    """A contract for normalized document extraction."""

    document_type: str = Field(..., description="Type of document (invoice, receipt, etc.)")
    vendor_name: str = Field(..., description="The vendor or supplier name")
    total_amount: Decimal = Field(..., description="Total amount")
    currency_code: str = Field(..., description="ISO-4217 currency code")
    confidence_notes: str = Field(default="", description="Notes about extraction confidence")


CONTRACTS: dict[str, type[BaseModel]] = {
    "ExtractedDocument": ExtractedDocument,
}
