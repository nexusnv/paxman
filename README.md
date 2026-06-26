# Paxman

> **Contract-driven deterministic normalization engine for Python.**

Paxman transforms arbitrary input (PDFs, scans, emails, spreadsheets, APIs, free text) into **evidence-backed, replayable** normalized artifacts conforming to caller-supplied contracts (Pydantic, JSON Schema, OpenAPI, or a built-in Dict DSL).

```python
from decimal import Decimal

import paxman

# Caller-owned contract (Pydantic example)
class Invoice(paxman.BaseModel):
    supplier_name: str
    total_amount: float
    currency_code: str
    line_items: list[LineItem]

# Normalize raw input against the contract
result = paxman.normalize(
    input_data=raw_invoice_bytes,
    contract=Invoice,
    budget=paxman.Budget(max_total_cost_usd=Decimal("0.10")),  # Decimal per ADR-0004
    policy=paxman.Policy(allow_remote_inference=True),
)

# Inspect or consume
print(result.normalized_data)        # matches the Invoice shape
print(result.unresolved_fields)      # any fields Paxman could not resolve
print(result.replay_hash)            # deterministic signature for replay

# Replay later from the artifact alone
rehydrated = paxman.replay(result, contract=Invoice)
assert rehydrated == result  # byte-equal
```

## Why Paxman?

- **Contract-driven.** You bring the contract. Paxman doesn't own your schema.
- **Field-centric, deterministic planning.** Each required field gets its own plan.
- **Evidence-backed.** Every resolved value carries provenance and confidence.
- **Replayable.** Rehydrate the artifact without recomputation.
- **Honest.** Unresolved fields are explicit, never silent.

## What Paxman is NOT

- Not a workflow engine.
- Not a general-purpose agent framework.
- Not a RAG framework.
- Not a persistence layer.
- Not a schema registry.
- Not a standard library.
- Not a domain ontology.

If you need any of these, wrap Paxman from the outside.

## Install

```bash
pip install paxman                          # core (no adapters)
pip install paxman[pydantic]                # + Pydantic adapter
pip install paxman[all]                     # + all V1 adapters
```

Paxman is in **pre-release** (v0.x). Public API may change between minor versions until 1.0.

## Documentation

| Doc | Purpose |
|---|---|
| **[PRD.md](./PRD.md)** | Product vision, philosophy, V1 success metrics and acceptance criteria. |
| **[ARCHITECTURE.md](./ARCHITECTURE.md)** | Subsystem design, sequence diagram, error model, versioning, observability. |
| **[PACKAGE_STRUCTURE.md](./PACKAGE_STRUCTURE.md)** | Module layout, dependency DAG, public/private API split, packaging. |
| **[GLOSSARY.md](./GLOSSARY.md)** | Single source of truth for Paxman vocabulary. |
| **[V1_ACCEPTANCE_CRITERIA.md](./V1_ACCEPTANCE_CRITERIA.md)** | Definition of done for the 1.0 release. |
| **[REPLAY_AND_DETERMINISM.md](./REPLAY_AND_DETERMINISM.md)** | Deep dive on replay and determinism. |
| **[SECURITY.md](./SECURITY.md)** | Threat model, PII handling, provider secrets, vulnerability reporting. |
| **[TESTING_STRATEGY.md](./TESTING_STRATEGY.md)** | Test seams, property tests, replay tests, fixtures. |
| **[docs/TEST_DATA.md](./docs/TEST_DATA.md)** | Test data policy, dataset catalog, licensing rules. |
| **[DEVELOPMENT.md](./DEVELOPMENT.md)** | Local dev setup, common tasks, release process. |
| **[EXTENDING.md](./EXTENDING.md)** | How to add a new contract adapter, capability, or inference provider. |
| **[DEPENDENCIES.md](./DEPENDENCIES.md)** | Core vs optional dependencies, packaging policy. |
| **[docs/adr/](./docs/adr/)** | Architecture Decision Records. |

## Quickstart (5 minutes)

### 1. Install

```bash
pip install paxman[pydantic]
```

### 2. Define a contract (Pydantic)

```python
from pydantic import BaseModel, Field


class LineItem(BaseModel):
    description: str
    quantity: int
    unit_price: float


class Invoice(BaseModel):
    supplier_name: str = Field(..., description="The supplier's name.")
    total_amount: float = Field(..., description="Total invoice amount.")
    currency_code: str = Field(..., description="ISO-4217 currency code.")
    line_items: list[LineItem] = Field(default_factory=list)
```

### 3. Normalize raw input

