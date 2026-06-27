"""Endpoint tests for the FastAPI normalization service."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.deterministic


def test_healthz(client: TestClient) -> None:
    """GET /healthz returns 200 with status ok."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_contracts(client: TestClient) -> None:
    """GET /contracts returns the list of available contract names."""
    response = client.get("/contracts")
    assert response.status_code == 200
    body = response.json()
    assert "contracts" in body
    assert "Invoice" in body["contracts"]


def test_normalize_invoice(client: TestClient, sample_invoice_text: str) -> None:
    """POST /normalize with Invoice contract returns 200 with proper shape."""
    response = client.post(
        "/normalize",
        json={
            "input_data": sample_invoice_text,
            "contract_name": "Invoice",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "status" in body
    assert "normalized_data" in body
    assert "unresolved_fields" in body
    assert "replay_hash" in body
    assert "diagnostics" in body
    assert isinstance(body["normalized_data"], dict)
    assert isinstance(body["unresolved_fields"], list)
    assert isinstance(body["diagnostics"], list)


def test_normalize_unknown_contract(client: TestClient, sample_invoice_text: str) -> None:
    """POST /normalize with an unknown contract name returns 404."""
    response = client.post(
        "/normalize",
        json={
            "input_data": sample_invoice_text,
            "contract_name": "NonExistent",
        },
    )
    assert response.status_code == 404
    body = response.json()
    assert "detail" in body
    assert "NonExistent" in body["detail"]


def test_normalize_invalid_input(client: TestClient) -> None:
    """POST /normalize with missing fields returns 422."""
    response = client.post("/normalize", json={})
    assert response.status_code == 422


def test_normalize_missing_contract_name(client: TestClient) -> None:
    """POST /normalize with only input_data returns 422."""
    response = client.post(
        "/normalize",
        json={"input_data": "some text"},
    )
    assert response.status_code == 422
