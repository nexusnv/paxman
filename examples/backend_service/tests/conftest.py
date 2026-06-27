"""Shared fixtures for backend service tests."""

from __future__ import annotations

import pytest
from backend_service.app import app
from fastapi.testclient import TestClient


@pytest.fixture()
def client() -> TestClient:
    """FastAPI TestClient instance."""
    return TestClient(app)


@pytest.fixture()
def sample_invoice_text() -> str:
    """Raw invoice text for normalization testing."""
    return (
        "ACME Corp\n"
        "Invoice #1234\n"
        "Total: $1,234.56 USD\n"
        "- Widget: 2 @ $500.00\n"
        "- Gadget: 1 @ $234.56\n"
    )