```python
import paxman

raw_invoice = """
ACME Corp
Invoice #1234
Total: $1,234.56 USD
- Widget: 2 @ $500.00
- Gadget: 1 @ $234.56
"""

artifact = paxman.normalize(
    input_data=raw_invoice,
    contract=Invoice,
)

print(artifact.status)               # Status.SUCCESS or Status.PARTIAL_SUCCESS
print(artifact.normalized_data)      # {"supplier_name": "ACME Corp", ...}
print(artifact.unresolved_fields)    # []  (or list of fields Paxman could not resolve)
print(artifact.replay_hash)          # "a3f8..."
```

### 4. Replay

```python
# Later, with just the artifact and the contract
rehydrated = paxman.replay(artifact, contract=Invoice)
assert rehydrated == artifact  # byte-equal
```

## Use cases

Paxman is designed for:

- **Invoice/quotation/procurement normalization** — compare offers across suppliers and currencies.
- **Agentic ingestion flows** — auditable, evidence-backed extraction for RAG or agent pipelines.
- **Document understanding services** — wrap Paxman inside a SaaS without giving up replay or evidence.
- **Multi-source data pipelines** — normalize email, OCR, CSV, and API inputs into one canonical schema.

See [PRD.md §7 Primary Use Cases](./PRD.md) for detailed examples.

## Status

- **v0.0.0 (Sprint 6):** Full pipeline — contract adaptation, planning, execution, reconciliation, artifact, and public API (`paxman.normalize()`, `paxman.replay()`). **In progress.**
- **v0.1.0 (initial preview):** planner + one adapter + one capability work end-to-end. (Pending.)
- **v0.5.0 (feature-complete beta):** 80% of V1 features. (Pending.)
- **1.0.0:** All V1 acceptance criteria met. (Pending.)

## Install (developer setup, Sprint 1)

Paxman uses [`uv`](https://docs.astral.sh/uv/) for package management. The first preview is not published to PyPI yet; developers install the project from a working tree.

```bash
# Clone the repository
git clone https://github.com/nexusnv/paxman.git
cd paxman

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install the package + all dev dependencies (editable)
uv sync --all-extras --dev

# Verify the install
uv run python -c "import paxman; print(f'paxman {paxman.__version__}')"
```

Expected output: `paxman 0.0.0`.

## Local CI

Run the full local-CI pipeline (the same checks run on GitHub Actions):

```bash
make ci
```

This runs, in order: `install-frozen → lint → format-check → typecheck → typecheck-pyright → imports → test-cov`. All checks must pass before opening a PR.

## Project structure

```text
paxman/
├── src/paxman/              # the package (src-layout)
│   ├── __init__.py          # exposes __version__
│   ├── py.typed             # PEP 561 marker
│   ├── errors.py            # 17-class PaxmanError hierarchy
│   ├── types.py             # Status, ConfidenceBand, FieldType enums
│   ├── protocols.py         # internal Protocol definitions
│   ├── versioning.py        # version constants and helpers
│   ├── logging.py           # structlog factory (no timestamps in replay)
│   ├── budget.py            # Budget, Policy, CurrencyPolicy
│   ├── clock.py             # injectable Clock + FakeClock
│   ├── ids.py               # prefixed ID helpers
│   ├── serialization.py     # stable JSON encoder (RFC 8785-style)
│   ├── contract/            # (empty; Sprint 2)
│   ├── planner/             # (empty; Sprint 3)
│   ├── capabilities/        # (empty; Sprints 3-4)
│   ├── executor/            # (empty; Sprint 4)
│   ├── reconciler/          # (empty; Sprint 5)
│   ├── artifact/            # (empty; Sprint 6)
│   └── api/                 # (empty; Sprint 6)
├── tests/                   # pytest test suite
├── docs/                    # design specs, ADRs, sprint plan
├── pyproject.toml           # PEP 621 metadata + tooling config
├── Makefile                 # `make ci`, `make test`, `make build`, …
├── .pre-commit-config.yaml
├── LICENSE                  # MIT (per ADR-0008)
└── CHANGELOG.md
```


See [V1_ACCEPTANCE_CRITERIA.md](./V1_ACCEPTANCE_CRITERIA.md) for the full definition of done.

## Contributing

See [DEVELOPMENT.md](./DEVELOPMENT.md) for the development workflow and [EXTENDING.md](./EXTENDING.md) for the extension guides.

Significant architectural changes require an ADR; see [docs/adr/README.md](./docs/adr/README.md).

## License

MIT (or Apache-2.0 — final TBD by the team). See `LICENSE`.

## See also

- [PRD.md](./PRD.md) — start here for the product vision
- [GLOSSARY.md](./GLOSSARY.md) — vocabulary
- [REPLAY_AND_DETERMINISM.md](./REPLAY_AND_DETERMINISM.md) — replay model
- [SECURITY.md](./SECURITY.md) — threat model
- [DeepWiki](https://deepwiki/nexusnv/paxman) - Discover Paxman with AI Q&A
- [Paxman Website](https://paxman.nexusnv.net) - Visit out website
- [NexusNV Website](https://nexusnv.net) - The people behind Paxman