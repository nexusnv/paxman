"""Smoke tests verifying imports and basic model behaviour."""

from __future__ import annotations


def test_import_app() -> None:
    """The FastAPI app can be imported."""
    from backend_service.app import app

    assert app.title == "Paxman Normalization Service"


def test_import_contracts() -> None:
    """Contract models and registry can be imported."""
    from backend_service.contracts import CONTRACTS, Invoice

    assert "Invoice" in CONTRACTS
    assert CONTRACTS["Invoice"] is Invoice


def test_invoice_model_serializes() -> None:
    """Invoice Pydantic model round-trips through dict/JSON."""
    from decimal import Decimal

    from backend_service.contracts import Invoice, LineItem

    invoice = Invoice(
        supplier_name="ACME Corp",
        total_amount=Decimal("1234.56"),
        currency_code="USD",
        line_items=[
            LineItem(description="Widget", quantity=2, unit_price=Decimal("500.00")),
        ],
    )
    data = invoice.model_dump()
    assert data["supplier_name"] == "ACME Corp"
    assert data["total_amount"] == Decimal("1234.56")

    restored = Invoice.model_validate(data)
    assert restored == invoice
