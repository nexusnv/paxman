# Extending Paxman

> **Status:** Draft v1.
> **Audience:** Paxman users who want to add a new contract adapter, capability, or inference provider.
> **Related docs:** [ARCHITECTURE.md §15 Extension Model](./architecture.md), [PACKAGE_STRUCTURE.md §15 Public Protocols](./package-structure.md), [GLOSSARY.md](./glossary.md)

This document is a **step-by-step guide** to extending Paxman. It covers the three V1 extension points: contract adapters, capabilities, and inference providers.

All extensions are public SPIs and live in `paxman.protocols`. They are stable across minor versions.

---

## 1. Adding a New Contract Adapter

A **contract adapter** translates an external contract format (e.g., a new schema language) into Paxman's internal `CanonicalContract` and back.

### 1.1 When to add a new adapter

Add a new adapter when:

- You want Paxman to accept a new schema language as input (e.g., a custom DSL, a vendor-specific schema, a Protobuf schema).
- You want to convert a non-supported contract origin to `CanonicalContract` (e.g., ERP object model → `CanonicalContract`).

Do **not** add a new adapter when:

- The format is already supported (Pydantic, JSON Schema, Dict DSL, OpenAPI).
- You can convert your input to a supported format with a small wrapper (e.g., convert ERP → JSON Schema once, then use the JSON Schema adapter).

> **V1.1.0 OpenAPI coverage** — The OpenAPI adapter now accepts both 3.0.x and 3.1.x documents. V1.1.0 support matrix:
>
> | OpenAPI 3.x feature | V1.1.0 support |
> |---|---|
> | `openapi: 3.0.x` | yes |
> | `openapi: 3.1.x` | yes |
> | `info.title` (contract id) | yes |
> | `components.schemas` (object) | yes |
> | `jsonSchemaDialect` (3.1) | yes — validated, forwarded to JSON Schema adapter |
> | `$defs` (3.1) | yes — sibling namespace for `$ref` resolution |
> | `components.schemas`-based `$ref` | yes |
> | `type: [string, null]` (3.1 nullable) | yes |
> | `webhooks` (3.1) | accepted, **ignored** (full path parsing is V2) |
> | path-item `parameters` (3.1 merge) | accepted, **ignored** (3.1 merge semantics locked in helper, see `OpenApiAdapter._merge_path_parameters`) |
> | `paths.*` (operations) | ignored |
> | `oneOf` / `anyOf` / `allOf` | rejected (V2 territory) |
> | external `$ref` (URL) | rejected (V2 territory) |

### 1.2 The `ContractAdapter` SPI

```python
from typing import Protocol, Any
from paxman import CanonicalContract


class ContractAdapter(Protocol):
    """SPI: translate an external contract format to/from CanonicalContract."""

    @property
    def format_id(self) -> str:
        """Stable identifier (e.g., 'pydantic', 'json_schema:draft-2020-12')."""
        ...

    def adapt(self, external: Any) -> CanonicalContract:
        """Translate an external contract into a CanonicalContract.

        Raises:
            InvalidContractError: if the external contract is invalid.
        """
        ...

    def export(self, canonical: CanonicalContract) -> Any:
        """Translate a CanonicalContract back into the external format.

        Raises:
            InvalidContractError: if the canonical contract cannot be exported.
        """
        ...
```

### 1.3 Step-by-step

1. **Create a new file** for the adapter, e.g., `paxman_myformat/adapter.py`.

2. **Implement the SPI:**

   ```python
   from paxman.protocols import ContractAdapter
   from paxman import CanonicalContract, InvalidContractError


   class MyFormatAdapter:
       @property
       def format_id(self) -> str:
           return "my_format"

       def adapt(self, external):
           try:
               fields = parse_my_format(external)
           except ParseError as e:
               raise InvalidContractError(
                   f"Failed to parse my_format: {e}",
                   error_code="INVALID_MY_FORMAT",
                   context={"line": e.line, "column": e.column},
               ) from e

           canonical_fields = [to_canonical_field(f) for f in fields]
           return CanonicalContract(
               id="my_format_contract",
               version="1",
               fields=canonical_fields,
               constraints=[],
               policies=ContractPolicy(),
           )

       def export(self, canonical):
           return serialize_my_format(canonical.fields)
   ```

3. **Validate that your adapter is pure:** the same input must produce the same `CanonicalContract` byte-for-byte. No randomness, no clock, no I/O.

4. **Register the adapter:**

   ```python
   import paxman

   paxman.register_adapter(MyFormatAdapter())
   ```

5. **Write tests:**

   ```python
   def test_my_format_adapter_handles_simple_contract():
       adapter = MyFormatAdapter()
       external = load_fixture("my_format/simple.myf")
       canonical = adapter.adapt(external)
       assert canonical.fields["name"].type == FieldType.STRING
       assert canonical.fields["name"].required is True
   ```

6. **Optional: ship as a third-party package.** The `paxman` core team accepts adapters into the main package only by ADR. For everything else, publish your adapter as a separate PyPI package (`paxman-myformat`) and document its registration.

### 1.4 What adapters MUST do

