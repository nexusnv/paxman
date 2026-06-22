# Product Requirements Document (PRD) — Paxman

> **Status:** Draft v2 (post-documentation review)
> **Scope:** Library v0.1 / V1
> **Owner:** Paxman core team
> **Related docs:** [ARCHITECTURE.md](./ARCHITECTURE.md), [PACKAGE_STRUCTURE.md](./PACKAGE_STRUCTURE.md), [GLOSSARY.md](./GLOSSARY.md), [V1_ACCEPTANCE_CRITERIA.md](./V1_ACCEPTANCE_CRITERIA.md)

---

## 1. Executive Summary

Paxman is a **contract-driven, deterministic normalization engine** for Python. Given arbitrary input (PDFs, scans, emails, spreadsheets, API payloads, free text) and a caller-owned target contract (Pydantic, JSON Schema, OpenAPI, or a built-in Dict DSL), Paxman synthesizes the **cheapest trustworthy execution path** required to produce an **evidence-backed, replayable** normalized artifact. The engine returns an explicit `UNRESOLVED` state for any field it cannot satisfy with sufficient confidence rather than guessing silently.

Paxman does **not** own schemas, domain ontologies, business standards, persistence, or workflow orchestration. It is a **library**, not a service: the caller owns the contract, the storage, and the orchestration around it.

**The pitch in one line:** _"You bring a contract, you bring the data, Paxman gives you a normalized, evidence-backed, replayable artifact — or tells you exactly which fields it could not resolve and why."_

---

## 2. Product Vision & North Star

Paxman is a contract-driven deterministic normalization engine that transforms ambiguous structured and unstructured input into evidence-backed normalized artifacts conforming to caller-defined contracts.

Paxman does not own schemas, domain ontologies, or business standards.

The caller is solely responsible for supplying the target contract, whether that contract originates from application schemas, ERP object models, API schemas, agent tool schemas, Pydantic models, JSON Schema, OpenAPI specifications, or other adapter-supported representations. Paxman's responsibility begins only after a valid contract has been provided.

Given arbitrary input and a target contract, Paxman synthesizes the cheapest trustworthy deterministic execution path required to produce normalized output with explicit evidence, confidence, diagnostics, and unresolved states. Every product, architecture, and roadmap decision should be checked against this vision.

---

## 3. Problem Statement

Modern systems receive unstructured or partially structured information from PDFs, scans, emails, spreadsheets, APIs, documents, and human text. Downstream systems need normalized data, but the path from raw input to valid structured output varies widely by source quality, schema complexity, accuracy requirements, and cost constraints.

A single fixed pipeline is not sufficient.

### 3.1 What goes wrong today

| Failure mode | Cost | Frequency |
|---|---|---|
| Hand-rolled per-source normalization pipelines | High maintenance, slow to add new sources | Every project |
| "Just call an LLM" approaches without evidence or replay | Untraceable failures, no auditability, non-reproducible | Common in AI-first teams |
| Schema-validator-only stacks that don't help with extraction | Forces callers to write and re-write extractors per source | Common in ETL |
| "Schema-less" or auto-schema approaches that hallucinate fields | Spurious data, downstream corruption | Common in research prototypes |
| Monolithic document-understanding services | Vendor lock-in, opaque pricing, no evidence | Enterprise procurement |

### 3.2 What callers actually need

A small, predictable, **learnable-in-minutes** surface that:

1. Accepts the caller's own contract — no opinion on how the schema was authored.
2. Decides per field what to do, not per document.
3. Returns the result with the evidence and confidence to defend it.
4. Can be re-run deterministically from the artifact alone.
5. Costs as little as possible for the required confidence.

---

## 4. Product Objective

Paxman's objective is to:

- Normalize input into a contract-defined structure.
- Infer the best execution path dynamically per field.
- Preserve evidence and traceability.
- Remain deterministic and replayable.
- Optimize for correctness and cost under explicit constraints.

---

## 5. Product Philosophy

