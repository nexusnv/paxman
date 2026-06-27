"""Request and response models for the FastAPI normalization service."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class NormalizeRequest(BaseModel):
    """Request body for POST /normalize."""

    input_data: str = Field(..., description="Raw text to normalize.")
    contract_name: str = Field(..., description="Name of the registered contract (e.g. 'Invoice').")


class DiagnosticsEntry(BaseModel):
    """A single diagnostic record."""

    code: str
    severity: str
    message: str


class NormalizeResponse(BaseModel):
    """Response body for POST /normalize."""

    status: str
    normalized_data: dict[str, Any]
    unresolved_fields: list[str]
    replay_hash: str
    diagnostics: list[DiagnosticsEntry]