- **Be pure:** same input → same `CanonicalContract`. No I/O, no clock, no random.
- **Raise `InvalidContractError`** on invalid input.
- **Preserve `MONEY` semantics** if the format supports monetary values.
- **Map semantic tags** if the format supports metadata.
- **Validate before returning** — the adapter's output must be a valid `CanonicalContract`.

### 1.5 What adapters MUST NOT do

- **Read raw input** — adapters only see contracts, not the data being normalized.
- **Invoke capabilities** — adapters only translate, never plan or execute.
- **Mutate global state** — adapters must be safe to use concurrently.
- **Embed provider secrets** — adapters don't talk to providers.

---

## 2. Adding a New Capability

A **capability** is an atomic, reusable operation that produces candidates for one or more field types. Examples: `text_extraction`, `regex_extraction`, `lookup`, `inference`, `validation`.

### 2.1 When to add a new capability

Add a new capability when:

- You have a domain-specific extraction or validation step that doesn't fit the V1 surface.
- You want to ship a new algorithm (e.g., a custom regex library, a custom lookup table, a custom model wrapper).

Do **not** add a new capability when:

- The operation can be expressed as a V1 capability (e.g., don't add `phone_extraction` — use `regex_extraction` with a phone regex).
- The operation is a "policy" rather than an operation (use `ResolutionPolicy` or `ContractPolicy` instead).

### 2.2 The `Capability` SPI

```python
from typing import Protocol
from paxman.protocols import CapabilitySpec, CapabilityContext, CapabilityResult


class Capability(Protocol):
    """SPI: an atomic operation."""

    @property
    def spec(self) -> CapabilitySpec:
        """Metadata describing the capability."""
        ...

    def invoke(self, ctx: CapabilityContext) -> CapabilityResult:
        """Run the capability on the given context.

        Returns:
            CapabilityResult with candidates, evidence_refs, and diagnostics.
            MUST NOT include a `confidence` field.

        Raises:
            CapabilityError: if the capability fails to run.
        """
        ...
```

### 2.3 Step-by-step

1. **Create a new file** for the capability, e.g., `paxman_myext/capabilities/date_parser.py`.

2. **Implement the SPI:**

   ```python
   from paxman.protocols import Capability, CapabilitySpec, CapabilityContext, CapabilityResult, Candidate
   from paxman import FieldType


   class DateParserCapability:
       @property
       def spec(self) -> CapabilitySpec:
           return CapabilitySpec(
               id="date_parser",
               version="1.0",
               input_type=FieldType.STRING,
               output_type=FieldType.DATE,
               cost_estimate=CostHint(tokens=0, ms=10, usd=0.0),
               deterministic=True,
               required_providers=[],
           )

       def invoke(self, ctx: CapabilityContext) -> CapabilityResult:
           try:
               date = parse_date(ctx.input_text)
           except ParseError:
               return CapabilityResult(
                   candidates=[],
                   evidence_refs=[],
                   diagnostics=[Diagnostic(code="DATE_PARSE_FAILED", message="...")],
               )

           return CapabilityResult(
               candidates=[Candidate(value=date)],
               evidence_refs=[EvidenceRef(capability="date_parser@1.0", span=ctx.span)],
               diagnostics=[],
           )
   ```

3. **Validate that your capability is stateless:** no mutable state across invocations. Each call must produce the same result for the same input (unless `spec.deterministic=False`).

4. **Register the capability:**

   ```python
   import paxman

   paxman.register_capability(DateParserCapability())
   ```

5. **Write tests:**

   ```python
   def test_date_parser_capability_handles_iso_format():
       cap = DateParserCapability()
       result = cap.invoke(CapabilityContext(input_text="2026-01-15"))
       assert len(result.candidates) == 1
       assert result.candidates[0].value == date(2026, 1, 15)
   ```

### 2.4 What capabilities MUST do

- **Return `CapabilityResult`** with `candidates`, `evidence_refs`, and `diagnostics`.
- **Be stateless** — no mutable state across invocations.
- **Declare a `CapabilitySpec`** with input/output, cost, determinism, and required providers.
- **Capture external effects in evidence** — if the capability calls an external service, record the call as evidence.
- **Fail loudly** on unrecoverable errors via `CapabilityError`.

### 2.5 What capabilities MUST NOT do

- **Assign confidence.** Capabilities return candidates; the Reconciler assigns confidence. See [ADR-0005](../adr/0005-confidence-ownership.md).
- **Read the canonical contract directly** — capabilities receive a `CapabilityContext`.
- **Read the raw input directly** — they receive an opaque `InputData` handle via `CapabilityContext`.
- **Mutate the executor state.**

---

## 3. Adding a New Inference Provider

An **inference provider** is a model implementation that satisfies the `InferenceProvider` SPI. The `inference` capability is provider-agnostic; the provider is pluggable.

### 3.1 When to add a new provider

Add a new provider when:

- You want to use a new model API (OpenAI, Anthropic, Cohere, local models, etc.).
- You want to wrap a custom model backend.

The V1 ship ships a stub provider; V2 will ship reference providers for OpenAI, Anthropic, etc.

### 3.2 The `InferenceProvider` SPI

```python
from typing import Protocol
from paxman_internal import CompletionRequest, Completion


class InferenceProvider(Protocol):
    """SPI: a model provider behind the inference capability (internal)."""

    def complete(self, request: CompletionRequest) -> Completion:
        """Run inference and return the completion.

        Raises:
            InferenceProviderError: if the provider fails.
        """
        ...
```

### 3.3 Step-by-step

1. **Create a new file** for the provider, e.g., `paxman_myext/providers/openai.py`.

2. **Implement the SPI:**

   ```python
   import os
   from paxman_internal import InferenceProvider, CompletionRequest, Completion
   from paxman import InferenceProviderError


   class OpenAIProvider:
       def __init__(self, api_key_ref: str, default_model: str = "gpt-5"):
           self.api_key_ref = api_key_ref  # reference, not the key itself
           self.default_model = default_model

       def complete(self, request: CompletionRequest) -> Completion:
           api_key = self._resolve_key()
           try:
               response = call_openai(api_key, request, self.default_model)
           except OpenAIError as e:
               raise InferenceProviderError(
                   f"OpenAI call failed: {e}",
                   error_code="INFERENCE_PROVIDER_ERROR",
                   context={"provider": "openai", "model": self.default_model},
               ) from e
           return Completion(text=response.text, model=response.model, usage=response.usage)

       def _resolve_key(self):
           if self.api_key_ref.startswith("env:"):
               env_var = self.api_key_ref[4:]
               key = os.environ.get(env_var)
               if not key:
                   raise InferenceProviderError(f"Missing env var: {env_var}")
               return key
           raise InferenceProviderError(f"Unsupported key reference: {self.api_key_ref}")
   ```

3. **Register the provider with the `inference` capability:**

   ```python
   import paxman

   paxman.register_capability(
       paxman.capabilities.inference.with_provider(
           "openai",
           OpenAIProvider(api_key_ref="env:OPENAI_API_KEY"),
       )
   )
   ```

4. **Write tests** that mock the provider's HTTP call (use `httpx` mocks or `respx`).

### 3.4 What providers MUST do

- **Resolve secrets by reference** — never embed the secret in the artifact or log.
- **Record the model id and version** in the completion evidence.
- **Fail loudly** via `InferenceProviderError`.
- **Be retry-safe** — Paxman may retry on transient errors.

### 3.5 What providers MUST NOT do

- **Log the API key** or any other secret.
- **Mutate the request** — return a fresh `Completion` based on the request.
- **Cache the completion** in a way that breaks determinism (the Executor will not re-invoke, but the artifact must reflect what was actually returned).

---

## 4. Adding a Custom Heuristic (post-V1)

The `Heuristic` SPI is **post-V1** but the protocol is exposed in `paxman.protocols` for forward compatibility.

```python
from typing import Protocol
from paxman_internal import CanonicalField, HeuristicContext, FieldPlanStep


class Heuristic(Protocol):
    """SPI: a planner heuristic (post-V1)."""

    def select(self, field: CanonicalField, ctx: HeuristicContext) -> list[FieldPlanStep]:
        """Select the capability chain for a field."""
        ...
```

Custom heuristics require an ADR (see [docs/adr/](../adr/)).

---

## 5. Testing Your Extension

See [TESTING_STRATEGY.md](../contributing/testing-strategy.md) for the test strategy. Specifically:

- **Adapters** — roundtrip tests, validation tests, golden tests.
- **Capabilities** — known-input tests, determinism tests (for deterministic capabilities), provider-mock tests.
- **Providers** — mock the upstream API, assert `Completion` shape.

The `paxman.testing` module exposes Hypothesis strategies for generating `CanonicalContract`s, inputs, budgets, policies, and registries. Use them for property tests.

---

## 6. Distributing Your Extension

The Paxman core team accepts extensions into the main package **only by ADR** (see [docs/adr/](../adr/)). For everything else, publish your extension as a separate PyPI package:

- `paxman-<your-format>` for adapters
- `paxman-<your-capability>` for capabilities
- `paxman-<your-provider>` for inference providers

Use the `paxman-` prefix to make your package discoverable.

Document your extension in its own README and link to it from Paxman's ecosystem documentation (when it exists).

---

## 7. Versioning Your Extension

Extensions follow their own semver:

- **MAJOR** — breaking change to your public API or to the Paxman SPIs you depend on.
- **MINOR** — new feature in your extension, backward compatible.
- **PATCH** — bug fix.

When the Paxman SPIs change, follow Paxman's release notes. Your extension may need to release a new MAJOR to track the Paxman change.

---

## 8. See also

- [ARCHITECTURE.md §15 Extension Model](./architecture.md)
- [PACKAGE_STRUCTURE.md §15 Public Protocols](./package-structure.md)
- [GLOSSARY.md](./glossary.md)
- [TESTING_STRATEGY.md](../contributing/testing-strategy.md)
- [docs/adr/](../adr/)
- [SECURITY.md §3 Provider Secrets](../security/index.md) — for inference providers
