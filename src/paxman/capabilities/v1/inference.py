"""``inference`` V1 capability — model-backed extraction.

V1 ships only the **SPI** and a **stub provider**. Real providers
(OpenAI, Anthropic, Cohere) are V2 per ``EXTENDING.md`` §3 and the
Sprint 3 scope. The capability exists so the planner's heuristic
chain (steps 4 + 5: local + remote inference) has something to
select; the stub returns hard-coded completions.

Inference provider SPI
----------------------

```python
class InferenceProvider(Protocol):
    def complete(self, request: CompletionRequest) -> Completion: ...
```

The capability takes a provider from :attr:`CapabilityContext.config`
(``ctx.config["provider"]``). The default provider is
:class:`StubInferenceProvider`, which returns
``Completion(text="<stub>", model="stub", usage=Usage(tokens=0))``
for every request.

Note: per the Sprint 3 risk register, the stub is **one class with
one method** that returns a hard-coded completion; it must never
make network calls. A test asserts this.

V1 surface:

- ``input_types`` = ``("STRING", "HTML_TEXT", "MIXED")``
- ``output_type`` = ``"STRING"`` (the model completion).
- ``deterministic`` = ``False`` (the default stub is deterministic
  for testability, but the SPI accommodates non-determinism).
- ``cost_estimate`` = ``(tokens=500, ms=1500, usd=0.001)`` (per
  ``docs/specs/capability-cost-model.md`` §3).
"""

from __future__ import annotations

import typing

import attrs

from paxman.capabilities.base import CapabilityContext
from paxman.capabilities.result import (
    Candidate,
    CapabilityResult,
    Diagnostic,
    DiagnosticCode,
    DiagnosticSeverity,
    EvidenceRef,
)
from paxman.capabilities.spec import CapabilitySpec, CapabilityTier, CostHint
from paxman.errors import InferenceProviderError

__all__ = [
    "Completion",
    "CompletionRequest",
    "InferenceCapability",
    "InferenceProvider",
    "StubInferenceProvider",
    "Usage",
]


# ---------------------------------------------------------------------------
# Provider SPI
# ---------------------------------------------------------------------------


class InferenceProvider(typing.Protocol):
    """SPI: a model provider behind the ``inference`` capability.

    Concrete implementations wrap external LLM or ML services
    (OpenAI, Anthropic, Cohere, local models). The V1 capability
    delegates the actual completion call to a provider that
    satisfies this Protocol.

    Internal
        Not re-exported in the public API. Live providers (V2)
        ship as separate packages (e.g., ``paxman-openai``).
    """

    def complete(self, request: CompletionRequest) -> Completion:
        """Send a :class:`CompletionRequest` to the provider.

        Args:
            request: A :class:`CompletionRequest` describing the
                prompt and any model parameters.

        Returns:
            A :class:`Completion` containing the model response.

        Raises:
            paxman.errors.InferenceProviderError: If the provider
                fails (network error, rate limit, etc.).
        """
        ...


# ---------------------------------------------------------------------------
# Request / Response
# ---------------------------------------------------------------------------


@attrs.frozen(slots=True)
class CompletionRequest:
    """A request to an :class:`InferenceProvider`.

    Attributes:
        prompt: The text to send to the model. Required.
        model: The model identifier (e.g., ``"gpt-4"``,
            ``"stub-v1"``). Defaults to ``"stub-v1"`` (V1 stub).
        max_tokens: Optional cap on completion length. ``None``
            means the provider's default. Defaults to ``None``.
        temperature: Sampling temperature in ``[0.0, 2.0]``.
            Defaults to ``0.0`` (deterministic).
        context: Optional structured request metadata (e.g.,
            the field path being resolved). Defaults to ``{}``.

    Examples:
        >>> CompletionRequest(prompt="Hello", model="stub-v1")
        CompletionRequest(prompt='Hello', model='stub-v1', max_tokens=None, temperature=0.0, context={})
    """

    prompt: str = attrs.field()
    model: str = "stub-v1"
    max_tokens: int | None = None
    temperature: float = 0.0
    context: dict[str, typing.Any] = attrs.field(factory=dict)

    def __attrs_post_init__(self) -> None:
        """Validate ``prompt`` is a non-empty string and ``temperature``
        is in ``[0.0, 2.0]`` (the OpenAI convention; the V1 spec
        uses the same range)."""
        if not isinstance(self.prompt, str):
            raise TypeError(f"prompt must be a str, got {type(self.prompt).__name__}")
        if not isinstance(self.model, str) or not self.model:
            raise ValueError(f"model must be a non-empty str, got {self.model!r}")
        if not isinstance(self.temperature, (int, float)) or isinstance(self.temperature, bool):
            raise TypeError(f"temperature must be a number, got {type(self.temperature).__name__}")
        if not 0.0 <= float(self.temperature) <= 2.0:
            raise ValueError(f"temperature must be in [0.0, 2.0], got {self.temperature}")


