# Backend Service — Paxman FastAPI Normalization Example

A minimal FastAPI service that exposes `POST /normalize` for contract-driven
normalization via `paxman.normalize()`.

## Problem statement

I'm a backend developer building a normalization service. I want to accept
arbitrary text input (invoices, quotations, free-form documents) from my API
consumers, run it through Paxman's normalization pipeline, and return structured,
evidence-backed JSON — all without writing custom parsing logic.

## Install

```bash
cd examples/backend_service
uv venv
uv pip install -e "../../[pydantic]"
uv pip install -e ".[dev]"
```

## Run

```bash
uvicorn backend_service.app:app --reload --port 8000
```

## Test

```bash
uv run pytest tests/ -v
```

## Expected output

```bash
curl -X POST http://localhost:8000/normalize \
  -H "Content-Type: application/json" \
  -d '{
    "input_data": "ACME Corp\nInvoice #1234\nTotal: $1,234.56 USD\n- Widget: 2 @ $500.00\n- Gadget: 1 @ $234.56",
    "contract_name": "Invoice"
  }'
```

```json
{
  "status": "SUCCESS",
  "normalized_data": {
    "supplier_name": "ACME Corp",
    "total_amount": "1234.56",
    "currency_code": "USD"
  },
  "unresolved_fields": [],
  "replay_hash": "a3f8...<64 hex chars>",
  "diagnostics": [...]
}
```

## What this example demonstrates

- **POST /normalize** — accepts raw text + a contract name, returns the
  Paxman `ExecutionArtifact` as JSON.
- **Pydantic contract** — the `Invoice` model in `contracts.py` is a
  caller-owned Pydantic `BaseModel`. Paxman never owns your schema.
- **Replay hash** — every response includes a deterministic `replay_hash`
  you can store and later use with `paxman.replay()` to verify integrity.
- **Unresolved fields** — fields Paxman could not resolve are listed
  explicitly; nothing is silently dropped.
- **GET /contracts** — lists registered contract names.
- **GET /healthz** — liveness probe.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/normalize` | Normalize input against a contract |
| `GET` | `/contracts` | List available contracts |
| `GET` | `/healthz` | Health check |

## Notes

- **No CORS middleware configured.** This example is designed for
  server-to-server use (e.g., another service in your backend). If you
  need to expose it to a browser, add FastAPI's `CORSMiddleware` and
  configure allowed origins.
- **No authentication.** This is a reference example. Production
  deployments should add auth (API keys, OAuth, mTLS, etc.) before
  exposing the endpoint.
