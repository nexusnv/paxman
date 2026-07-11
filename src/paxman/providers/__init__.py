"""``paxman.providers`` — public entry point for the V1.2.0 inference layer.

This subpackage ships the public SPI for real inference providers
(``ModelRef``, ``Provider``, ``ProviderRegistry``, ``SecretResolver``,
``EnvSecretResolver``, ``PricingResolver``, ``PricingTuple``,
``StaticPricingResolver``, ``register_provider``, ``register``,
``get_default_registry``, ``set_default_registry``).

Loading is lazy via PEP 562 ``__getattr__``. Importing
``paxman.providers`` does NOT eagerly load any of the SPI classes
— the first attribute access resolves them.

Plan 1/4 (issue #51) ships only the core SPI. Plan 2/4 (issue #119)
adds the router, factory, and strategies; plan 3/4 (issue #120)
adds the vendor provider modules (``openai_compatible``,
``openai``, ``anthropic``). The pre-declared ``_LAZY_EXPORTS``
and ``_VENDOR_MODULES`` maps in this file are kept minimal for
plan 1/4; subsequent plans amend the maps to add their entries.

Design spec: issue #50 (``.sisyphus/specs/2026-07-09-v120-inference-providers-design.md``).
Implementation plan: issues #51, #119, #120, #121.
"""

from __future__ import annotations

import importlib
import typing

if typing.TYPE_CHECKING:
    from paxman.providers._model import ModelRef, ProviderRegistry
    from paxman.providers._pricing import (
        PricingResolver,
        PricingTuple,
        StaticPricingResolver,
    )
    from paxman.providers._provider import Provider
    from paxman.providers._resolver import EnvSecretResolver, SecretResolver

# The default global registry is a process-wide singleton. It is
# created on first access via get_default_registry(). Callers who
# need a separate registry (multi-tenant, tests, dual-environment)
# instantiate ProviderRegistry() directly and pass it explicitly
# to register_provider() / set_default_registry().
_DEFAULT_REGISTRY: object = None


def get_default_registry() -> ProviderRegistry:
    """Return the process-wide default :class:`ProviderRegistry`.

    The registry is lazily initialized on first call. Multi-tenant
    and test callers should create their own :class:`ProviderRegistry`
    and pass it explicitly to :func:`register_provider` /
    :func:`set_default_registry`.

    Returns:
        The default :class:`ProviderRegistry` (singleton).
    """
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        # Lazy import to keep cold-start fast.
        from paxman.providers._model import ProviderRegistry

        _DEFAULT_REGISTRY = ProviderRegistry()
    return typing.cast("ProviderRegistry", _DEFAULT_REGISTRY)


def set_default_registry(registry: ProviderRegistry) -> None:
    """Replace the process-wide default :class:`ProviderRegistry`.

    Useful for tests and for callers that want a custom default
    (e.g. a multi-tenant app with a per-process registry
    pre-populated from configuration).

    Args:
        registry: The :class:`ProviderRegistry` to use as the
            default. Subsequent calls to :func:`get_default_registry`
            return this instance. Pass an empty
            :class:`ProviderRegistry` to reset.
    """
    global _DEFAULT_REGISTRY
    _DEFAULT_REGISTRY = registry


def register_provider(
    name: str,
    provider: Provider,
    *,
    replace: bool = False,
    registry: ProviderRegistry | None = None,
) -> None:
    """Register a provider in a :class:`ProviderRegistry`.

    Canonical entry point for registration. Writes to the supplied
    ``registry`` (or the default global if ``registry`` is ``None``).

    Args:
        name: The registration name. Must be unique within
            ``registry`` unless ``replace=True``.
        provider: The :class:`Provider` instance. Must expose
            ``name``, ``capabilities``, and ``complete(request)``.
        replace: If ``True``, allow replacing an existing
            registration under the same name. Defaults to ``False``.
        registry: The :class:`ProviderRegistry` to register into.
            Defaults to ``None``, which means "use
            :func:`get_default_registry`."

    Raises:
        ValueError: If ``name`` is not a non-empty string.
        TypeError: If ``provider`` does not implement the
            :class:`Provider` Protocol.
        ConfigurationError: If ``name`` is already registered and
            ``replace=False``.
    """
    if registry is None:
        registry = get_default_registry()
    registry.register(name, provider, replace=replace)


def register(
    provider: Provider,
    *,
    replace: bool = False,
    registry: ProviderRegistry | None = None,
) -> None:
    """Sugar over :func:`register_provider` that reads ``provider.name``.

    Args:
        provider: The :class:`Provider` instance. Its ``name``
            attribute is the registration key.
        replace: If ``True``, allow replacing an existing
            registration under the same name. Defaults to ``False``.
        registry: The :class:`ProviderRegistry` to register into.
            Defaults to ``None`` (the default global).

    Raises:
        AttributeError: If ``provider`` does not have a ``name``
            attribute.
    """
    if not hasattr(provider, "name"):
        raise AttributeError(
            "register(provider) requires provider.name; "
            "use register_provider(name, provider) to specify explicitly"
        )
    register_provider(provider.name, provider, replace=replace, registry=registry)


# ---------------------------------------------------------------------------
# PEP 562 lazy attribute resolution
# ---------------------------------------------------------------------------


# Plan 1/4 ships only the core SPI. Plans 2/4 (router, factory) and
# 3/4 (vendor providers) amend this map to add their entries. Each
# value is (module_path, attribute_name).
_LAZY_EXPORTS: typing.Final[dict[str, tuple[str, str]]] = {
    # (module, attribute)
    "ModelRef": ("paxman.providers._model", "ModelRef"),
    "ProviderRegistry": ("paxman.providers._model", "ProviderRegistry"),
    "Provider": ("paxman.providers._provider", "Provider"),
    "SecretResolver": ("paxman.providers._resolver", "SecretResolver"),
    "EnvSecretResolver": ("paxman.providers._resolver", "EnvSecretResolver"),
    "PricingResolver": ("paxman.providers._pricing", "PricingResolver"),
    "PricingTuple": ("paxman.providers._pricing", "PricingTuple"),
    "StaticPricingResolver": ("paxman.providers._pricing", "StaticPricingResolver"),
}


def __getattr__(name: str) -> typing.Any:
    """PEP 562 lazy attribute resolution.

    Resolves the public SPI classes from ``_LAZY_EXPORTS`` on first
    access. The class is then cached in ``globals()`` for subsequent
    access (per PEP 562).

    The return type is ``typing.Any`` per PEP 562 (the protocol
    requires it; the resolved object may be any class).
    """
    if name in _LAZY_EXPORTS:
        module_path, attr_name = _LAZY_EXPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value  # cache for subsequent access
        return value
    raise AttributeError(f"module 'paxman.providers' has no attribute {name!r}")


def __dir__() -> list[str]:
    """PEP 562 dir() support: include lazy exports for IDE auto-completion."""
    return sorted(set(list(globals().keys()) + list(_LAZY_EXPORTS.keys())))


__all__ = [
    # Lazy exports (also listed in __dir__):
    "EnvSecretResolver",
    "ModelRef",
    "PricingResolver",
    "PricingTuple",
    "Provider",
    "ProviderRegistry",
    "SecretResolver",
    "StaticPricingResolver",
    "get_default_registry",
    "register",
    "register_provider",
    "set_default_registry",
]