@attrs.frozen(slots=True)
class Usage:
    """Token usage for a :class:`Completion`.

    Attributes:
        prompt_tokens: Tokens consumed by the prompt.
        completion_tokens: Tokens generated in the completion.
        total_tokens: Total tokens (``prompt + completion``).
    """

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __attrs_post_init__(self) -> None:
        """Validate non-negative token counts (reject bool-as-int)."""
        for f in (self.prompt_tokens, self.completion_tokens, self.total_tokens):
            if type(f) is not int:
                raise TypeError(f"token count must be an int, got {type(f).__name__}: {f!r}")
            if f < 0:
                raise ValueError(f"token count must be non-negative, got {f}")


@attrs.frozen(slots=True)
class Completion:
    """A :class:`CompletionRequest`'s response.

    Attributes:
        text: The model's text response.
        model: The model identifier (echoed from the request).
        usage: :class:`Usage` token counts. Defaults to a zero
            usage record.

    Examples:
        >>> Completion(text="Hello, world", model="stub-v1")
        Completion(text='Hello, world', model='stub-v1', usage=Usage(...))
    """

    text: str = attrs.field()
    model: str = attrs.field()
    usage: Usage = attrs.field(default=attrs.Factory(Usage))

    def __attrs_post_init__(self) -> None:
        """Validate ``text`` is a ``str`` and ``model`` is a non-empty
        ``str``."""
        if not isinstance(self.text, str):
            raise TypeError(f"text must be a str, got {type(self.text).__name__}")
        if not isinstance(self.model, str) or not self.model:
            raise ValueError(f"model must be a non-empty str, got {self.model!r}")


# ---------------------------------------------------------------------------
# Stub provider
# ---------------------------------------------------------------------------


class StubInferenceProvider:
    """V1 default :class:`InferenceProvider`.

    Returns a hard-coded :class:`Completion` for every request. The
    text is ``"<stub: {prompt[:64]}>"`` and the model is
    ``"stub-v1"``. **Never makes network calls.**

    Per the Sprint 3 risk register, this stub is one class with
    one method; it must not drift toward real-provider behavior.
    A test (``test_stub_never_makes_network_calls``) pins this.
    """

    def complete(self, request: CompletionRequest) -> Completion:
        """Return a hard-coded :class:`Completion`.

        Args:
            request: The :class:`CompletionRequest`. Only the
                ``prompt`` is read (truncated to 64 chars).

        Returns:
            A :class:`Completion` with text
            ``"<stub: {truncated_prompt}>"``.
        """
        text = f"<stub: {request.prompt[:64]}>"
        return Completion(text=text, model="stub-v1", usage=Usage())


#: The default :class:`InferenceProvider` used when no provider is
#: supplied via :attr:`CapabilityContext.config`.
_DEFAULT_PROVIDER: typing.Final[InferenceProvider] = StubInferenceProvider()


# ---------------------------------------------------------------------------
# Capability
# ---------------------------------------------------------------------------


