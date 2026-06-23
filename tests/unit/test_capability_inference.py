"""Unit tests for :mod:`paxman.capabilities.v1.inference`.

Per Sprint 3 D3.15: V1 ships the ``InferenceProvider`` SPI and a
``StubInferenceProvider`` that returns a hard-coded completion.
Real providers (OpenAI, Anthropic) are V2.
"""

from __future__ import annotations

import pytest

from paxman.capabilities.base import CapabilityContext
from paxman.capabilities.result import DiagnosticCode
from paxman.capabilities.spec import CapabilitySpec, CapabilityTier, CostHint
from paxman.capabilities.v1.inference import (
    Completion,
    CompletionRequest,
    CyclingStubInferenceProvider,
    InferenceCapability,
    InferenceProvider,
    StubInferenceProvider,
    Usage,
)
from paxman.errors import InferenceProviderError

pytestmark = pytest.mark.unit


# --- data models ----------------------------------------------------------


def test_usage_defaults() -> None:
    """Default Usage is all zero."""
    u = Usage()
    assert u.prompt_tokens == 0
    assert u.completion_tokens == 0
    assert u.total_tokens == 0


def test_usage_rejects_negative() -> None:
    with pytest.raises(ValueError, match="token count must be non-negative"):
        Usage(prompt_tokens=-1)


def test_usage_rejects_bool() -> None:
    with pytest.raises(TypeError, match="token count must be an int"):
        Usage(prompt_tokens=True)  # type: ignore[arg-type]


def test_completion_minimal() -> None:
    c = Completion(text="hi", model="stub-v1")
    assert c.text == "hi"
    assert c.model == "stub-v1"
    assert c.usage == Usage()


def test_completion_rejects_non_str_text() -> None:
    with pytest.raises(TypeError, match="text must be a str"):
        Completion(text=42, model="stub-v1")  # type: ignore[arg-type]


def test_completion_rejects_empty_model() -> None:
    with pytest.raises(ValueError, match="model must be a non-empty str"):
        Completion(text="x", model="")


def test_completion_request_defaults() -> None:
    r = CompletionRequest(prompt="hi")
    assert r.prompt == "hi"
    assert r.model == "stub-v1"
    assert r.temperature == 0.0
    assert r.context == {}


def test_completion_request_rejects_non_str_prompt() -> None:
    with pytest.raises(TypeError, match="prompt must be a str"):
        CompletionRequest(prompt=42)  # type: ignore[arg-type]


def test_completion_request_rejects_empty_prompt() -> None:
    """An empty prompt is rejected (matches the documented contract)."""
    with pytest.raises(ValueError, match="prompt must be a non-empty str"):
        CompletionRequest(prompt="")


def test_completion_request_rejects_invalid_temperature() -> None:
    with pytest.raises(ValueError, match="temperature must be in"):
        CompletionRequest(prompt="x", temperature=-0.1)
    with pytest.raises(ValueError, match="temperature must be in"):
        CompletionRequest(prompt="x", temperature=2.5)


# --- stub provider -------------------------------------------------------


def test_stub_returns_stub_completion() -> None:
    """The stub returns a hard-coded completion with model 'stub-v1'."""
    stub = StubInferenceProvider()
    c = stub.complete(CompletionRequest(prompt="Hello, world"))
    assert c.text == "<stub: Hello, world>"
    assert c.model == "stub-v1"


def test_stub_truncates_long_prompts() -> None:
    """Prompts > 64 chars are truncated in the stub response."""
    stub = StubInferenceProvider()
    long_prompt = "x" * 100
    c = stub.complete(CompletionRequest(prompt=long_prompt))
    assert c.text == f"<stub: {'x' * 64}>"


def test_stub_never_makes_network_calls() -> None:
    """Sprint 3 risk register: the stub must never make network calls.

    This test asserts the stub has no network-related attributes or
    methods (e.g., ``requests``, ``httpx``, ``urllib3``, etc.). A
    future contributor who tries to add real-provider behavior to
    the stub will be caught by this check.
    """
    stub = StubInferenceProvider()
    forbidden = ("requests", "httpx", "urllib3", "aiohttp", "socket")
    for attr in forbidden:
        assert not hasattr(stub, attr), (
            f"StubInferenceProvider must not depend on {attr!r} (network access forbidden)"
        )


