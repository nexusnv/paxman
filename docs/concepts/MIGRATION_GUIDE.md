# Migration Guide — Moving to Paxman

> **Status:** Skeleton (per Sprint 8 D8.10). This document is a
> high-level map of how to migrate from common "ad-hoc normalization"
> patterns to Paxman. It is intentionally a **skeleton**; the full
> guide will be filled in during V2.
> **Audience:** Engineers and teams considering Paxman for an
> existing normalization pipeline.
> **Related docs:** [README.md](../index.md), [PRD.md](https://github.com/nexusnv/paxman-wiki/blob/main/Internal-Development/PRD.md)
> (product vision), [docs/concepts/contracts.md](../concepts/contracts.md)
> (what a contract is), [docs/concepts/replay.md](../concepts/replay.md).

This document is a **migration scaffold** for users moving from
ad-hoc normalization (regex + LLM + cleanup, document parsers, …)
to Paxman. It outlines the typical migration shape and points at
the relevant concepts and how-tos. The full guide with worked
examples is V2.

---

## 1. Why migrate to Paxman?

If you are doing any of the following today, Paxman is designed to
replace the ad-hoc solution with a structured, replayable, evidence-backed
pipeline:

| Ad-hoc pattern | Paxman equivalent |
|---|---|
| "Run a regex, then an LLM, then a cleanup script" | The Planner synthesizes the chain; the Executor runs it. |
| "Hand-roll confidence for each candidate" | The Reconciler assigns confidence (per [ADR-0005](../adr/0005-confidence-ownership.md)). |
| "Manually track which step produced which value" | The artifact carries evidence references. |
| "Re-run the whole pipeline to verify a result" | `paxman.replay()` rehydrates the artifact without recomputation. |
| "Pick the cheapest path per field by hand" | The Planner's heuristic chain picks the cheapest sufficient path. |

If you need any of the things Paxman is **not** (a workflow engine,
an agent framework, a RAG framework, a persistence layer, a schema
registry, a domain ontology), **wrap Paxman from the outside** —
do not migrate to Paxman. See
[README.md §What Paxman is NOT](../index.md).

---

## 2. The migration shape

A typical migration has five steps:

### 2.1 Identify the contract

The first step is to **identify the contract**: the data shape
your downstream system expects. This may be a Pydantic model, a
JSON Schema, a database schema, or a domain-specific format.

```python
from pydantic import BaseModel, Field


class Invoice(BaseModel):
    supplier_name: str = Field(..., description="The supplier's name.")
    total_amount: float = Field(..., description="Total invoice amount.")
    currency_code: str = Field(..., description="ISO-4217 currency code.")
```

This is the contract. It is the **single source of truth** for
what Paxman produces.

### 2.2 Identify the input

The second step is to **identify the input**: the raw bytes, text,
PDF, or structured document Paxman will normalize. Paxman accepts
`str` or `bytes`; the executor's `text_extraction` capability
handles `text/plain` and `text/html` (PDF/OCR is V2).

### 2.3 Identify the budget and policy

The third step is to **identify the budget and policy** — the
constraints Paxman must respect. Typical defaults:

```python
import paxman
from decimal import Decimal

budget = paxman.Budget(max_total_cost_usd=Decimal("0.10"))
policy = paxman.Policy(
    allow_remote_inference=True,  # set False to disable remote inference
    unresolved_acceptable=False,  # set True to accept partial results
)
```

### 2.4 Call `paxman.normalize()`

The fourth step is to **call `paxman.normalize()`**:

```python
artifact = paxman.normalize(
    input_data=raw_invoice_bytes,
    contract=Invoice,
    budget=budget,
    policy=policy,
)
```

`artifact.status` is one of:

- `Status.SUCCESS` — every required field is resolved.
- `Status.PARTIAL_SUCCESS` — at least one optional field is unresolved.
- `Status.UNRESOLVED` — at least one required field is unresolved.
- `Status.INVALID_CONTRACT` — the contract failed validation.
- `Status.EXECUTION_FAILED` — an unrecoverable error occurred.

`artifact.normalized_data` is the contract-shaped result. If the
status is not `SUCCESS`, check `artifact.unresolved_fields` and
`artifact.diagnostics` for what went wrong.

### 2.5 Store the artifact (if you need replay)

The fifth step is to **store the artifact** if you need replay:

```python
import json

payload = json.dumps(artifact.to_dict(), sort_keys=True, separators=(",", ":"))
# Store `payload` somewhere; Paxman does not store artifacts.
```

Later, with the same contract:

```python
artifact = ExecutionArtifact.from_dict(json.loads(payload))
rehydrated = paxman.replay(artifact, contract=Invoice)
assert rehydrated == artifact  # byte-equal
```

---

## 3. Common migration patterns

### 3.1 From "regex + LLM" to Paxman

If you currently run a regex pass followed by an LLM pass for
fallback:

- The **regex** becomes a `regex_extraction` capability invocation.
- The **LLM fallback** becomes an `inference` capability invocation.
- The **hand-rolled merge** becomes the Reconciler's merge logic.
- The **hand-rolled confidence** becomes the Reconciler's
  `assign_confidence` rubric (per
  [ADR-0005](../adr/0005-confidence-ownership.md)).

The Paxman plan synthesizes the chain automatically; the executor
runs it sequentially (per [ADR-0006](../adr/0006-sequential-execution-v1.md)).

### 3.2 From "document parser" to Paxman

If you currently use a document parser (e.g. Tika, Unstructured,
LlamaParse) to produce structured output:

- The **parser** becomes the input to `paxman.normalize()` (you
  pre-process the document, then pass the text/JSON to Paxman).
- The **structured schema** becomes the contract (Pydantic / JSON
  Schema / Dict DSL).
- The **hand-rolled cleanup** becomes the Reconciler's merge logic.
- The **hand-rolled confidence** becomes the Reconciler's rubric.

If you are using the parser to produce JSON Schema, you may not
need Paxman at all — Paxman is for cases where you need
evidence-backed, replayable normalization with confidence.

### 3.3 From "agent framework" to Paxman

If you currently use an agent framework (LangChain, LlamaIndex,
CrewAI) to extract structured data from text:

- The **agent prompt + tool calls** become capability invocations
  on a single field's plan chain.
- The **agent's hand-rolled confidence** becomes the Reconciler's
  rubric.
- The **agent's "re-run to verify"** becomes `paxman.replay()`.

If you need the **agentic** part (multi-step reasoning, tool use,
planning across many turns), wrap Paxman from the outside. Paxman
is not an agent framework.

### 3.4 From "schema validation" to Paxman

If you currently use a schema validator (Pydantic, JSON Schema,
Cerberus) to validate parsed output:

- The **schema** becomes the contract.
- The **validator** becomes the Reconciler's validation step.
- The **"missing fields → error"** logic becomes the artifact's
  `unresolved_fields` list.

If you do not need evidence, replay, or confidence, you may not
need Paxman at all — a schema validator is simpler.

---

## 4. What stays the same

When you migrate to Paxman, these things stay the same:

- **Your domain model.** Paxman is contract-driven; you keep your
  Pydantic / JSON Schema / OpenAPI / Dict DSL contract.
- **Your input format.** Paxman accepts `str` and `bytes`; you
  pre-process the input as before.
- **Your storage layer.** Paxman does not store artifacts; you keep
  your database / S3 / filesystem.

---

## 5. What changes

When you migrate to Paxman, these things change:

- **No more hand-rolled merge logic.** The Reconciler merges
  candidates.
- **No more hand-rolled confidence.** The Reconciler assigns
  confidence (one rubric, one scale).
- **No more hand-rolled replay.** `paxman.replay()` rehydrates the
  artifact.
- **No more hand-rolled capability registry.** The Planner picks
  the cheapest sufficient chain.
- **A small public API surface** — `paxman.normalize()` and
  `paxman.replay()` are the only two functions you need.

---

## 6. Worked example: regex + LLM → Paxman

Suppose you currently have:

```python
# Hand-rolled extraction pipeline
def extract_invoice(raw_text: str) -> dict:
    # Step 1: regex
    supplier = re.search(r"Supplier:\s*(\S+)", raw_text)
    supplier_name = supplier.group(1) if supplier else None

    # Step 2: LLM fallback
    if not supplier_name:
        supplier_name = llm_call(f"Extract supplier name from: {raw_text}")

    # Step 3: hand-rolled confidence
    confidence = 0.95 if supplier else 0.7

    return {"supplier_name": supplier_name, "confidence": confidence}
```

The Paxman equivalent:

```python
import paxman
from pydantic import BaseModel, Field


class Invoice(BaseModel):
    supplier_name: str = Field(..., description="The supplier's name.")


artifact = paxman.normalize(
    input_data=raw_text,
    contract=Invoice,
)

if "supplier_name" in artifact.normalized_data:
    field = artifact.field_results["supplier_name"]
    print(field.value, field.confidence, field.confidence_band)
```

The Paxman plan synthesizes the chain (`regex_extraction` →
`inference` fallback), the Reconciler assigns confidence
deterministically, and the artifact carries the evidence. To
re-verify without re-running, store the artifact and call
`paxman.replay(artifact, contract=Invoice)`.

---

## 7. V2 roadmap for this guide

The full migration guide (V2) will include:

- **Migrating from LlamaIndex** — concrete example with a LlamaIndex
  pipeline.
- **Migrating from LangChain** — concrete example with a LangChain
  `Chain`.
- **Migrating from Unstructured** — concrete example with an
  Unstructured document parser.
- **Migrating from a hand-rolled JSON Schema validator** — concrete
  example with a Cerberus or jsonschema pipeline.
- **Side-by-side benchmarks** — Paxman vs the ad-hoc equivalent on
  the same inputs.
- **Cost comparison** — Paxman vs the ad-hoc equivalent (LLM API
  cost, latency).

If you have a specific migration in mind, open an issue on
[GitHub](https://github.com/nexusnv/paxman/issues) and we will
prioritize the worked example.

---

## 8. See also

- [README.md](../index.md) — what Paxman is and is not.
- [docs/concepts/contracts.md](../concepts/contracts.md) — the
  contract model.
- [docs/concepts/planning.md](../concepts/planning.md) — the
  planner.
- [docs/concepts/capabilities.md](../concepts/capabilities.md) —
  the capability model.
- [docs/concepts/reconciliation.md](../concepts/reconciliation.md) —
  the Reconciler.
- [docs/concepts/replay.md](../concepts/replay.md) — replay.
- [EXTENDING.md](../reference/extending.md) — adding custom adapters,
  capabilities, and providers.
