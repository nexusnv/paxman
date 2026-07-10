"""Tests for the ``paxman.providers`` public surface (V1.2.0 plan 1/4, Task 7).

The ``paxman.providers`` subpackage exposes the core SPI surface
for the V1.2.0 real inference providers via PEP 562
``__getattr__``. Loading the subpackage is cheap (no SPI classes
are eagerly imported); the first attribute access resolves them.

The default global registry is a process-wide singleton, created
lazily on first call to :func:`get_default_registry`. Multi-tenant
and test callers create their own :class:`ProviderRegistry` and
pass it explicitly to :func:`register_provider` via the ``registry``
keyword.

Plan 1/4 ships only the core SPI (ModelRef, ProviderRegistry,
Provider, SecretResolver, EnvSecretResolver, PricingResolver,
PricingTuple, StaticPricingResolver). The router, factory, and
vendor modules ship in plan 2/4 and plan 3/4 respectively; this
``__init__.py`` is structured to allow plan 2/4 / 3/4 to amend
``_LAZY_EXPORTS`` and ``_VENDOR_MODULES`` without breaking the
plan 1/4 contract.
"""

from __future__ import annotations

import pytest


class TestPackageLoadsCleanly:
    """``import paxman.providers`` must succeed and return the
    subpackage module. No SPI class is eagerly imported."""

    def test_import_subpackage(self) -> None:
        import paxman.providers

        assert paxman.providers is not None
        assert paxman.providers.__name__ == "paxman.providers"


class TestLazyAttributeResolution:
    """The first attribute access on the subpackage resolves the
    SPI class via PEP 562 ``__getattr__``. The class is then cached
    in the module's ``globals()`` for subsequent access."""

    def test_model_ref(self) -> None:
        import paxman.providers
        from paxman.providers._model import ModelRef as _Canonical

        ref = paxman.providers.ModelRef(provider="openai", model="gpt-4o")
        assert ref is not None
        # The PEP 562 caching means subsequent access returns the same object.
        assert paxman.providers.ModelRef is _Canonical

    def test_provider_registry(self) -> None:
        import paxman.providers
        from paxman.providers._model import ProviderRegistry as _Canonical

        reg = paxman.providers.ProviderRegistry()
        assert reg is not None
        assert paxman.providers.ProviderRegistry is _Canonical

    def test_provider(self) -> None:
        import paxman.providers
        from paxman.providers._provider import Provider as _Canonical

        proto = paxman.providers.Provider
        assert proto is not None
        assert paxman.providers.Provider is _Canonical

    def test_secret_resolver(self) -> None:
        import paxman.providers
        from paxman.providers._resolver import SecretResolver as _Canonical

        assert paxman.providers.SecretResolver is _Canonical

    def test_env_secret_resolver(self) -> None:
        import paxman.providers
        from paxman.providers._resolver import EnvSecretResolver as _Canonical

        resolver = paxman.providers.EnvSecretResolver()
        assert resolver is not None
        assert paxman.providers.EnvSecretResolver is _Canonical

    def test_pricing_resolver(self) -> None:
        import paxman.providers
        from paxman.providers._pricing import PricingResolver as _Canonical

        assert paxman.providers.PricingResolver is _Canonical

    def test_pricing_tuple(self) -> None:
        from decimal import Decimal

        import paxman.providers
        from paxman.providers._pricing import PricingTuple as _Canonical

        t = paxman.providers.PricingTuple(
            prompt_usd_per_token=Decimal("0.0000025"),
            completion_usd_per_token=Decimal("0.00001"),
        )
        assert t.prompt_usd_per_token == Decimal("0.0000025")
        assert paxman.providers.PricingTuple is _Canonical

    def test_static_pricing_resolver(self) -> None:
        import paxman.providers
        from paxman.providers._pricing import StaticPricingResolver as _Canonical

        resolver = paxman.providers.StaticPricingResolver()
        assert resolver is not None
        assert paxman.providers.StaticPricingResolver is _Canonical


class TestUnknownAttribute:
    """An unknown attribute access must raise ``AttributeError`` with
    a clear message — not ``ModuleNotFoundError`` or
    ``ConfigurationError``."""

    def test_unknown_attribute_raises_attribute_error(self) -> None:
        import paxman.providers

        with pytest.raises(AttributeError, match="no attribute"):
            _ = paxman.providers.NotARealSymbol