1. **No contract, no normalization.** Paxman cannot normalize without a target contract.
2. **The contract describes what, not how.** Contracts describe required fields, criticality, types, confidence expectations, and evidence requirements. Planning and execution decide how to satisfy them.
3. **Paxman does not guess silently.** Any inferred value must be surfaced with evidence, confidence, and resolution metadata.
4. **The pipeline is synthesized, not fixed.** Paxman selects the best execution plan per input and contract.
5. **Determinism is required.** The same input, contract, version set, and execution constraints must yield the same plan and replayable result.
6. **Cost is a first-class concern.** Paxman should prefer the cheapest sufficient path that still satisfies the required accuracy policy.
7. **The API must stay tiny.** The public surface should remain learnable in minutes and keep complexity inside the planner and executor, not the caller.

### 5.1 Contract Ownership Principle

Paxman never owns business schemas, enterprise data models, domain standards, or ontologies.

Contracts are fully caller-owned. The caller is responsible for supplying the target contract.

Contracts may originate from:

- Python models (Pydantic)
- API schemas (JSON Schema, OpenAPI)
- ERP object models
- Agent tool schemas
- Custom DSLs (Paxman Dict DSL)
- Wrapper applications

Paxman treats all external contract formats as equivalent after canonicalization.

### 5.2 V1 Origin → Adapter Mapping

Not every origin in §5.1 ships a first-party adapter in V1. The current mapping is:

| Origin | V1 Adapter | Notes |
|---|---|---|
| Python models | **Pydantic Adapter** | Required. The default for most users. |
| JSON Schema | **JSON Schema Adapter** | Required. Covers most API contracts. |
| Custom DSL | **Dict DSL Adapter** | Required. Internal escape hatch and Paxman-native format. |
| API / OpenAPI | **Optional OpenAPI Adapter** | Best-effort in V1; not all OpenAPI features translate. |
| ERP object models | _(no V1 adapter)_ | Wrap as Pydantic or JSON Schema. |
| Agent tool schemas | _(no V1 adapter)_ | Wrap as Pydantic or JSON Schema. |
| Wrapper applications | _(no V1 adapter)_ | Translate wrapper output to Pydantic. |

**Rule:** If a contract origin is not listed in V1, the caller adapts it to a supported origin before passing it to Paxman. This is by design — Paxman stays small and Paxman adapters stay testable.

---

## 6. Target Users

### 6.1 Primary personas

#### Persona A — Backend developer building a normalization service

- **Role:** Senior/staff backend engineer at a SaaS or platform team.
- **Goal:** Stand up a normalization pipeline that can ingest invoices, quotations, or procurement docs from many sources and produce the same canonical shape for downstream services.
- **Pain today:** Hand-rolled per-source pipelines, no evidence trail, no replay, opaque cost.
- **Picks Paxman because:** Stable, contract-driven, evidence-backed, no opinions on storage.
- **Decision criteria:** Maturity, observability, integration with their schema language (Pydantic / JSON Schema).

#### Persona B — AI engineer building an agentic ingestion flow

- **Role:** Applied ML / agent engineer.
- **Goal:** Extract structured data from documents for an agent or RAG pipeline that must be auditable and replayable.
- **Pain today:** LLM calls give plausible output but no provenance, no replay, no "I told you so" evidence.
- **Picks Paxman because:** LLMs are providers behind inference capabilities, never the source of truth; evidence is required.
- **Decision criteria:** Determinism, evidence quality, model-provider flexibility.

#### Persona C — SaaS team building procurement / invoice / quotation pipelines

- **Role:** Tech lead at a procurement, expense, or AP automation company.
- **Goal:** Compare offers across suppliers, currencies, and formats; build normalized procurement records.
- **Pain today:** Each supplier uses different formats, currencies, line-item conventions.
- **Picks Paxman because:** `MONEY` is first-class, evidence-backed, deterministic — required for finance.
- **Decision criteria:** `MONEY` accuracy, FX handling, replay for audits.

#### Persona D — Platform team wrapping Paxman

- **Role:** Platform / infrastructure team.
- **Goal:** Embed Paxman inside a larger service that adds persistence, queues, and tenant isolation.
- **Pain today:** Wants a small, stable surface; doesn't want Paxman to take over its stack.
- **Picks Paxman because:** Tiny public API, no persistence in core, deterministic.
- **Decision criteria:** API stability, optional extras, packaging policy.

### 6.2 Non-target users (out of persona)

