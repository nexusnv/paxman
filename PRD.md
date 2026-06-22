# Product Requirements Document (PRD)

### 1. Product Vision & North Star
Paxman is a contract-driven deterministic normalization engine that transforms ambiguous structured and unstructured input into evidence-backed normalized artifacts conforming to caller-defined contracts.

Paxman does not own schemas, domain ontologies, or business standards.

The caller is solely responsible for supplying the target contract, whether that contract originates from application schemas, ERP object models, API schemas, agent tool schemas, Pydantic models, JSON Schema, OpenAPI specifications, or other adapter-supported representations. Paxman’s responsibility begins only after a valid contract has been provided.

Given arbitrary input and a target contract, Paxman synthesizes the cheapest trustworthy deterministic execution path required to produce normalized output with explicit evidence, confidence, diagnostics, and unresolved states. Every product, architecture, and roadmap decision should be checked against this vision.

### 2. Problem Statement
Modern systems receive unstructured or partially structured information from PDFs, scans, emails, spreadsheets, APIs, documents, and human text. Downstream systems need normalized data, but the path from raw input to valid structured output varies widely by source quality, schema complexity, accuracy requirements, and cost constraints.

A single fixed pipeline is not sufficient.

### 3. Product Objective
Paxman’s objective is to:
- normalize input into a contract-defined structure,
- infer the best execution path dynamically per field,
- preserve evidence and traceability,
- remain deterministic and replayable,
- optimize for correctness and cost under explicit constraints.

### 4. Product Philosophy
1. **No contract, no normalization.** Paxman cannot normalize without a target contract.
2. **The contract describes what, not how.** Contracts describe required fields, criticality, types, confidence expectations, and evidence requirements. Planning and execution decide how to satisfy them.
3. **Paxman does not guess silently.** Any inferred value must be surfaced with evidence, confidence, and resolution metadata.
4. **The pipeline is synthesized, not fixed.** Paxman selects the best execution plan per input and contract.
5. **Determinism is required.** The same input, contract, version set, and execution constraints must yield the same plan and replayable result.
6. **Cost is a first-class concern.** Paxman should prefer the cheapest sufficient path that still satisfies the required accuracy policy.
7. **The API must stay tiny.** The public surface should remain learnable in minutes and keep complexity inside the planner and executor, not the caller.

### 4.1 Contract Ownership Principle
Paxman never owns business schemas, enterprise data models, domain standards, or ontologies.
Contracts are fully caller-owned. The caller is responsible for supplying the target contract. 

Contracts may originate from:
* Python models
* API schemas
* ERP object models
* agent tool schemas
* JSON Schema
* OpenAPI
* custom DSLs
* wrapper applications

Paxman treats all external contract formats as equivalent after canonicalization.

### 5. Target Users
- Backend developers building normalization services.
- AI engineers building agentic ingestion or extraction flows.
- SaaS teams building procurement, invoice, quotation, and document pipelines.
- Platform teams wrapping Paxman inside a larger service.

### 6. Primary Use Cases
#### A. Compare prices from scanned invoices
A user drops in three scanned invoices and asks which is cheaper. Paxman normalizes invoice fields into the same contract so downstream logic can compare totals, currencies, taxes, and line items consistently.

#### B. Normalize supplier quotations
A supplier quotation may contain inconsistent formatting, partial metadata, footnotes, and implicit currency clues. Paxman produces a contract-valid quotation object or returns an explicit unresolved result.

#### C. Normalize multi-source procurement data
A SaaS wrapper receives data from email, OCR, CSV, and API sources. Paxman converts them into one canonical procurement schema while preserving source evidence.

### 7. Core Requirements
#### 7.1 Contract-Driven Normalization
- The caller must provide a target contract.
- Normalization must fail or return unresolved if no usable contract is supplied.
- Paxman must support multiple contract representations through adapters.

#### 7.2 Adaptive Plan Synthesis
- Paxman must determine the execution plan based on input type, contract shape, required confidence, and budget.
- The plan should favor deterministic and low-cost methods when sufficient.
- The planner is responsible for synthesis; capabilities are responsible for execution.

#### 7.3 Evidence-Backed Output
- Every resolved fact should carry provenance or evidence metadata.
- Inferred or derived values must be distinguishable from directly observed values.
- Unresolved fields must be explicit.

#### 7.4 Deterministic Replay
- A completed execution should be replayable.
- Replaying with the same contract, configuration, and version set should reproduce the same artifact.

#### 7.5 Budget Awareness
- The caller may provide cost, latency, and accuracy constraints.
- Paxman should use these constraints during plan synthesis.

#### 7.6 Rule-Based Planning in V1
- V1 planning must be deterministic and rule-based.
- No LLM planner, no agent planner, and no AI-generated planner logic should be required for core operation.

#### 7.7 First-Class Capabilities
- Capabilities should be explicit planning primitives with metadata for input, output, cost, and determinism.
- LLMs should be modeled as providers behind inference capabilities, not as capabilities themselves.

#### 7.8 Limited V1 Capability Surface
A lean V1 should ship with a small set of capabilities:
- Text extraction
- Regex extraction
- Lookup / retrieval
- Inference
- Validation

#### 7.9 Artifact Is the Product
- The artifact should include normalized data, evidence, unresolved fields, diagnostics, plan metadata, execution hash, and replay data.

#### 7.10 No Persistence in Core
- Paxman should return an artifact and leave persistence to the caller. The core should not assume any storage backend.

### 8. Non-Goals
- Paxman is not a workflow engine.
- Paxman is not a general-purpose agent framework.
- Paxman is not a RAG framework.
- Paxman is not a persistence layer.
- Paxman is not responsible for tenant routing or enterprise access control.
- Paxman is not a schema registry.
- Paxman does not own standards libraries.
- Paxman does not define domain ontologies.
- Paxman does not manage enterprise data models.

---