# Paxman 1.0.0 — Release Notes — 2026-06-27

> **Status:** Stable v1.
> **Audience:** Paxman users, contributors, and reviewers.
> **Related docs:** [CHANGELOG.md](../operations/changelog.md),
> [V1_ACCEPTANCE_CRITERIA.md](https://github.com/nexusnv/paxman-wiki/blob/main/Internal-Development/V1-acceptance-criteria.md),
> [README.md](../index.md), [PRD.md](https://github.com/nexusnv/paxman-wiki/blob/main/Internal-Development/PRD.md).

---

## TL;DR

Paxman 1.0.0 is the first production-ready release of the contract-driven
deterministic normalization engine for Python. It ships the full pipeline
(contract adaptation, planning, execution, reconciliation, artifact
construction, and replay), four contract adapters, five capabilities,
seven subsystems, a small stable public API, and three reference examples
covering backend services, AI agent ingestion, and SaaS procurement.
MONEY is a first-class Decimal type. Replay is byte-equal via SHA-256.
The 9-check CI pipeline gates every PR.

---

## What shipped

### Contract adapters (4)

- **Pydantic v2 adapter** — adapts Pydantic `BaseModel` classes to
  `CanonicalContract` and back. Covers required, optional, default,
  validator, and constraint metadata.
- **JSON Schema adapter** — adapts JSON Schema (draft 2020-12 and
  earlier) to `CanonicalContract`. Covers `type`, `properties`,
  `required`, `enum`, `format`, `pattern`, `minLength`/`maxLength`,
  `minimum`/`maximum`, and `items`.
- **Dict DSL adapter** — adapts Paxman's internal Dict DSL to
  `CanonicalContract`. The escape hatch and the source of truth for
  tests that do not need Pydantic.
- **OpenAPI adapter** (best-effort) — adapts OpenAPI 3.x schemas to
  `CanonicalContract`. Covers a useful subset of OpenAPI 3.0; full
  3.1 coverage is deferred to V2.

### Capabilities (5)

- `text_extraction` — supports `text/plain` and `text/html` inputs.
- `regex_extraction` — ECMAScript-flavored regex with named groups.
- `lookup` — deterministic in-memory dict backend.
- `inference` — provider SPI with a stub provider. Real LLM providers
  (OpenAI, Anthropic) are V2.
- `validation` — type, range, regex, enum, and ISO-4217 constraint
  checks.

### Subsystems (7)

- `contract/` — adapt and validate for all four V1 adapters.
- `planner/` — rule-based field-centric planning, deterministic,
  7-step heuristic chain.
- `capabilities/` — registry, dispatch, `CapabilitySpec` metadata,
  all five V1 capabilities.
- `executor/` — sequential execution, early stop, budget tracking.
- `reconciler/` — merge, conflict detection, confidence assignment,
  MONEY arithmetic, `CurrencyPolicy`.
- `artifact/` — build, serialize, `replay_hash`, rehydration,
  tamper detection.
- `api/` — `paxman.normalize`, `paxman.replay`, public types,
  public errors, public SPIs.

### Public API

- `paxman.normalize(input_data, contract, budget=None, policy=None) -> ExecutionArtifact`
- `paxman.replay(artifact, contract) -> ExecutionArtifact`
- `paxman.register_adapter(adapter) -> None`
- `paxman.register_capability(capability) -> None`
- Public types re-exported: `CanonicalContract`, `CanonicalField`,
  `FieldType`, `Status`, `ConfidenceBand`, `ResolutionPolicy`,
  `Budget`, `Policy`, `ExecutionArtifact`, `CurrencyPolicy`.
- Public errors re-exported: `PaxmanError`, `InvalidContractError`,
  `ExecutionError`, `CapabilityError`, `InferenceProviderError`,
  `BudgetExceededError`, `ReconciliationError`, `ReplayError`,
  `VersionMismatchError`, `HashMismatchError`, `ConfigurationError`.
- Public SPIs: `ContractAdapter`, `Capability`.

### Field types (9)

`STRING`, `INTEGER`, `DECIMAL`, `BOOLEAN`, `DATE`, `ENUM`, `OBJECT`,
`ARRAY`, `MONEY`.

### MONEY as a first-class type

- `MONEY` carries a numeric amount (`Decimal`), an ISO-4217 currency
  code, and optional precision. No float rounding.
- The Reconciler enforces currency matching by default
  (`CurrencyPolicy.STRICT_MATCH`).
- `CurrencyPolicy.ALLOW_FX` requires an explicit `fx_rate` field.

### Determinism and replay

- The planner is a pure function. Same inputs produce byte-equal
  `ExecutionPlan` JSON (property-tested with Hypothesis
  `derandomize=True`).
- `paxman.replay()` rehydrates an artifact without recomputation.
  The `replay_hash` (SHA-256) detects tampering.
- Replay raises `HashMismatchError` on a tampered artifact and
  `VersionMismatchError` on an unsupported Paxman version.

### Reference examples (3)

- `examples/backend_service/` — FastAPI + Pydantic.
- `examples/ai_agent_ingest/` — stdlib-only agent tool-calling loop.
- `examples/saas_procurement/` — CSV batch procurement pipeline.

### CI pipeline (9 checks)

`ruff check`, `ruff format --check`, `mypy --strict`, `interrogate`
(100% on public surface), `bandit`, `pip-audit`, `pyright`,
`import-linter` (6 subsystem contracts), `pytest --cov` (per-subsystem
thresholds), and `hatchling build`. All 9 checks run on every PR via
GitHub Actions.

---

## What's deferred to V2

- **LLM planner.** The V1 planner is rule-based (7-step heuristic
  chain). An LLM-driven planner is V2.
- **Async API.** V1 `paxman.normalize()` is synchronous and not
  thread-safe. Async support is V2.
- **Parallel field execution.** V1 executes fields sequentially per
  [ADR-0006](../adr/0006-sequential-execution-v1.md). Parallel
  execution is V2.
- **Real inference provider integrations.** V1 ships a stub inference
  provider. Real providers (OpenAI, Anthropic, Cohere) are V2.
- **RAG framework integration.** Paxman is not a RAG framework. Wrap
  Paxman behind a RAG pipeline; the contract becomes the structured
  extraction step.
- **OpenAPI 3.1 full coverage.** V1 ships best-effort OpenAPI 3.0
  support. Full 3.1 coverage is V2.
- **Pyright strict mode.** V1 runs pyright as advisory. Strict mode
  is V2.
- **Migration tools.** The migration guide
  ([docs/concepts/MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md)) is a
  skeleton in V1. Worked examples for LlamaIndex, LangChain, and
  Unstructured are V2.

---

## Reference examples

Three reference examples ship with V1. Each demonstrates a different
persona and integration pattern.

### `examples/backend_service/`

A minimal FastAPI service that exposes `POST /normalize` for
contract-driven normalization via `paxman.normalize()`. Demonstrates
the backend-developer persona (Persona A). Uses a Pydantic `Invoice`
model as the contract. Returns the `ExecutionArtifact` as JSON with
status, normalized data, unresolved fields, replay hash, and
diagnostics.

### `examples/ai_agent_ingest/`

A framework-agnostic agent tool-calling loop that calls
`paxman.normalize()` as a tool. Demonstrates the AI-engineer persona
(Persona B). Zero framework dependencies (just `paxman[pydantic]`).
The pattern ports to LangChain, LlamaIndex, or any custom agent
framework by replacing the `FakeLLM` with a real LLM.

### `examples/saas_procurement/`

A CSV-batch invoice and quotation pipeline for SaaS procurement.
Demonstrates the procurement-team persona (Persona C). Reads a CSV
manifest (`id,input_file,contract_name`), normalizes each row via
`paxman.normalize()`, writes artifacts to disk as JSON, and verifies
cross-run `replay_hash` reproducibility.

---

## Known limitations

V1-specific limitations that users should be aware of:

- **Stub inference provider only.** V1 ships a `StubInferenceProvider`
  that returns fixed text. Real LLM and AI providers (OpenAI,
  Anthropic, Cohere) are V2. The inference capability's provider SPI
  is in place; only the real provider implementations are missing.
- **Sequential execution.** V1 executes fields one at a time in plan
  order. There is no parallel field execution. For a 20-field
  contract, the executor runs 20 capability chains sequentially.
  Parallel execution is V2.
- **OpenAPI 3.1 coverage is best-effort.** The OpenAPI adapter covers
  a useful subset of OpenAPI 3.0. Keywords like `oneOf`, `anyOf`,
  `allOf`, and `discriminator` are rejected with
  `UNSUPPORTED_OPENAPI_FEATURE`. Full 3.1 coverage is V2.
- **PDF and OCR are not supported.** The `text_extraction` capability
  handles `text/plain` and `text/html` only. PDF parsing and OCR are
  V2. Pre-process PDFs to text before passing them to
  `paxman.normalize()`.
- **No async API.** `paxman.normalize()` is synchronous. Async support
  is V2.
- **No migration tools.** The migration guide is a skeleton. Worked
  examples for moving from LlamaIndex, LangChain, or Unstructured to
  Paxman are V2.

---

## External user validation

[V1_ACCEPTANCE_CRITERIA.md](https://github.com/nexusnv/paxman-wiki/blob/main/Internal-Development/V1-acceptance-criteria.md) §5
requires at least three external users (from the target personas in
[PRD.md §6](https://github.com/nexusnv/paxman-wiki/blob/main/Internal-Development/PRD.md)) to have used Paxman for a real workload
and reported no blocking issues before tagging `1.0.0`.

This validation is documented as the project owner's task per the
Oracle review M5 fallback. If fewer than three external users have
validated Paxman by sprint end, the project owner will issue a
formal waiver noting the gap and the plan to close it in a
post-release cycle.

---

## Upgrade notes

N/A. V1.0.0 is the first stable release. There is no prior 1.x
version to upgrade from.

For users migrating from pre-1.0 (v0.x) releases: the public API
(`paxman.normalize()`, `paxman.replay()`, `paxman.register_adapter()`,
`paxman.register_capability()`) is stable from 1.0.0 onward and
follows semver. Breaking changes between 0.x and 1.0 are documented
in the [CHANGELOG.md](../operations/changelog.md).

For users migrating from ad-hoc normalization pipelines (regex + LLM,
document parsers, agent frameworks) to Paxman, see
[docs/concepts/MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md).

---

## Install

```bash
pip install paxman[pydantic]
```

This installs the core package plus the Pydantic adapter. To install
all V1 adapters:

```bash
pip install paxman[all]
```

Paxman requires Python 3.11 or later. The core package has three
runtime dependencies: `attrs`, `typing-extensions`, and `structlog`.

---

## See also

- [CHANGELOG.md](../operations/changelog.md) — full release history.
- [V1_ACCEPTANCE_CRITERIA.md](https://github.com/nexusnv/paxman-wiki/blob/main/Internal-Development/V1-acceptance-criteria.md) — the
  definition of done for V1.
- [README.md](../index.md) — quickstart and usage guide.
- [PRD.md](https://github.com/nexusnv/paxman-wiki/blob/main/Internal-Development/PRD.md) — product vision and success metrics.
- [ARCHITECTURE.md](../reference/architecture.md) — subsystem design and
  sequence diagram.
- [GLOSSARY.md](../reference/glossary.md) — vocabulary.
- [REPLAY_AND_DETERMINISM.md](../reference/replay-and-determinism.md) —
  replay model deep dive.
- [SECURITY.md](../security/index.md) — threat model and PII handling.
- [EXTENDING.md](../reference/extending.md) — how to add adapters,
  capabilities, and inference providers.
- [docs/concepts/](./) — conceptual docs (contracts, capabilities,
  planning, reconciliation, replay, migration guide).
- [docs/howto/](../howto/) — quick-start how-tos.
- [examples/](../../examples/) — reference examples.