- **End users** of a document-understanding SaaS — Paxman is a library, not a service.
- **Data scientists building ad-hoc extraction notebooks** — Paxman's determinism and contract-first design is heavier than needed for throwaway analysis.
- **Teams that need workflows, queues, or persistence** — Paxman explicitly does not own these.

---

## 7. Primary Use Cases

Use cases follow a **structured format**: `Input → Contract → Expected output → Edge cases → Failure modes`.

### 7.1 Use case A — Compare prices from scanned invoices

**Input:** Three scanned invoices in mixed formats (PDF text + image OCR + email body).
**Contract:** A Pydantic `Invoice` model with required `supplier_name`, `total_amount`, `currency_code`, `tax_amount`, `line_items[]`.
**Expected output:** Three `Invoice` objects with evidence and confidence per field. Cheapest supplier deterministically identifiable.
**Edge cases:** Missing `tax_amount`, ambiguous currency symbol, OCR errors in supplier name.
**Failure modes:** At least one `UNRESOLVED` field on a degraded scan; caller decides whether to retry with a stronger OCR or accept partial.

### 7.2 Use case B — Normalize supplier quotations

**Input:** Supplier quotation with inconsistent formatting, partial metadata, footnotes, implicit currency clues.
**Contract:** A `Quotation` model with optional `valid_until`, `payment_terms`, required `unit_price`, `currency`.
**Expected output:** A contract-valid `Quotation` or an explicit list of `UNRESOLVED` fields.
**Edge cases:** Footnote-only metadata, multi-currency lines, embedded discount clauses.
**Failure modes:** Planner downgrades to remote inference for footnotes; Reconciler marks evidence as `LOW` confidence.

### 7.3 Use case C — Normalize multi-source procurement data

**Input:** Mixed data from email, OCR, CSV, and API sources.
**Contract:** A canonical procurement schema (Pydantic) with MONEY-typed fields, array of `LineItem`, optional `tax_id`.
**Expected output:** A single canonical procurement record with per-field source evidence and a unified `MONEY` representation.
**Edge cases:** Conflicting totals across sources, mixed currencies, missing line items.
**Failure modes:** Reconciler detects conflict between two candidates and either picks the higher-confidence one or surfaces `PARTIAL_SUCCESS` with both candidates' evidence.

### 7.4 Use case D — Replay an existing artifact

**Input:** A previously produced `ExecutionArtifact` and a Paxman version.
**Contract:** The same contract that was originally used (version-pinned).
**Expected output:** A rehydrated `ExecutionArtifact` with identical `normalized_data`, `field_results`, `evidence_refs`, and `replay_hash`. No recomputation.
**Edge cases:** Replay on a different Paxman version (should warn, may be rejected).
**Failure modes:** Replay divergence → artifact is **rejected** and the divergence report is returned.

---

## 8. Core Requirements

Core requirements are split into **functional** (what the system does) and **non-functional** (how it does it). The PRD does not specify _how_; that is the architecture's job.

### 8.1 Functional requirements

#### FR-1 Contract-driven normalization
- The caller must provide a target contract.
- Normalization must fail or return `UNRESOLVED` if no usable contract is supplied.
- Paxman must support multiple contract representations through adapters.

#### FR-2 Adaptive plan synthesis
- Paxman must determine the execution plan based on input type, contract shape, required confidence, and budget.
- The plan should favor deterministic and low-cost methods when sufficient.
- The planner is responsible for synthesis; capabilities are responsible for execution.

#### FR-3 Evidence-backed output
- Every resolved fact carries provenance or evidence metadata.
- Inferred or derived values are distinguishable from directly observed values.
- Unresolved fields are explicit.

#### FR-4 Deterministic replay
- A completed execution is replayable.
- Replaying with the same contract, configuration, and version set reproduces the same artifact.

#### FR-5 First-class capabilities
- Capabilities are explicit planning primitives with metadata for input, output, cost, and determinism.
- LLMs are modeled as providers behind inference capabilities, not as capabilities themselves.

#### FR-6 Limited V1 capability surface
A lean V1 ships with a small set of capabilities:
- Text extraction
- Regex extraction
- Lookup / retrieval
- Inference
- Validation

#### FR-7 Artifact is the product
- The artifact includes normalized data, evidence, unresolved fields, diagnostics, plan metadata, execution hash, and replay data.