class InferenceCapability:
    """V1 ``inference`` capability.

    Sends a :class:`CompletionRequest` to an :class:`InferenceProvider`
    and returns the response as a single :class:`Candidate`.

    The provider is supplied via :attr:`CapabilityContext.config`
    (``ctx.config["provider"]``). The prompt is built from
    ``ctx.raw_input`` (decoded as UTF-8) plus the field path; the
    model id is ``ctx.config.get("model", "stub-v1")``.

    V1 behavior: the default :class:`StubInferenceProvider` returns
    a hard-coded completion. The capability is still useful — it
    proves the SPI works and lets the planner exercise heuristic
    step 5/6 (local/remote inference).

    Examples:
        >>> cap = InferenceCapability()
        >>> ctx = CapabilityContext(
        ...     raw_input=b"ACME Corp",
        ...     field_path="supplier_name",
        ...     field_type_name="STRING",
        ... )
        >>> result = cap.invoke(ctx)
        >>> result.candidates[0].value
        '<stub: ACME Corp>'
    """

    @property
    def spec(self) -> CapabilitySpec:
        """The :class:`CapabilitySpec` for ``inference@1.0``."""
        return _INFERENCE_SPEC

    def invoke(self, ctx: CapabilityContext) -> CapabilityResult:
        """Run the inference call.

        Args:
            ctx: The :class:`CapabilityContext`. ``ctx.config`` may
                contain:

                - ``"provider"``: an :class:`InferenceProvider`.
                  Defaults to :data:`_DEFAULT_PROVIDER`.
                - ``"model"``: a ``str`` model id. Defaults to
                  ``"stub-v1"``.

        Returns:
            A :class:`CapabilityResult` with one :class:`Candidate`
            containing the completion text, plus an :class:`EvidenceRef`
            with the model id.
        """
        provider = ctx.config.get("provider", _DEFAULT_PROVIDER)
        if not hasattr(provider, "complete"):
            return CapabilityResult(
                candidates=(),
                diagnostics=(
                    Diagnostic(
                        code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                        severity=DiagnosticSeverity.ERROR,
                        message=("inference: config['provider'] does not implement complete()"),
                        context={"field_path": ctx.field_path},
                    ),
                ),
            )
        model = ctx.config.get("model", "stub-v1")
        if not isinstance(model, str) or not model:
            model = "stub-v1"

        prompt = ctx.raw_input.decode("utf-8", errors="replace")
        request = CompletionRequest(
            prompt=prompt,
            model=model,
            context={"field_path": ctx.field_path},
        )

        try:
            completion = provider.complete(request)
        except InferenceProviderError as e:
            return CapabilityResult(
                candidates=(),
                diagnostics=(
                    Diagnostic(
                        code=DiagnosticCode.INFERENCE_PROVIDER_ERROR,
                        severity=DiagnosticSeverity.ERROR,
                        message=str(e),
                        context=e.context,
                    ),
                ),
            )

        evidence = (
            EvidenceRef(
                capability_id="inference",
                capability_version="1.0",
                field_path=ctx.field_path,
                model_id=completion.model,
                context={
                    "usage": {
                        "prompt_tokens": completion.usage.prompt_tokens,
                        "completion_tokens": completion.usage.completion_tokens,
                        "total_tokens": completion.usage.total_tokens,
                    },
                },
            ),
        )
        return CapabilityResult(
            candidates=(Candidate(value=completion.text, evidence_refs=evidence),),
            evidence=evidence,
            diagnostics=(
                Diagnostic(
                    code=DiagnosticCode.INFERENCE_OUTPUT_UNTRUSTED,
                    severity=DiagnosticSeverity.WARNING,
                    message=("inference output is untrusted; Reconciler must validate"),
                    context={"field_path": ctx.field_path, "model": completion.model},
                ),
            ),
        )


#: Singleton spec for ``inference@1.0``. Reused across instances.
_INFERENCE_SPEC: typing.Final[CapabilitySpec] = CapabilitySpec(
    id="inference",
    version="1.0",
    input_types=("STRING", "HTML_TEXT", "MIXED"),
    output_type="STRING",
    cost_estimate=CostHint(tokens=500, ms=1500, usd=0.001),
    tier=CapabilityTier.REMOTE_INFERENCE,
    deterministic=False,
    required_providers=("stub",),
)
