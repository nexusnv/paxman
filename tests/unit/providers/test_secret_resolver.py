"""Tests for SecretResolver + EnvSecretResolver (V1.2.0 design spec #50 §7).

Per design spec #50 §7: the SecretResolver is the boundary between
the inference layer and any secret source. The default
``EnvSecretResolver`` accepts refs of the form ``"env:NAME"`` and
reads ``os.environ["NAME"]``. Anything else raises
``INFERENCE_PROVIDER_KEY_REFERENCE``; a missing env var raises
``INFERENCE_PROVIDER_KEY_MISSING``.
"""
from __future__ import annotations

import pytest

from paxman.errors import InferenceProviderError
from paxman.providers._resolver import EnvSecretResolver, SecretResolver


class TestEnvSecretResolver:
    """The default ``EnvSecretResolver`` reads from ``os.environ``."""

    def test_resolve_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PAXMAN_TEST_KEY", "secret-value-123")
        resolver = EnvSecretResolver()
        assert resolver.resolve("env:PAXMAN_TEST_KEY") == "secret-value-123"

    def test_resolve_missing_env_var_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DOES_NOT_EXIST_ANYWHERE", raising=False)
        resolver = EnvSecretResolver()
        with pytest.raises(InferenceProviderError) as exc_info:
            resolver.resolve("env:DOES_NOT_EXIST_ANYWHERE")
        assert exc_info.value.error_code == "INFERENCE_PROVIDER_KEY_MISSING"

    def test_resolve_invalid_ref_scheme_raises(self) -> None:
        """Per spec §7: anything that is not 'env:NAME' raises
        INFERENCE_PROVIDER_KEY_REFERENCE."""
        resolver = EnvSecretResolver()
        with pytest.raises(InferenceProviderError) as exc_info:
            resolver.resolve("vault:secret/foo")
        assert exc_info.value.error_code == "INFERENCE_PROVIDER_KEY_REFERENCE"

    def test_resolve_empty_ref_raises(self) -> None:
        resolver = EnvSecretResolver()
        with pytest.raises(InferenceProviderError) as exc_info:
            resolver.resolve("")
        assert exc_info.value.error_code == "INFERENCE_PROVIDER_KEY_REFERENCE"

    def test_resolve_non_string_raises(self) -> None:
        resolver = EnvSecretResolver()
        with pytest.raises(InferenceProviderError) as exc_info:
            resolver.resolve(None)  # type: ignore[arg-type]
        assert exc_info.value.error_code == "INFERENCE_PROVIDER_KEY_REFERENCE"

    def test_context_includes_ref(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The raised error must include the offending ref in context
        for diagnostic purposes (per spec §6 table)."""
        monkeypatch.delenv("DOES_NOT_EXIST", raising=False)
        resolver = EnvSecretResolver()
        with pytest.raises(InferenceProviderError) as exc_info:
            resolver.resolve("env:DOES_NOT_EXIST")
        assert exc_info.value.context.get("ref") == "env:DOES_NOT_EXIST"

    def test_context_includes_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The KEY_MISSING case must include the env-var name in context
        (not just the ref) — operators need both for diagnostics."""
        monkeypatch.delenv("DOES_NOT_EXIST", raising=False)
        resolver = EnvSecretResolver()
        with pytest.raises(InferenceProviderError) as exc_info:
            resolver.resolve("env:DOES_NOT_EXIST")
        assert exc_info.value.context.get("env_var") == "DOES_NOT_EXIST"

    def test_empty_value_returned_as_is(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An empty env var is returned as-is. The caller decides whether
        an empty string is a valid secret."""
        monkeypatch.setenv("EMPTY_KEY", "")
        resolver = EnvSecretResolver()
        assert resolver.resolve("env:EMPTY_KEY") == ""


class TestSecretResolverProtocol:
    """The SecretResolver Protocol is structural; the type-checker
    uses it for static analysis. At runtime, EnvSecretResolver is
    accepted as a SecretResolver because it exposes ``resolve(ref)``.
    """

    def test_env_resolver_satisfies_protocol(self) -> None:
        resolver: SecretResolver = EnvSecretResolver()
        assert hasattr(resolver, "resolve")
        assert callable(resolver.resolve)