# --- spec + capability ---------------------------------------------------


def test_spec() -> None:
    cap = InferenceCapability()
    spec = cap.spec
    assert isinstance(spec, CapabilitySpec)
    assert spec.id == "inference"
    assert spec.version == "1.0"
    assert spec.tier is CapabilityTier.REMOTE_INFERENCE
    assert spec.deterministic is False
    assert spec.cost_estimate == CostHint(tokens=500, ms=1500, usd=0.001)


def test_capability_uses_default_stub() -> None:
    cap = InferenceCapability()
    result = cap.invoke(
        CapabilityContext(
            raw_input=b"ACME Corp",
            field_path="supplier_name",
            field_type_name="STRING",
        )
    )
    assert result.candidates[0].value == "<stub: ACME Corp>"
    assert result.candidates[0].evidence_refs[0].model_id == "stub-v1"
    # Inference is untrusted by default.
    assert any(d.code is DiagnosticCode.INFERENCE_OUTPUT_UNTRUSTED for d in result.diagnostics)


def test_capability_uses_custom_provider() -> None:
    """A custom provider is used when supplied via config."""

    class _EchoProvider:
        def complete(self, request: CompletionRequest) -> Completion:
            return Completion(text=f"echo: {request.prompt}", model="echo-v1")

    cap = InferenceCapability()
    result = cap.invoke(
        CapabilityContext(
            raw_input=b"hi",
            field_path="x",
            field_type_name="STRING",
            config={"provider": _EchoProvider(), "model": "echo-v1"},
        )
    )
    assert result.candidates[0].value == "echo: hi"
    assert result.candidates[0].evidence_refs[0].model_id == "echo-v1"


def test_capability_handles_provider_error() -> None:
    """A provider that raises InferenceProviderError returns a diagnostic."""

    class _BoomProvider:
        def complete(self, request: CompletionRequest) -> Completion:
            raise InferenceProviderError(
                "kaboom",
                error_code="INFERENCE_PROVIDER_ERROR",
                context={"reason": "test"},
            )

    cap = InferenceCapability()
    result = cap.invoke(
        CapabilityContext(
            raw_input=b"hi",
            field_path="x",
            field_type_name="STRING",
            config={"provider": _BoomProvider()},
        )
    )
    assert result.candidates == ()
    assert result.diagnostics[0].code is DiagnosticCode.INFERENCE_PROVIDER_ERROR


def test_capability_rejects_provider_without_complete() -> None:
    """A non-provider config returns an error diagnostic."""

    class _NotAProvider:
        pass

    cap = InferenceCapability()
    result = cap.invoke(
        CapabilityContext(
            raw_input=b"hi",
            field_path="x",
            field_type_name="STRING",
            config={"provider": _NotAProvider()},
        )
    )
    assert result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED


# --- SPI ------------------------------------------------------------------


def test_inference_provider_is_protocol() -> None:
    """InferenceProvider is a typing.Protocol; custom providers that
    implement ``complete(request) -> Completion`` are accepted
    structurally (PEP 544)."""
    assert hasattr(InferenceProvider, "complete")


# --- CyclingStubInferenceProvider (Sprint 4 D4.9) --------------------


def test_cycling_stub_returns_three_strings_in_rotation() -> None:
    """The cycling stub cycles through 3 fixed strings."""
    stub = CyclingStubInferenceProvider()
    r1 = stub.complete(CompletionRequest(prompt="hello"))
    r2 = stub.complete(CompletionRequest(prompt="hello"))
    r3 = stub.complete(CompletionRequest(prompt="hello"))
    r4 = stub.complete(CompletionRequest(prompt="hello"))
    assert r1.text == "ACME Corp"
    assert r2.text == "Globex Industries"
    assert r3.text == "Initech LLC"
    # The cycle wraps.
    assert r4.text == "ACME Corp"


