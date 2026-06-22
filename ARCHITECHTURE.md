## Architecture Draft

### 1. Architecture Overview
Paxman Core consists of six major subsystems. Each subsystem has strict responsibilities. This separation preserves determinism, debuggability, and architectural clarity.

```text
Contract Adapter System
        ↓
Contract Validator
        ↓
Field Planner
        ↓
Executor
        ↓
Reconciler
        ↓
Artifact Builder

```

### 2. High-Level Flow

1. Receive input and target contract.
2. Canonicalize the contract via the Contract Adapter System.
3. Validate the contract via the Contract Validator.
4. Analyze the input profile.
5. Build a deterministic, field-centric execution plan.
6. Execute capabilities in plan order.
7. Reconcile truths to assign confidence and resolve conflicts.
8. Emit artifact.

### 3. Core Architectural Principles

#### 3.1 Contract Externalization

Paxman should remain agnostic about where the contract came from. It only needs a canonical internal representation.

#### 3.2 Deterministic Planning

Given the same input profile, canonical contract, configuration, and capability set, the planner must choose the same plan.

#### 3.3 Isolation of Concerns

* Contracts define what output must look like.
* Planner defines what to do.
* Executor defines how to run it.
* Reconciler defines what is ultimately true.
* Artifact defines what was produced.

### 4. Internal Modules

```text
paxman_core/
├── contract/
│   ├── canonical.py
│   ├── validator.py
│   ├── semantics.py
│   └── adapters/
│
├── planner/
│   ├── planner.py
│   ├── heuristics.py
│   ├── scoring.py
│   └── policies.py
│
├── capabilities/
│
├── executor/
│
├── reconciler/
│
├── artifact/
│
└── api/

```

### 5. Contract Adapter System

The Contract Adapter System converts caller-provided contracts into Paxman’s canonical internal representation. Paxman never executes directly against external schemas.

Supported adapters in V1:

* Pydantic Adapter
* JSON Schema Adapter
* Dict DSL Adapter
* Optional OpenAPI Adapter

Responsibilities:

* structural conversion
* semantic annotation
* field normalization
* constraint translation
* canonical contract generation

### 6. Contract Validator

Because Paxman accepts arbitrary caller contracts, contract validation is mandatory.

Responsibilities:

* validate supported field types
* validate constraints
* validate field paths
* validate semantic tags
* validate confidence thresholds
* reject unsupported contract features

Invalid contracts must fail immediately with `INVALID_CONTRACT`. Without a valid contract, Paxman cannot operate.

### 7. Canonical Contract Model

Paxman translates supported contract formats into a canonical internal form.

```python
CanonicalContract(
    id: str,
    version: str,
    fields: list[CanonicalField],
    constraints: list[Constraint],
    policies: ContractPolicy
)

```

```python
CanonicalField(
    id: str,
    path: str,
    name: str,
    type: FieldType,
    required: bool,
    critical: bool,
    nullable: bool,
    confidence_threshold: float,
    evidence_required: bool,
    semantic_tags: list[str],
    fallback_policy: ResolutionPolicy
)

```

**Supported V1 Types:** `STRING`, `INTEGER`, `DECIMAL`, `BOOLEAN`, `DATE`, `ENUM`, `OBJECT`, `ARRAY`, `MONEY`.
*Note: `MONEY` is a first-class type because financial normalization requires money-aware semantics such as precision, currency symbol resolution, ISO currency normalization, FX conversion, and rounding rules.*

#### 7.1 Structural vs Semantic Layers

Contracts contain two layers.

* **Structural Layer:** Defines shape (e.g., `currency_code: string`).
* **Semantic Layer:** Defines meaning (e.g., `semantic_tags = ["currency", "iso4217"]`).

Structural metadata alone is insufficient for intelligent planning. Semantic metadata enables capability selection, planning optimization, and reconciliation quality.

### 8. Planner Design

