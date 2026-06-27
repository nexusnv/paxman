# Paxman

> **Contract-driven deterministic normalization engine for Python.**

[![CI](https://github.com/nexusnv/paxman/actions/workflows/ci.yml/badge.svg)](https://github.com/nexusnv/paxman/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/nexusnv/paxman/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)](https://github.com/nexusnv/paxman/blob/main/pyproject.toml)
[![py.typed](https://img.shields.io/badge/py--typed-yes-success)](https://peps.python.org/pep-0561/)

Paxman transforms arbitrary input (PDFs, scans, emails, spreadsheets, APIs, free text) into **evidence-backed, replayable** normalized artifacts that conform to caller-supplied contracts (Pydantic, JSON Schema, OpenAPI, or a built-in Dict DSL).

---

## What is Paxman?

Paxman is a **library** that produces an evidence-backed, replayable normalized artifact. It is the normalization step in a larger system. If you find yourself wanting workflow, persistence, or agentic features inside Paxman, that is a signal to wrap Paxman from the outside.

- **Contract-driven.** You bring the contract. Paxman doesn't own your schema.
- **Field-centric, deterministic planning.** Each required field gets its own plan.
- **Evidence-backed.** Every resolved value carries provenance and confidence.
- **Replayable.** Rehydrate the artifact without recomputation.
- **Honest.** Unresolved fields are explicit, never silent.

## Install

```bash
pip install paxman                          # core (no adapters)
pip install paxman[pydantic]                # + Pydantic adapter
pip install paxman[all]                     # + all V1 adapters
```

## 5-minute quickstart

```python
from decimal import Decimal
from pydantic import BaseModel

import paxman
import paxman.contract.adapters.pydantic  # self-registers the adapter


class LineItem(BaseModel):
    description: str
    quantity: int
    unit_price: float


class Invoice(BaseModel):
    supplier_name: str
    total_amount: float
    currency_code: str
    line_items: list[LineItem] = []


artifact = paxman.normalize(
    input_data="ACME Corp — Invoice #1234 — Total: $1,234.56 USD",
    contract=Invoice,
    budget=paxman.Budget(max_total_cost_usd=Decimal("0.10")),
)

print(artifact.status)               # Status.SUCCESS or Status.PARTIAL_SUCCESS
print(artifact.normalized_data)      # {"supplier_name": "ACME Corp", ...}
print(artifact.unresolved_fields)    # []  (or list of fields Paxman could not resolve)
print(artifact.replay_hash)          # deterministic SHA-256 signature

# Later: replay the artifact without re-running the pipeline
rehydrated = paxman.replay(artifact, contract=Invoice)
assert rehydrated == artifact  # byte-equal
```

## Where to go next

| If you want to… | Start here |
|---|---|
| Understand the mental model | [Concepts → Contracts](concepts/contracts.md) |
| Add a new contract format (e.g. Avro) | [How-to → Add a contract adapter](howto/add_adapter.md) |
| Add a new capability (e.g. table extraction) | [How-to → Add a capability](howto/add_capability.md) |
| Add a new inference provider (OpenAI, Anthropic, local) | [How-to → Add an inference provider](howto/add_inference_provider.md) |
| Replay a stored artifact | [How-to → Replay an artifact](howto/replay_artifact.md) |
| Understand why a decision was made | [Decision records (ADRs)](adr/index.md) |
| Migrate from LlamaIndex / LangChain / Unstructured | [Migration guide](concepts/MIGRATION_GUIDE.md) |
| Contribute to Paxman | [Contributing](contributing/index.md) |
| Read the v1.0.0 release notes | [Release notes v1.0.0](concepts/RELEASE_NOTES_v1.0.0.md) |

## Project links

- **Source code:** [github.com/nexusnv/paxman](https://github.com/nexusnv/paxman)
- **PyPI:** [pypi.org/project/paxman](https://pypi.org/project/paxman/)
- **Changelog:** [CHANGELOG.md on Read the Docs](https://paxman.readthedocs.io/en/latest/operations/changelog/)
- **Issue tracker:** [github.com/nexusnv/paxman/issues](https://github.com/nexusnv/paxman/issues)
- **Security disclosures:** [security policy](security/index.md)

## About

Paxman is developed by [Nexus Envision Sdn Bhd](https://nexusnv.net). Released under the [MIT License](https://github.com/nexusnv/paxman/blob/main/LICENSE).