def test_cycling_stub_uses_prompt_independent_rotation() -> None:
    """The cycling is prompt-independent: same prompt yields different completions."""
    stub = CyclingStubInferenceProvider()
    r1 = stub.complete(CompletionRequest(prompt="first prompt"))
    r2 = stub.complete(CompletionRequest(prompt="different prompt"))
    assert r1.text != r2.text


def test_cycling_stub_records_call_count() -> None:
    stub = CyclingStubInferenceProvider()
    assert stub.call_count == 0
    stub.complete(CompletionRequest(prompt="x"))
    assert stub.call_count == 1
    stub.complete(CompletionRequest(prompt="y"))
    assert stub.call_count == 2
    stub.reset()
    assert stub.call_count == 0


def test_cycling_stub_after_reset_starts_from_first() -> None:
    stub = CyclingStubInferenceProvider()
    stub.complete(CompletionRequest(prompt="x"))  # 0: "ACME Corp"
    stub.complete(CompletionRequest(prompt="x"))  # 1: "Globex Industries"
    stub.reset()
    assert stub.complete(CompletionRequest(prompt="x")).text == "ACME Corp"


def test_cycling_stub_reports_token_usage() -> None:
    """The cycling stub records prompt + completion token counts."""
    stub = CyclingStubInferenceProvider()
    r = stub.complete(CompletionRequest(prompt="hello world"))
    assert r.usage.prompt_tokens == len("hello world")
    assert r.usage.completion_tokens == len(r.text)
    assert r.usage.total_tokens == r.usage.prompt_tokens + r.usage.completion_tokens


def test_cycling_stub_accepts_custom_texts() -> None:
    stub = CyclingStubInferenceProvider(texts=("A", "B"))
    assert stub.complete(CompletionRequest(prompt="x")).text == "A"
    assert stub.complete(CompletionRequest(prompt="x")).text == "B"
    # Wrap.
    assert stub.complete(CompletionRequest(prompt="x")).text == "A"


def test_cycling_stub_rejects_empty_texts() -> None:
    with pytest.raises(ValueError, match="texts must be non-empty"):
        CyclingStubInferenceProvider(texts=())


def test_cycling_stub_rejects_non_tuple_texts() -> None:
    with pytest.raises(TypeError, match="texts must be a tuple"):
        CyclingStubInferenceProvider(texts=["A", "B"])  # type: ignore[arg-type]


def test_cycling_stub_rejects_non_string_texts() -> None:
    with pytest.raises(TypeError, match="texts\\[0\\] must be a str"):
        CyclingStubInferenceProvider(texts=(1, "B"))  # type: ignore[arg-type]


def test_cycling_stub_rejects_empty_model_id() -> None:
    with pytest.raises(ValueError, match="model_id must be a non-empty str"):
        CyclingStubInferenceProvider(model_id="")


def test_cycling_stub_in_capability_uses_config_provider() -> None:
    """The cycling stub can be plugged into the inference capability via config."""
    cap = InferenceCapability()
    cycling = CyclingStubInferenceProvider()
    r1 = cap.invoke(
        CapabilityContext(
            raw_input=b"hi",
            field_path="x",
            field_type_name="STRING",
            config={"provider": cycling, "model": "stub-cycle-v1"},
        )
    )
    r2 = cap.invoke(
        CapabilityContext(
            raw_input=b"hi",
            field_path="x",
            field_type_name="STRING",
            config={"provider": cycling, "model": "stub-cycle-v1"},
        )
    )
    # The cycling stub returns different completions for
    # sequential calls; the inference capability surfaces
    # them as distinct candidate values.
    assert r1.candidates[0].value != r2.candidates[0].value
    # The model id is recorded in the evidence.
    assert r1.candidates[0].evidence_refs[0].model_id == "stub-cycle-v1"


def test_cycling_stub_never_makes_network_calls() -> None:
    """Sprint 3 risk register applies to the cycling stub too."""
    stub = CyclingStubInferenceProvider()
    forbidden = ("requests", "httpx", "urllib3", "aiohttp", "socket")
    for attr in forbidden:
        assert not hasattr(stub, attr), f"CyclingStubInferenceProvider must not depend on {attr!r}"
