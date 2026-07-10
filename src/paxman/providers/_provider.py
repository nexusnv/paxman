"""``_provider`` — the public Provider Protocol (V1.2.0, spec §4).

This Protocol extends the V1.0.0 :class:`InferenceProvider` SPI with
two additions:

- :attr:`Provider.name` — the registration identity (per D11, separate
  from endpoint configuration).
- :attr:`Provider.capabilities` — the set of capability identifiers
  (``"text"``, ``"vision"``, ``"json_mode"``, ``"function_calling"``,
  ``"long_context"``, ``"pii_safe"``, ``"high_precision"``) the
  provider advertises. The :class:`~paxman.providers._router.ModelRouter`
  matches required capabilities against this set.

The Protocol is structural. Conformance is enforced at registration
time by :meth:`paxman.providers._model.ProviderRegistry._validate_provider`.
"""
from __future__ import annotations

import typing

from paxman.capabilities.v1.inference import Completion, CompletionRequest

__all__ = ["Provider"]


class Provider(typing.Protocol):
    """The public inference provider Protocol (V1.2.0).

    Thread-safety: implementations MUST be safe to call from multiple
    threads concurrently. The default providers
    (:class:`~paxman.capabilities.v1.inference.StubInferenceProvider`
    and the V1.2.0 real providers — :class:`OpenAICompatibleProvider`,
    :class:`OpenAIProvider`, :class:`AnthropicProvider`) are
    thread-safe by construction. Custom providers that hold mutable
    state MUST guard it with their own lock; Paxman does not provide
    per-provider locking. (D18)

    Determinism: the ``complete()`` method is the unit of determinism.
    Given the same :class:`CompletionRequest`, two concurrent calls on
    the same provider instance may return different :class:`Completion`
    values (real LLMs are non-deterministic); this is by design and
    does not violate Paxman's replay model — the recorded
    ``Completion`` is what ``replay()`` returns, and replay does not
    re-invoke the provider.

    Attributes:
        name: The registration identity. Used as the key in
            :class:`ProviderRegistry` and as the lookup key when
            resolving a :class:`~paxman.providers._model.ModelRef`.
            Must be unique within a registry. Per D11, the name is a
            short identifier; the endpoint configuration (base URL,
            API key reference, default model) lives on the instance,
            not in the name.
        capabilities: The set of capability identifiers this provider
            advertises. Used by the
            :class:`~paxman.providers._router.ModelRouter` to match
            required capabilities. Known identifiers: ``"text"``,
            ``"vision"``, ``"json_mode"``, ``"function_calling"``,
            ``"long_context"``, ``"pii_safe"``, ``"high_precision"``.

    Examples:
        >>> class MyProvider:
        ...     name = "my-provider"
        ...     capabilities = frozenset({"text", "json_mode"})
        ...     def complete(self, request: CompletionRequest) -> Completion:
        ...         return Completion(text="...", model="...")
    """

    name: str
    capabilities: frozenset[str]

    def complete(self, request: CompletionRequest) -> Completion:
        """Send a :class:`CompletionRequest` to the provider.

        Args:
            request: The request to send.

        Returns:
            The :class:`Completion` produced by the provider.

        Raises:
            paxman.errors.InferenceProviderError: If the provider fails
                (network error, rate limit, missing API key, etc.). The
                ``error_code`` is one of the standardized codes in
                spec §6 (``INFERENCE_PROVIDER_KEY_MISSING``,
                ``INFERENCE_PROVIDER_KEY_REFERENCE``,
                ``INFERENCE_PROVIDER_RATE_LIMITED``,
                ``INFERENCE_PROVIDER_TIMEOUT``,
                ``INFERENCE_PROVIDER_INVALID_RESPONSE``,
                ``INFERENCE_PROVIDER_MODEL_NOT_FOUND``,
                ``INFERENCE_PROVIDER_CAPABILITY_UNSUPPORTED``).
        """
        ...
