# How to Add a New Inference Provider

> **Status:** V1 (the V1 `inference` capability is provider-agnostic;
> V1 ships a stub provider).
> **Audience:** Paxman users who want to add a new model provider
> (OpenAI, Anthropic, Cohere, a local model, …).
> **Related docs:** [EXTENDING.md §3](../../EXTENDING.md) (the full
> SPI walkthrough), [docs/concepts/capabilities.md](../concepts/capabilities.md)
> (what a capability is), [SECURITY.md §3](../../SECURITY.md)
> (provider secrets).

This guide is a **focused quick-start** for adding a new inference
provider behind Paxman's `inference` capability. The full SPI
walkthrough is in [EXTENDING.md §3](../../EXTENDING.md); this
document is a 5-minute checklist.

---

## 1. The InferenceProvider SPI

```python
import typing


class InferenceProvider(Protocol):
    """SPI: a model provider behind the inference capability (internal)."""

    def complete(self, request: CompletionRequest) -> Completion:
        """Run inference and return the completion.

        Raises:
            InferenceProviderError: if the provider fails.
        """
        ...
```

The `inference` capability is **provider-agnostic**. The provider
is a pluggable object that satisfies the `InferenceProvider` SPI.
You register the provider with the `inference` capability at
registration time.

> **V1 status.** Paxman V1 ships a **stub provider**; real
> reference providers (OpenAI, Anthropic, Cohere, local models)
> are V2. The SPI is stable across minor versions, so a V1 stub
> consumer can adopt a V2 reference provider without code changes.

---

## 2. Step-by-step

### 2.1 Pick a provider name

Choose a stable, lowercase identifier. Examples:

- `"openai"`
- `"anthropic"`
- `"cohere"`
- `"local:llama-3"`
- `"my_company_internal"`

The name appears in the artifact's evidence (`provider: "<name>"`).
Do **not** include the model in the provider name — the model is a
separate field.

### 2.2 Create the provider file

```python
import os
import attrs
from paxman import InferenceProviderError
from paxman.capabilities.v1.inference import (
    CompletionRequest,
    Completion,
    Usage,
    InferenceProvider,
)


@attrs.frozen(slots=True)
class OpenAIProvider:
    """OpenAI provider for the inference capability.

    The API key is passed by reference (env var name); the provider
    resolves the reference at call time. The artifact records the
    reference, not the key.
    """

    api_key_ref: str  # e.g. "env:OPENAI_API_KEY"
    default_model: str = "gpt-5"
    base_url: str = "https://api.openai.com/v1"

    def complete(self, request: CompletionRequest) -> Completion:
        api_key = self._resolve_key()
        try:
            response = call_openai(
                api_key=api_key,
                model=self.default_model,
                prompt=request.prompt,
                temperature=request.temperature,
                base_url=self.base_url,
            )
        except OpenAIError as e:
            raise InferenceProviderError(
                f"OpenAI call failed: {e}",
                error_code="INFERENCE_PROVIDER_ERROR",
                context={"provider": "openai", "model": self.default_model},
            ) from e

        return Completion(
            text=response.text,
            model=response.model,
            usage=Usage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            ),
        )

    def _resolve_key(self) -> str:
        if self.api_key_ref.startswith("env:"):
            env_var = self.api_key_ref[4:]
            key = os.environ.get(env_var)
            if not key:
                raise InferenceProviderError(
                    f"Missing env var: {env_var}",
                    error_code="INFERENCE_PROVIDER_KEY_MISSING",
                    context={"env_var": env_var},
                )
            return key
        raise InferenceProviderError(
            f"Unsupported key reference: {self.api_key_ref}",
            error_code="INFERENCE_PROVIDER_KEY_REFERENCE",
            context={"api_key_ref": self.api_key_ref},
        )
```

### 2.3 Resolve secrets by reference

The provider **must not** embed the API key in the artifact or in
logs. Use a **reference** (e.g. `"env:OPENAI_API_KEY"`,
`"vault:secret/openai#api_key"`); resolve the reference at call
time.

