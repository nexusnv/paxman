"""FastAPI application for the Paxman normalization service."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

import paxman
import paxman.contract.adapters.pydantic  # side-effect: registers Pydantic adapter
from backend_service.contracts import CONTRACTS
from backend_service.models import (
    DiagnosticsEntry,
    NormalizeRequest,
    NormalizeResponse,
)

app = FastAPI(
    title="Paxman Normalization Service",
    description="Minimal FastAPI reference example for paxman.normalize().",
    version="0.1.0",
)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@app.get("/contracts")
def list_contracts() -> dict[str, list[str]]:
    """Return the list of available contract names."""
    return {"contracts": sorted(CONTRACTS.keys())}


@app.post("/normalize", response_model=NormalizeResponse)
def normalize_endpoint(request: NormalizeRequest) -> NormalizeResponse:
    """Normalize raw input against a registered contract.

    Args:
        request: The normalization request containing input data and
            contract name.

    Returns:
        A NormalizeResponse with the resolved data, unresolved fields,
        replay hash, and diagnostics.

    Raises:
        HTTPException: 404 if the contract name is unknown.
    """
    contract_cls = CONTRACTS.get(request.contract_name)
    if contract_cls is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown contract: {request.contract_name!r}. "
            f"Available: {sorted(CONTRACTS.keys())}",
        )

    artifact = paxman.normalize(
        input_data=request.input_data,
        contract=contract_cls,
    )

    diagnostics = [
        DiagnosticsEntry(
            code=d.code.value if hasattr(d.code, "value") else str(d.code),
            severity=d.severity.value if hasattr(d.severity, "value") else str(d.severity),
            message=d.message,
        )
        for d in artifact.diagnostics
    ]

    return NormalizeResponse(
        status=artifact.status.value,
        normalized_data=artifact.normalized_data,
        unresolved_fields=artifact.unresolved_fields,
        replay_hash=artifact.replay_hash,
        diagnostics=diagnostics,
    )