#### FR-8 No persistence in core
- Paxman returns an artifact and leaves persistence to the caller. The core does not assume any storage backend.

### 8.2 Non-functional requirements

#### NFR-1 Rule-based planning in V1
- V1 planning is deterministic and rule-based.
- No LLM planner, no agent planner, and no AI-generated planner logic is required for core operation.

#### NFR-2 Budget awareness
- The caller may provide cost, latency, and accuracy constraints.
- Paxman uses these constraints during plan synthesis.

#### NFR-3 Determinism guarantees
Given the same canonical contract, input profile, configuration, capability set, and budget/policy, Paxman produces the same `FieldPlan`s, the same execution order, and the same `ExecutionArtifact` (modulo declared non-deterministic capability outputs, which are recorded as evidence).

Replay reproduces the same artifact **without recomputation**.

#### NFR-4 Performance
- **Target p50:** ≤ 200 ms for a 20-field contract on a 100 KB input (no remote inference).
- **Target p99:** ≤ 2 s under the same conditions.
- Paxman does not commit to SLOs in V1; these are aspirational targets for measurement.

#### NFR-5 Security & privacy
- Paxman does not log raw input data in production by default.
- Inference providers are pluggable; secrets are passed by reference, never embedded in artifacts.
- See [SECURITY.md](./SECURITY.md) for the full threat model.

#### NFR-6 Type safety & API stability
- All public API is type-hinted; the package ships `py.typed`.
- Major version 0.x may break; version 1.0+ follows semver.
- See [ARCHITECTURE.md §9 Versioning Strategy](./ARCHITECTURE.md) for details.

#### NFR-7 Testability
- Subsystems are testable in isolation via defined seams.
- Determinism is property-tested.
- See [TESTING_STRATEGY.md](./TESTING_STRATEGY.md).

---

## 9. Success Metrics

These are **measurable** outcomes for V1. Targets are aspirational for v0.1 and become gating criteria for v1.0.

| Metric | Target | How measured |
|---|---|---|
| Field resolution rate on canonical invoice corpus | ≥ 90% `SUCCESS` (excluding `UNRESOLVED`) on a held-out set | Eval suite |
| Replay reproducibility | 100% identical artifact hash for deterministic plans on the same Paxman version | CI property test |
| API surface size | ≤ 5 public functions in V1 | Public API audit |
| Type coverage (mypy strict on public surface) | 100% | `mypy --strict paxman` |
| Test coverage on core | ≥ 90% lines for `contract/`, `planner/`, `executor/`, `reconciler/` | `pytest --cov` |
| Doc coverage | Every public symbol has a docstring; every subsystem has a doc | `interrogate` |
| Cold-start time (import + register capabilities) | ≤ 100 ms | Microbenchmark |
| Adapters shipped in V1 | Pydantic, JSON Schema, Dict DSL (required) + OpenAPI (optional) | Package count |
| Capabilities shipped in V1 | 5 (text/regex/lookup/inference/validation) | Capability registry count |

---

## 10. V1 Acceptance Criteria (Definition of Done)

V1 is "done" when **all** of the following are true. See [V1_ACCEPTANCE_CRITERIA.md](./V1_ACCEPTANCE_CRITERIA.md) for the full checklist.

1. All 9 success-metrics targets above are met or explicitly waived.
2. The required 3 contract adapters ship: **Pydantic, JSON Schema, Dict DSL**.
3. The OpenAPI adapter ships at **best-effort** quality (a passing test suite is enough; full OpenAPI 3.1 coverage is not required).
4. All 5 V1 capabilities ship with `CapabilitySpec` metadata.
5. `paxman.normalize()` and `paxman.replay()` are the only public functions; everything else is private.
6. `py.typed` is shipped; mypy strict passes on the public surface.
7. Replay reproduces the same artifact hash for at least one end-to-end fixture.
8. The package is publishable to PyPI via trusted publishing.

---

## 11. Dependencies and Assumptions

### 11.1 Runtime assumptions

- **Python:** ≥ 3.11 (V1). Drops support when Python reaches EOL or when the upstream LTS usage falls below 5% of downloads.
- **Pydantic:** v2 (used by the Pydantic adapter; optional in core, required by the adapter).
- **JSON Schema validation:** `jsonschema` (optional, used by JSON Schema adapter).
- **OpenAPI parsing:** `openapi-spec-validator` or equivalent (optional, used by OpenAPI adapter).
- **LLM inference:** Provider-agnostic; V1 ships one reference provider behind the Inference capability (stub or local-only).