Paxman does not validate the reference scheme. Implement what your
environment supports (env vars, AWS Secrets Manager, HashiCorp
Vault, Kubernetes secrets, …).

### 2.4 Record the model id and version

The `Completion` carries `model` and `usage`. These are recorded in
the artifact's evidence, so replay knows which model produced the
output. If the model has a separate version (e.g. a snapshot id),
include it:

```python
Completion(
    text=response.text,
    model=response.model,            # e.g. "gpt-5-2025-08-07"
    model_version=response.snapshot, # optional
    usage=Usage(...),
)
```

### 2.5 Be retry-safe

Paxman may retry on transient errors. Your provider **must** be
idempotent: re-calling `complete(request)` with the same request
must be safe (e.g. if your underlying API has side effects, dedupe
the call by `request.id`).

### 2.6 Do not log the API key

The provider **must not** log the API key or any other secret. Use
`structlog` with `redact_keys=["api_key", "authorization", ...]`
or the equivalent in your logging library. See
[SECURITY.md §3](../../SECURITY.md).

### 2.7 Register the provider with the `inference` capability

```python
import paxman

# Build the provider.
provider = OpenAIProvider(api_key_ref="env:OPENAI_API_KEY")

# Register the inference capability with this provider.
paxman.register_capability(
    paxman.capabilities.inference.with_provider("openai", provider),
)
```

The `with_provider(name, provider)` method returns a new
`InferenceCapability` instance with the provider bound. The
artifact's evidence will include `provider: "openai"`.

### 2.8 Write tests with mocks

Mock the upstream API call. The recommended pattern is
`httpx.MockTransport` or `respx`:

```python
import respx
from paxman import normalize


@respx.mock
def test_openai_provider_returns_completion():
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "ACME Corp"}}],
                "model": "gpt-5",
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            },
        )
    )

    # Register the provider, then call paxman.normalize(...)
    ...
```

Property tests should verify:

- Same request → same `Completion` shape (text + model + usage).
- Non-determinism is recorded in evidence.
- Replay rehydrates the recorded `Completion` without re-invoking
  the provider.

---

## 3. What providers MUST do

- **Resolve secrets by reference** — never embed the secret in the
  artifact or log.
- **Record the model id and version** in the completion evidence.
- **Fail loudly** via `InferenceProviderError` with a structured
  `error_code` and `context` dict.
- **Be retry-safe** — Paxman may retry on transient errors.
- **Preserve the determinism contract** — the recorded evidence is
  the source of truth for replay.

## 4. What providers MUST NOT do

- **Log the API key** or any other secret.
- **Mutate the request** — return a fresh `Completion` based on the
  request.
- **Cache the completion** in a way that breaks determinism (the
  Executor will not re-invoke, but the artifact must reflect what
  was actually returned).
- **Embed provider secrets** in the artifact.

---

## 5. Stub vs real providers

V1 ships a **stub provider** (`StubInferenceProvider`) that
returns a fixed completion. A test-only variant
(`CyclingStubInferenceProvider`) cycles through 3 fixed vendor
names to simulate the non-determinism of a real provider.

When you ship a real provider, the artifact's evidence will record
`provider: "<your-name>"` and the model id. Replay will rehydrate
the artifact without re-invoking your provider, so the recorded
completion is what the artifact always returns.

---

## 6. The full SPI walkthrough

For the full SPI walkthrough (including a longer example, the
`Completion` data model, and a worked OpenAI-style provider), see
[EXTENDING.md §3](../../EXTENDING.md).

---

## 7. See also

- [EXTENDING.md §3](../../EXTENDING.md) — full SPI walkthrough.
- [docs/concepts/capabilities.md](../concepts/capabilities.md) —
  what a capability is in Paxman.
- [SECURITY.md §3](../../SECURITY.md) — provider secrets policy.
- [paxman.capabilities.v1.inference](../../EXTENDING.md) — the
  `InferenceProvider` SPI and the stub providers.
- [tests/unit/test_capability_inference.py](../../EXTENDING.md) —
  the stub provider tests (a useful template for real providers).