#### 8.1 Field-Centric Planning

Paxman is field-centric, not document-centric. Paxman does not plan to "parse the entire document". Instead, Paxman plans resolution independently for each required field.

Example required fields: `supplier_name`, `currency_code`, `line_items[].price`, `tax_amount`.
Each field receives its own execution plan. This enables:

* cost optimization
* targeted inference
* deterministic execution
* selective capability invocation

#### 8.2 Planning Heuristics

The planner should deterministically favor:

1. Explicit evidence
2. Local deterministic extraction
3. Structured lookup
4. Derived computation
5. Local inference
6. Remote inference
7. UNRESOLVED

### 9. Capability Model

Capabilities are reusable atomic operations.

#### 9.1 Capability Confidence Rule

Capabilities never assign confidence. Capabilities only return:

* candidates
* evidence
* diagnostics

Confidence is exclusively owned by the Planner and Reconciler. This ensures confidence remains globally comparable across all capabilities and prevents confidence inflation.

### 10. Execution Model

The executor runs the plan deterministically. It should pass context forward, collect evidence and diagnostics, stop early when the contract is satisfied with acceptable confidence, and return explicit unresolved states when it cannot satisfy the contract.

### 11. Reconciler

Reconciler is a first-class subsystem. Its responsibilities are:

* merge candidate values
* detect conflicts
* compare evidence quality
* assign confidence
* resolve final truth
* decide unresolved states

Reconciliation is where Paxman converts uncertainty into trustworthy normalized output.

### 12. Truth Resolution Model

Paxman internally operates on three truth layers:

```text
Contract Truth (What the caller requires)
        ↓
Candidate Truth (What capabilities discover)
        ↓
Resolved Truth (What Reconciler accepts into the final artifact)

```

### 13. Artifact Model

The artifact is the final output bundle containing normalized data, evidence, and traceability.

```python
ExecutionArtifact(
    normalized_data,
    field_results,
    unresolved_fields,
    evidence,
    diagnostics,
    execution_plan,
    replay_hash,
    statistics
)

```

```python
FieldResult(
    field_id,
    status,
    value,
    confidence,
    evidence_refs
)

```

Statuses:

* `SUCCESS`
* `PARTIAL_SUCCESS`
* `UNRESOLVED`
* `INVALID_CONTRACT`
* `EXECUTION_FAILED`

#### 13.1 Confidence Model

Confidence external artifact representation is sorted into bands: `CERTAIN`, `HIGH`, `MEDIUM`, `LOW`, `UNTRUSTED`.
Internal representation is managed as a float between `0.0 – 1.0`.

### 14. Replay Model

The replay hash captures the execution signature, including the canonical contract representation, input fingerprint, planner version, capability versions, configuration, and constraints. Replaying reconstructs the same plan where possible and otherwise explains any divergence.

### 15. Public API Direction

The top-level API shape:

```python
result = paxman.normalize(
    input_data,
    contract=target_contract,
    budget=budget,
    policy=policy,
)

```

The API should remain tiny. The complexity belongs inside planning, execution, and reconciliation.

### 16. V1 Scope

#### 16.1 What to Ship

* Contract Adapters (Pydantic, JSON Schema, Dict)
* Contract Validator
* Canonical Contract Model
* Field-Centric Planner
* Executor
* Reconciler
* Artifact Builder
* Capabilities: Text extraction, Regex extraction, Lookup/retrieval, Inference, Validation
* Replay hash & Evidence capture

#### 16.2 What to Postpone to V2

* capability marketplace
* visual planners
* graph execution
* LLM planners
* workflow orchestration
* persistent execution
* RAG subsystems
* multi-agent coordination

### 17. Recommended Direction

The strongest version of Paxman requires that the contract is supplied externally, translated into a canonical form, validated, and then passed to a field-centric planner. The reconciler evaluates the candidate truths from capabilities to build a fully documented, evidence-backed artifact.