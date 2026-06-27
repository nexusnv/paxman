"""Shared fixtures for the AI agent ingest tests."""

from __future__ import annotations

import pytest


@pytest.fixture()
def sample_document_text() -> str:
    """A sample invoice document for testing."""
    return """
    ACME Corp
    Invoice #INV-2026-0042
    Total: $1,234.56 USD
    """
