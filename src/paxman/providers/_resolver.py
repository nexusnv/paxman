"""``_resolver`` — SecretResolver SPI and EnvSecretResolver default (V1.2.0, spec §7).

The SecretResolver is the boundary between the inference layer and
any secret source. Providers MUST call ``secret_resolver.resolve(ref)``
and MUST NOT read ``os.environ`` directly. The default
``EnvSecretResolver`` accepts refs of the form ``"env:NAME"``; vendor
resolvers (``VaultSecretResolver``, ``AWSSecretsManagerSecretResolver``,
``K8sSecretResolver``) are follow-up packages, not in V1.2.0.
"""

from __future__ import annotations

import os
import typing

from paxman.errors import InferenceProviderError

__all__ = ["EnvSecretResolver", "SecretResolver"]


class SecretResolver(typing.Protocol):
    """SPI: a resolver for secret references.

    Implementations are responsible for fetching a secret from
    wherever it lives (``os.environ``, HashiCorp Vault, AWS Secrets
    Manager, Kubernetes Secrets, etc.). The default implementation,
    :class:`EnvSecretResolver`, reads from ``os.environ``.

    Per spec §7: the only failure modes are
    ``INFERENCE_PROVIDER_KEY_MISSING`` (the ref scheme is recognized
    but the secret is not present) and
    ``INFERENCE_PROVIDER_KEY_REFERENCE`` (the ref scheme is not
    recognized). Both map to ``Status.INVALID_CONTRACT`` at the
    reconciler (per spec §6, ADR-0005).
    """

    def resolve(self, ref: str) -> str:
        """Resolve a secret reference to its plaintext value.

        Args:
            ref: A reference string. The format is
                implementation-defined; the default
                ``EnvSecretResolver`` accepts ``"env:NAME"``.

        Returns:
            The resolved secret value (a string — empty values are
            returned as-is; the caller decides whether an empty
            string is a valid secret).

        Raises:
            paxman.errors.InferenceProviderError: With
                ``error_code="INFERENCE_PROVIDER_KEY_MISSING"`` if the
                scheme is recognized but the secret is not present, or
                ``error_code="INFERENCE_PROVIDER_KEY_REFERENCE"`` if
                the scheme is not recognized.
        """
        ...


class EnvSecretResolver:
    """Default :class:`SecretResolver` that reads from ``os.environ``.

    Accepts refs of the form ``"env:NAME"``. The corresponding
    ``os.environ["NAME"]`` is returned. Empty values are returned
    as-is (the caller decides whether an empty string is a valid
    secret).

    This is the only class in the inference layer that reads
    ``os.environ``. Providers MUST call
    ``secret_resolver.resolve(ref)`` and MUST NOT call
    ``os.environ`` directly.
    """

    _PREFIX: typing.Final[str] = "env:"

    def resolve(self, ref: str) -> str:
        """Resolve ``"env:NAME"`` to ``os.environ["NAME"]``.

        Args:
            ref: The reference string. Must start with ``"env:"``.

        Returns:
            The value of ``os.environ[NAME]``. Empty values are
            returned as-is.

        Raises:
            paxman.errors.InferenceProviderError:
                - ``INFERENCE_PROVIDER_KEY_REFERENCE`` if ``ref`` is
                  not a string or does not start with ``"env:"``.
                - ``INFERENCE_PROVIDER_KEY_MISSING`` if the env var
                  is not set.
        """
        if not isinstance(ref, str) or not ref.startswith(self._PREFIX):
            raise InferenceProviderError(
                f"Secret reference {ref!r} is not recognised; expected 'env:NAME'",
                error_code="INFERENCE_PROVIDER_KEY_REFERENCE",
                context={"ref": ref, "expected_scheme": "env:NAME"},
            )
        name = ref[len(self._PREFIX) :]
        try:
            value = os.environ[name]
        except KeyError as e:
            raise InferenceProviderError(
                f"Environment variable {name!r} is not set",
                error_code="INFERENCE_PROVIDER_KEY_MISSING",
                context={"ref": ref, "env_var": name},
            ) from e
        return value
