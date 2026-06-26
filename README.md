# Paxman

> **Contract-driven deterministic normalization engine for Python.**

[![CI](https://github.com/nexusnv/paxman/actions/workflows/ci.yml/badge.svg)](https://github.com/nexusnv/paxman/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)](./pyproject.toml)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://docs.astral.sh/ruff/)
[![Type checked: mypy --strict](https://img.shields.io/badge/type%20checked-mypy%20--strict-blue)](https://mypy.readthedocs.io/)
[![py.typed](https://img.shields.io/badge/py--typed-yes-success)](https://peps.python.org/pep-0561/)

Paxman transforms arbitrary input (PDFs, scans, emails, spreadsheets, APIs, free text) into **evidence-backed, replayable** normalized artifacts conforming to caller-supplied contracts (Pydantic, JSON Schema, OpenAPI, or a built-in Dict DSL).

```python
from decimal import Decimal
from pydantic import BaseModel

import paxman

# IMPORTANT: import the adapter(s) you need so they self-register.
# Pydantic is an optional extra; the core package ships the registry
# but not the adapters themselves.
import paxman.contract.adapters.pydantic  # noqa: F401  (triggers self-registration)
import paxman.contract.adapters.dict_dsl  # noqa: F401


# Caller-owned contract (Pydantic example)
class Invoice(BaseModel):
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

If you need any of these, **wrap Paxman from the outside** (see
[§When to use Paxman vs When to wrap Paxman](#when-to-use-paxman-vs-when-to-wrap-paxman)
below).

## When to use Paxman vs When to wrap Paxman

Paxman is a **library** that produces an evidence-backed, replayable
normalized artifact. Use Paxman directly when your problem is one of
the following:

- You have **arbitrary input** (text, PDF, JSON, HTML) that needs to
  be normalized against a **caller-owned contract** (Pydantic / JSON
  Schema / OpenAPI / Dict DSL).
- You need **evidence-backed** normalization — every resolved value
  carries provenance, and every step is auditable.
- You need **replay** — the ability to rehydrate a stored artifact
  without re-running the pipeline.
- You need **field-centric confidence** — different fields can have
  different confidence, and the Reconciler grades the candidates
  with a single, fixed rubric.
- You are integrating into a **service** (or a SaaS) that needs
  auditable normalization without owning a normalization engine.

**Wrap Paxman from the outside** when your problem is one of the
following:

- You need a **workflow engine** (DAG of long-running tasks, retries,
  human-in-the-loop, …). Wrap Paxman in a workflow engine.
- You need a **general-purpose agent framework** (multi-turn
  reasoning, tool use, planning across many turns). Wrap Paxman
  behind an agent's tool call.
- You need a **RAG framework** (vector search, retrieval, ranking).
  Wrap Paxman behind a RAG pipeline; the contract becomes the
  structured extraction step.
- You need a **persistence layer** (database, ORM, migration
  tooling). Wrap Paxman in a service that stores the artifact.
- You need a **schema registry** (catalog of contracts, versioning
  of contracts, governance). Wrap Paxman in a registry.
- You need a **standard library** (general-purpose data
  transformation). Paxman is opinionated about evidence, replay,
  and confidence; it is not a general-purpose library.
- You need a **domain ontology** (taxonomy, classification,
  knowledge graph). Wrap Paxman behind an ontology lookup.

In short: **Paxman is the normalization step in a larger system.** It
is not the larger system. If you find yourself wanting to add
workflow, persistence, or agentic features to Paxman itself, that
is a signal to wrap Paxman from the outside.

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
| **[docs/concepts/](./docs/concepts/)** | Conceptual docs (contracts, capabilities, planning, reconciliation, replay, MIGRATION_GUIDE). |
| **[docs/howto/](./docs/howto/)** | Quick-start how-tos (add adapter, add capability, add inference provider, replay artifact). |
| **[CONTRIBUTING.md](./CONTRIBUTING.md)** | Contribution workflow + ADR-driven process. |
| **[CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md)** | Community standards (Contributor Covenant v2.1). |
| **[CHANGELOG.md](./CHANGELOG.md)** | Release notes. |

## Quickstart (5 minutes)

> **Note:** Paxman V1 is in pre-release. The quickstart below is
> verified end-to-end in CI (see `.github/workflows/ci.yml`). For a
> full migration walkthrough (e.g. from LlamaIndex, LangChain, or a
> hand-rolled pipeline), see
> [`docs/concepts/MIGRATION_GUIDE.md`](./docs/concepts/MIGRATION_GUIDE.md).

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

# IMPORTANT: import the adapter(s) you need so they self-register.
# Pydantic is an optional extra; the core package ships the registry
# but not the adapters themselves.
import paxman.contract.adapters.pydantic  # noqa: F401
import paxman.contract.adapters.dict_dsl  # noqa: F401

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

- **v0.0.0 (Sprint 6):** Full pipeline — contract adaptation, planning, execution, reconciliation, artifact, and public API (`paxman.normalize()`, `paxman.replay()`).
- **v0.0.0 + Sprint 7:** `paxman.testing` (Hypothesis strategies), golden artifacts, end-to-end integration tests, per-subsystem coverage thresholds. **In progress.**
- **v0.0.0 + Sprint 8:** Documentation site (`docs/concepts/`, `docs/howto/`), community files (`CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`), CI hardening (pyright, interrogate, bandit, pip-audit), 9-check `make ci`. **In progress.**
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

This runs, in order: `install-frozen → lint → format-check → typecheck → typecheck-pyright → imports → docs-check → security → test-cov`. **All 9 checks** must pass before opening a PR. Each check is also runnable individually (e.g. `make lint`, `make typecheck`, `make docs-check`, `make security`).

## Project structure

```text
paxman/
├── src/paxman/              # the package (src-layout)
│   ├── __init__.py          # exposes __version__ + public API
│   ├── py.typed             # PEP 561 marker
│   ├── errors.py            # PaxmanError hierarchy
│   ├── types.py             # Status, ConfidenceBand, FieldType enums
│   ├── protocols.py         # internal Protocol definitions
│   ├── versioning.py        # version constants and helpers
│   ├── logging.py           # structlog factory (no timestamps in replay)
│   ├── budget.py            # Budget, Policy, CurrencyPolicy
│   ├── clock.py             # injectable Clock + FakeClock
│   ├── ids.py               # prefixed ID helpers
│   ├── serialization.py     # stable JSON encoder (RFC 8785-style)
│   ├── contract/            # adapter + validation (4 formats → CanonicalContract)
│   ├── planner/             # rule-based field-centric planning
│   ├── capabilities/        # 5 V1 capabilities (text/regex/lookup/inference/validation)
│   ├── executor/            # sequential execution + budget tracking
│   ├── reconciler/          # truth resolution + confidence + MONEY
│   ├── artifact/            # ExecutionArtifact + replay hash + diagnostics
│   ├── api/                 # public API (normalize, replay, register_*)
│   └── testing/             # public Hypothesis strategies (paxman.testing)
├── tests/                   # pytest test suite (unit / property / integration / public_api)
├── docs/                    # design specs, ADRs, sprint plan, concepts, howtos
├── pyproject.toml           # PEP 621 metadata + tooling config
├── Makefile                 # `make ci`, `make test`, `make build`, …
├── .pre-commit-config.yaml
├── .github/                 # workflows + issue/PR templates
├── LICENSE                  # MIT (per ADR-0008)
├── CONTRIBUTING.md          # contribution workflow + ADR-driven process
├── CODE_OF_CONDUCT.md       # Contributor Covenant v2.1
└── CHANGELOG.md             # release notes
```


See [V1_ACCEPTANCE_CRITERIA.md](./V1_ACCEPTANCE_CRITERIA.md) for the full definition of done.

## Contributing

We welcome contributions of all sizes — from typo fixes to new
subsystems. See [CONTRIBUTING.md](./CONTRIBUTING.md) for the
contribution workflow and the ADR-driven process.

For local development setup, see [DEVELOPMENT.md](./DEVELOPMENT.md).
For extension guides (adding a new contract adapter, capability, or
inference provider), see [EXTENDING.md](./EXTENDING.md).

Significant architectural changes require an ADR; see
[docs/adr/README.md](./docs/adr/README.md). Community standards are
in [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md).

## License

MIT. See [LICENSE](./LICENSE). Per [ADR-0008](./docs/adr/0008-license-decision.md),
MIT is the chosen license for V1. Apache-2.0 is the documented
alternative if patent concerns emerge (see
[docs/specs/license-decision.md](./docs/specs/license-decision.md)
for the full trade-off analysis).

## See also

- [PRD.md](./PRD.md) — start here for the product vision
- [GLOSSARY.md](./GLOSSARY.md) — vocabulary
- [REPLAY_AND_DETERMINISM.md](./REPLAY_AND_DETERMINISM.md) — replay model
- [SECURITY.md](./SECURITY.md) — threat model
- [Paxman Website](https://paxman.nexusnv.net) — the official project site
- [NexusNV Website](https://nexusnv.net) — the people behind Paxman