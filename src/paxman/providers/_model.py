"""``_model`` — ModelRef dataclass and ProviderRegistry (V1.2.0, spec §4).

This module is internal (the underscore prefix is the convention). The
public re-exports live in :mod:`paxman.providers` (PEP 562 lazy) and
:mod:`paxman.api.types` (the snapshot-test-gated public surface).
"""

from __future__ import annotations

import threading
import typing

import attrs

from paxman.errors import ConfigurationError

if typing.TYPE_CHECKING:
    # Imported only for type-checker (mypy / pyright). The
    # ``ProviderRegistry._validate_provider`` static check is
    # structural (``hasattr`` + ``callable``), so a runtime import of
    # the Protocol would be a needless circular dependency.
    from paxman.providers._provider import Provider

__all__ = ["ModelRef", "ProviderRegistry"]


# ---------------------------------------------------------------------------
# ModelRef
# ---------------------------------------------------------------------------


@typing.final
@attrs.frozen(slots=True)
class ModelRef:
    """A reference to a specific provider and model.

    Per design spec #50 §4 (D11): provider identity is separate from
    endpoint configuration. The ``provider`` field is a short identifier
    (e.g. ``"openai"``, ``"anthropic"``); the endpoint URL lives on the
    provider instance, not in the name.

    ``ModelRef`` is a frozen :func:`attrs.frozen` dataclass (the v1.1.0
    pattern). The ``__str__`` form is ``"{provider}:{model}"`` — useful
    for display and logging, not for persistence (the recorded model
    id in evidence is the canonical source of truth).

    Attributes:
        provider: The provider registration name (e.g. ``"openai"``,
            ``"anthropic"``). Must be a non-empty string.
        model: The model identifier as the provider expects it (e.g.
            ``"gpt-4o-2024-08-06"``, ``"claude-3-5-sonnet-20241022"``).
            Must be a non-empty string.

    Examples:
        >>> ref = ModelRef(provider="openai", model="gpt-4o-2024-08-06")
        >>> str(ref)
        'openai:gpt-4o-2024-08-06'
    """

    provider: str = attrs.field()
    model: str = attrs.field()

    def __attrs_post_init__(self) -> None:
        """Validate both fields are non-empty strings."""
        if not isinstance(self.provider, str) or not self.provider:
            raise ValueError(f"provider must be a non-empty str, got {self.provider!r}")
        if not isinstance(self.model, str) or not self.model:
            raise ValueError(f"model must be a non-empty str, got {self.model!r}")

    def __str__(self) -> str:
        """Return ``"{provider}:{model}"`` — a round-trippable representation.

        Use ``ModelRef.parse(str(ref))`` (not provided in V1.2.0) to invert
        the format if needed; the round-trip is for display, not for
        persistence. The provider configuration is on the instance, not
        in this string.
        """
        return f"{self.provider}:{self.model}"


# ---------------------------------------------------------------------------
# ProviderRegistry
# ---------------------------------------------------------------------------


class ProviderRegistry:
    """A thread-safe registry of named inference providers.

    Per design spec #50 §4 (D10): the registry is a class, not a global
    singleton. Multi-tenant / test / dual-environment callers create
    their own registry. A default global is exposed via
    :func:`paxman.providers.get_default_registry` for the common case.

    Thread-safety: all mutating and read methods are guarded by an
    internal :class:`threading.RLock` (re-entrant, so nested
    ``resolve`` during ``register`` is safe). Concurrent ``register``
    and ``resolve`` from multiple threads are safe; the registry's
    internal state is always consistent (D18).
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._providers: dict[str, Provider] = {}

    def register(
        self,
        name: str,
        provider: Provider,
        *,
        replace: bool = False,
    ) -> None:
        """Register a provider under ``name``.

        Args:
            name: The registration name. Must be a non-empty string.
            provider: The :class:`Provider` instance. Must expose
                ``name`` and ``capabilities`` attributes and a
                ``complete(request)`` method.
            replace: If ``True``, allow replacing an existing
                registration under the same name. If ``False`` (the
                default), a :class:`ConfigurationError` is raised on
                collision.

        Raises:
            ValueError: If ``name`` is not a non-empty string.
            TypeError: If ``provider`` does not implement the
                :class:`Provider` Protocol.
            ConfigurationError: If ``name`` is already registered and
                ``replace=False``.
        """
        if not isinstance(name, str) or not name:
            raise ValueError(f"name must be a non-empty str, got {name!r}")
        self._validate_provider(provider)
        with self._lock:
            if name in self._providers and not replace:
                raise ConfigurationError(
                    f"Provider {name!r} is already registered; pass replace=True to override",
                    error_code="PROVIDER_ALREADY_REGISTERED",
                    context={"name": name, "replace": replace},
                )
            self._providers[name] = provider

    def resolve(self, ref: ModelRef) -> Provider:
        """Resolve a :class:`ModelRef` to its registered provider.

        The provider's ``name`` attribute is the lookup key (not
        ``ref.provider``). This decouples the registry's internal key
        from the external ``ModelRef`` contract.

        Args:
            ref: The :class:`ModelRef` to resolve.

        Returns:
            The registered :class:`Provider` whose ``name`` equals
            ``ref.provider``.

        Raises:
            ConfigurationError: If no provider with that name is
                registered.
        """
        with self._lock:
            provider = self._providers.get(ref.provider)
        if provider is None:
            raise ConfigurationError(
                f"No provider registered for name {ref.provider!r}",
                error_code="INFERENCE_PROVIDER_NOT_REGISTERED",
                context={"name": ref.provider, "model": ref.model},
            )
        return provider

    def get(self, name: str) -> Provider:
        """Return the provider registered under ``name``.

        Raises:
            ConfigurationError: If no provider is registered under
                that name.
        """
        with self._lock:
            provider = self._providers.get(name)
        if provider is None:
            raise ConfigurationError(
                f"No provider registered for name {name!r}",
                error_code="INFERENCE_PROVIDER_NOT_REGISTERED",
                context={"name": name},
            )
        return provider

    def clear(self) -> None:
        """Remove all registrations. Testing-only; not re-exported publicly."""
        with self._lock:
            self._providers.clear()

    def __contains__(self, name: object) -> bool:
        with self._lock:
            return name in self._providers

    def __len__(self) -> int:
        with self._lock:
            return len(self._providers)

    @staticmethod
    def _validate_provider(provider: object) -> None:
        """Validate that ``provider`` implements the Provider Protocol.

        The check is structural: ``name`` and ``capabilities`` attributes
        plus a callable ``complete``. We do not use ``isinstance``
        against a Protocol (would require runtime-registered Protocols,
        which ``typing.Protocol`` does not provide by default).
        """
        if not hasattr(provider, "name"):
            raise TypeError("provider must have a 'name' attribute (Provider Protocol)")
        name_attr = getattr(provider, "name")
        if not isinstance(name_attr, str):
            raise TypeError(
                f"provider.name must be a str, got {type(name_attr).__name__}"
            )
        if not hasattr(provider, "capabilities"):
            raise TypeError("provider must have a 'capabilities' attribute (Provider Protocol)")
        complete_attr = getattr(provider, "complete", None)
        if not callable(complete_attr):
            raise TypeError("provider must implement complete(request) (Provider Protocol)")