### 11.2 Caller assumptions

- The caller provides a valid, well-formed contract.
- The caller provides a parseable input (or declares it unparseable up-front).
- The caller is responsible for storage, transport, and any audit pipeline around artifacts.
- The caller configures inference-provider secrets (Paxman never persists them).

### 11.3 Out-of-band assumptions

- The Pydantic v2 ecosystem remains stable; Pydantic v1 is not supported.
- Inference providers honor the cost / latency budget at the call level; Paxman does not micro-bill.
- Non-determinism in inference outputs is acceptable as long as it is recorded as evidence.

---

## 12. Risks and Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-1 | LLM inference non-determinism undermines replay claims | High | High | V1 planner avoids inference unless required; inference outputs are captured as evidence; replay rehydrates the captured value without re-inferring. |
| R-2 | Adapter maintenance burden grows as contract formats multiply | Medium | Medium | V1 ships only 3 required + 1 optional; new adapters are best-effort community additions; the contract adapter interface is small and stable. |
| R-3 | Confidence calibration becomes subjective | Medium | Medium | Confidence is owned by Planner and Reconciler (never by capabilities); bands are fixed (`CERTAIN`/`HIGH`/`MEDIUM`/`LOW`/`UNTRUSTED`); calibration is tested. |
| R-4 | Field-plan synthesis is too slow for large contracts | Low | Medium | Field-plans are O(fields) in V1; V2 may add plan caching. |
| R-5 | `MONEY` arithmetic causes silent rounding errors | Medium | High | `MONEY` is first-class; the Reconciler enforces precision and currency matching; cross-currency is gated by an explicit policy. |
| R-6 | Artifact format becomes coupled to Paxman version | Medium | Medium | Artifact includes a Paxman-core version; replay warns on version drift; artifact is JSON-friendly for forward-compatible migration. |
| R-7 | Public API accidentally leaks implementation details | Medium | High | The `api/` module is a hard boundary; CI enforces the public API surface; `import paxman._internal` is unsupported. |
| R-8 | Confusion between "deterministic" and "reproducible" | Medium | Low | Documentation distinguishes them; determinism refers to plan synthesis; reproducibility refers to artifact identity. |
| R-9 | Compliance / data-residency concerns for inference providers | High | High | Inference provider is pluggable; artifacts do not embed raw input by default; provider is selected by the caller, not Paxman. |
| R-10 | "Six vs seven subsystems" or other doc drift returns | Low | Low | CI checks that the public docs cross-reference consistent terminology. |

---

## 13. Open Questions

These are **deliberately deferred** and tracked for the V1 cycle:

1. **Q-1** Does the Reconciler own all confidence assignment, or does the Planner assign an initial confidence that the Reconciler then re-scores? *(Resolved: see [ADR-0005](./docs/adr/0005-confidence-ownership.md).)*
2. **Q-2** Is the OpenAPI adapter required in V1 or optional? *(Resolved: optional, best-effort.)*
3. **Q-3** Can the Executor run field-plans in parallel? *(Resolved: V1 is strictly sequential; parallelism is V2.)*
4. **Q-4** Should the artifact include raw input or only evidence references? *(Resolved by default: evidence references only, raw input never embedded.)*
5. **Q-5** How is "MONEY" arithmetic handled when currencies differ? *(Resolved: explicit `CurrencyPolicy` on the field, default is to require currency match.)*
6. **Q-6** What is the deterministic canonical form for Pydantic v2 models? *(Open — see [GLOSSARY.md §Canonical Contract](./GLOSSARY.md).)*
7. **Q-7** Should Paxman ship a reference inference provider in V1? *(Open — likely yes, as a stub.)*
8. **Q-8** How do we express "no inference allowed at all" in the budget? *(Open — see [REPLAY_AND_DETERMINISM.md](./REPLAY_AND_DETERMINISM.md).)*

---

## 14. Non-Goals

Paxman is **explicitly not**:

- A workflow engine.
- A general-purpose agent framework.
- A RAG framework.
- A persistence layer.
- A schema registry.
- A standard library.
- A domain ontology.
- An enterprise data model manager.
- A tenant-routing or access-control layer.
- A GUI / web application.

If a caller needs any of these, they wrap Paxman from the outside.

---

## 15. Compliance and Data Privacy Notes

Paxman processes data the caller provides. The following non-binding defaults apply; the caller remains responsible for their own compliance posture.

- **GDPR / data minimization:** Artifacts store evidence references by default; raw input bytes are not embedded.
- **Right to erasure:** The caller is responsible for storing and deleting artifacts.
- **Data residency:** Provider selection (e.g., inference region) is the caller's responsibility.
- **PII handling:** V1 does not auto-redact PII; callers are expected to provide sanitized input or to scrub artifacts after the fact.
- **Audit trail:** Artifacts are auditable: each resolved value carries evidence and confidence.

See [SECURITY.md](./SECURITY.md) for the full threat model.

---

## 16. Glossary (inline — full glossary in [GLOSSARY.md](./GLOSSARY.md))

| Term | One-line definition |
|---|---|
| **Contract** | A caller-supplied schema describing the target shape of normalized output. |
| **Canonical Contract** | The internal, language-agnostic representation of a contract after adapter translation. |
| **Adapter** | The translation layer that converts an external contract format (Pydantic, JSON Schema, etc.) into the Canonical Contract. |
| **Field Plan** | A per-field execution plan: the ordered list of capabilities the planner chose to resolve one field. |
| **Capability** | A reusable, atomic operation (text extraction, regex, lookup, inference, validation). |
| **CapabilitySpec** | The metadata describing a capability: inputs, outputs, cost, determinism. |
| **Planner** | The deterministic, rule-based subsystem that produces field plans. |
| **Executor** | The deterministic runner that executes the plan and collects evidence. |
| **Reconciler** | The subsystem that merges candidate truths, assigns final confidence, and resolves truth. |
| **Artifact** | The frozen, evidence-backed, replayable output bundle. |
| **Truth Layer** | One of three: Contract Truth (what's required), Candidate Truth (what's discovered), Resolved Truth (what's accepted). |
| **Evidence** | Provenance metadata attached to a candidate or resolved value (source span, capability invocation, model id, etc.). |
| **Confidence** | A float 0.0–1.0 representing planner/reconciler trust in a value, mapped to bands `CERTAIN`/`HIGH`/`MEDIUM`/`LOW`/`UNTRUSTED`. |
| **Replay** | Rehydrating an artifact to its original state without recomputation. |
| **Replay Hash** | The deterministic signature that uniquely identifies an artifact given all inputs and versions. |
| **Budget** | A user-supplied constraint on cost, latency, and capability classes. |
| **Policy** | A user-supplied set of fallbacks and accuracy targets (e.g., "don't use remote inference"). |

---

## 17. References

- [ARCHITECTURE.md](./ARCHITECTURE.md) — System architecture, subsystems, ADRs.
- [PACKAGE_STRUCTURE.md](./PACKAGE_STRUCTURE.md) — Module layout, dependency DAG, public/private API.
- [GLOSSARY.md](./GLOSSARY.md) — Full domain vocabulary.
- [V1_ACCEPTANCE_CRITERIA.md](./V1_ACCEPTANCE_CRITERIA.md) — V1 definition of done.
- [REPLAY_AND_DETERMINISM.md](./REPLAY_AND_DETERMINISM.md) — Replay and determinism deep dive.
- [TESTING_STRATEGY.md](./TESTING_STRATEGY.md) — Test seams, property tests, replay tests.
- [docs/TEST_DATA.md](./docs/TEST_DATA.md) — Test data policy, dataset catalog, licensing rules.
- [SECURITY.md](./SECURITY.md) — Threat model and PII handling.
- [TESTING_STRATEGY.md](./TESTING_STRATEGY.md) — Test seams, determinism tests, property-based testing.
- [DEVELOPMENT.md](./DEVELOPMENT.md) — Local dev setup.
- [EXTENDING.md](./EXTENDING.md) — How to add a new capability, adapter, or provider.
- [DEPENDENCIES.md](./DEPENDENCIES.md) — Core vs optional dependencies, packaging policy.
- [docs/adr/](./docs/adr/) — Architecture Decision Records.