class TestPublicSurface:
    """The subpackage's ``__all__`` lists every public name."""

    def test_all_includes_core_spi(self) -> None:
        import paxman.providers

        # Public functions
        for name in (
            "register_provider",
            "register",
            "get_default_registry",
            "set_default_registry",
        ):
            assert name in paxman.providers.__all__, f"{name} missing from __all__"
        # Lazy exports
        for name in (
            "ModelRef",
            "ProviderRegistry",
            "Provider",
            "SecretResolver",
            "EnvSecretResolver",
            "PricingResolver",
            "PricingTuple",
            "StaticPricingResolver",
        ):
            assert name in paxman.providers.__all__, f"{name} missing from __all__"

    def test_dir_includes_lazy_exports(self) -> None:
        """``dir(paxman.providers)`` must list the lazy exports so
        IDE auto-completion and ``paxman.providers.<TAB>`` work."""

        import paxman.providers

        names = dir(paxman.providers)
        for name in (
            "ModelRef",
            "ProviderRegistry",
            "Provider",
            "SecretResolver",
            "EnvSecretResolver",
            "PricingResolver",
            "PricingTuple",
            "StaticPricingResolver",
        ):
            assert name in names, f"{name} missing from dir()"


class TestRegisterAndDefaultRegistry:
    """``register_provider`` and ``register`` write to a registry;
    ``get_default_registry`` returns a process-wide singleton."""

    def test_get_default_registry_is_singleton(self) -> None:
        import paxman.providers

        r1 = paxman.providers.get_default_registry()
        r2 = paxman.providers.get_default_registry()
        assert r1 is r2

    def test_set_default_registry_replaces(self) -> None:
        import paxman.providers

        original = paxman.providers.get_default_registry()
        try:
            custom = paxman.providers.ProviderRegistry()
            paxman.providers.set_default_registry(custom)
            assert paxman.providers.get_default_registry() is custom
        finally:
            # Restore for test isolation.
            paxman.providers.set_default_registry(original)

    def test_register_provider_default_registry(self) -> None:
        """``register_provider`` with no ``registry`` argument writes
        to the default global."""

        import paxman.providers

        class _Stub:
            name = "stub"
            capabilities = frozenset({"text"})

            def complete(self, request):  # pragma: no cover
                raise NotImplementedError

        original = paxman.providers.get_default_registry()
        try:
            test_reg = paxman.providers.ProviderRegistry()
            paxman.providers.set_default_registry(test_reg)
            paxman.providers.register_provider("stub", _Stub())
            assert "stub" in test_reg
            assert test_reg.get("stub") is not None
        finally:
            paxman.providers.set_default_registry(original)

    def test_register_provider_explicit_registry(self) -> None:
        """``register_provider(..., registry=my_reg)`` writes to the
        supplied registry, NOT the default global."""

        import paxman.providers

        class _Stub:
            name = "stub"
            capabilities = frozenset({"text"})

            def complete(self, request):  # pragma: no cover
                raise NotImplementedError

        original = paxman.providers.get_default_registry()
        try:
            default_reg = paxman.providers.get_default_registry()
            custom_reg = paxman.providers.ProviderRegistry()
            paxman.providers.register_provider("stub", _Stub(), registry=custom_reg)
            assert "stub" in custom_reg
            assert "stub" not in default_reg
        finally:
            paxman.providers.set_default_registry(original)

    def test_register_sugar_reads_name(self) -> None:
        """``register(provider)`` reads ``provider.name``."""

        import paxman.providers

        class _Stub:
            name = "sugar-name"
            capabilities = frozenset({"text"})

            def complete(self, request):  # pragma: no cover
                raise NotImplementedError

        original = paxman.providers.get_default_registry()
        try:
            test_reg = paxman.providers.ProviderRegistry()
            paxman.providers.set_default_registry(test_reg)
            paxman.providers.register(_Stub())
            assert "sugar-name" in test_reg
        finally:
            paxman.providers.set_default_registry(original)

    def test_register_sugar_missing_name_raises(self) -> None:
        import paxman.providers

        class _NoName:
            capabilities = frozenset({"text"})

            def complete(self, request):  # pragma: no cover
                raise NotImplementedError

        with pytest.raises(AttributeError):
            paxman.providers.register(_NoName())  # type: ignore[arg-type]


class TestColdStartImpact:
    """Importing ``paxman.providers`` must not eagerly load the SPI
    modules. The cold-start budget (D9.5) is not regressed."""

    def test_subpackage_load_does_not_load_spi_modules(self) -> None:
        import sys

        # Remove the SPI modules if already loaded (e.g. by the test
        # runner's collection), then re-import the subpackage.
        for mod_name in (
            "paxman.providers",
            "paxman.providers._model",
            "paxman.providers._provider",
            "paxman.providers._resolver",
            "paxman.providers._pricing",
        ):
            sys.modules.pop(mod_name, None)

        import paxman.providers  # noqa: F401

        # The subpackage module is loaded; the SPI modules are NOT.
        assert "paxman.providers" in sys.modules
        assert "paxman.providers._model" not in sys.modules
        assert "paxman.providers._provider" not in sys.modules
        assert "paxman.providers._resolver" not in sys.modules
        assert "paxman.providers._pricing" not in sys.modules
