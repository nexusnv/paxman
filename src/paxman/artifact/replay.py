"""Replay rehydration — version checks, capability verification, and tamper detection.

Per ``REPLAY_AND_DETERMINISM.md`` §3, replay rehydrates an
:class:`ExecutionArtifact` from its serialised form and verifies its
integrity **without** re-executing the normalise pipeline:

1. **Type check** — the artifact is a valid :class:`ExecutionArtifact` instance.
2. **Version check** — the artifact's ``paxman_version`` is compatible with
   the running library version (same major, not newer).
3. **Capability check** — all capabilities referenced in
   ``capability_versions`` are still registered in the capability registry.
4. **Hash check** — the ``replay_hash`` matches a recomputation over the
   artifact's hash-relevant fields.

If all checks pass, the artifact is returned unchanged (per
``REPLAY_AND_DETERMINISM.md`` §3).
"""

from __future__ import annotations

import typing

from packaging.version import Version

from paxman.artifact._hash import compute_replay_hash
from paxman.artifact.artifact import ExecutionArtifact
from paxman.contract.canonical import CanonicalContract
from paxman.errors import CapabilityNotFoundError, HashMismatchError, VersionMismatchError
from paxman.protocols import Capability
from paxman.versioning import PAXMAN_VERSION

__all__: list[str] = [
    "CapabilityRegistry",
    "replay_artifact",
]


class CapabilityRegistry(typing.Protocol):
    """Protocol for a capability registry used during replay.

    The registry must provide a ``get`` method that returns a
    :class:`~paxman.protocols.Capability` for a given capability id,
    or ``None`` if the capability is not registered.

    This is a structural protocol (PEP 544) — concrete implementations
    need not inherit from it; they are accepted as long as they satisfy
    the interface.

    Examples:
        >>> class MockRegistry:
        ...     def get(self, capability_id: str) -> Capability | None:
        ...         return None
        >>> isinstance(MockRegistry(), CapabilityRegistry)
        True
    """

    def get(self, capability_id: str) -> Capability | None:
        """Look up a capability by its identifier.

        Args:
            capability_id: The capability's identifier (e.g.,
                ``"regex_extraction"``).

        Returns:
            The :class:`~paxman.protocols.Capability` if found, or
            ``None`` if the capability is not registered.
        """
        ...


def replay_artifact(
    artifact: object,
    contract: CanonicalContract,
    capability_registry: CapabilityRegistry,
) -> ExecutionArtifact:
    """Verify and rehydrate an :class:`ExecutionArtifact` without re-execution.

    Performs the four replay checks in order:

    1. **Type check** — *artifact* must be a non-``None``
       :class:`ExecutionArtifact` instance.
    2. **Version check** — *artifact.paxman_version* must be compatible
       with the running library version (same major version, not newer).
    3. **Capability check** — every capability id in
       *artifact.capability_versions* must be registered in the
       *capability_registry*.
    4. **Hash check** — *artifact.replay_hash* must match a recomputation
       over the artifact's hash-relevant fields (see
       :func:`~paxman.artifact._hash.compute_replay_hash`).

    Args:
        artifact: The artifact to replay.  Must be a non-``None``
            :class:`ExecutionArtifact` instance.
        contract: The :class:`CanonicalContract` that produced the
            artifact.  Currently unused in V1 replay; reserved for
            forward compatibility (V2 may validate field schemas
            during replay).
        capability_registry: A registry implementing the
            :class:`CapabilityRegistry` protocol for looking up
            capabilities by identifier.

    Returns:
        The unchanged *artifact* if all replay checks pass.

    Raises:
        TypeError: If *artifact* is ``None`` or not an
            :class:`ExecutionArtifact` instance.
        VersionMismatchError: If *artifact.paxman_version* is
            incompatible with the current
            :data:`~paxman.versioning.PAXMAN_VERSION` (different major
            version, or artifact is from a newer release).
        CapabilityNotFoundError: If a capability referenced in
            *artifact.capability_versions* is not found in the
            *capability_registry*.
        HashMismatchError: If *artifact.replay_hash* does not match
            the recomputed hash, indicating tampering or corruption.

    Examples:
        >>> from paxman.artifact.artifact import ExecutionArtifact
        >>> from paxman.contract.canonical import CanonicalContract, CanonicalField
        >>> from paxman.types import Status, FieldType
        >>> contract = CanonicalContract(
        ...     id="test",
        ...     fields=(
        ...         CanonicalField(
        ...             id="f1", path="a", name="a",
        ...             type=FieldType.STRING, required=True,
        ...         ),
        ...     ),
        ... )
        >>> art = ExecutionArtifact(status=Status.UNRESOLVED)
        >>> class MockRegistry:
        ...     def get(self, capability_id: str) -> None:
        ...         return None
        >>> result = replay_artifact(art, contract, MockRegistry())
        >>> result is art
        True
    """
    # ------------------------------------------------------------------
    # Check 1: Type — artifact must be a non-None ExecutionArtifact.
    # ------------------------------------------------------------------
    if artifact is None:
        raise TypeError("replay_artifact requires a non-None artifact, got None")
    if not isinstance(artifact, ExecutionArtifact):
        raise TypeError(
            f"replay_artifact requires an ExecutionArtifact, got {type(artifact).__name__}"
        )

    # ------------------------------------------------------------------
    # Check 2: Version — artifact must not be newer or from a different
    #           major version than the running library.
    # ------------------------------------------------------------------
    try:
        current_version: Version = Version(PAXMAN_VERSION)
        artifact_version: Version = Version(artifact.paxman_version)
    except (ValueError, TypeError) as exc:
        raise VersionMismatchError(
            message=(
                f"Cannot parse version: artifact={artifact.paxman_version!r}, "
                f"current={PAXMAN_VERSION!r}"
            ),
            context={
                "artifact_version": artifact.paxman_version,
                "current_version": PAXMAN_VERSION,
                "parse_error": str(exc),
            },
        ) from exc

    if artifact_version.major != current_version.major:
        raise VersionMismatchError(
            message=(
                f"Artifact produced by Paxman {artifact.paxman_version}, "
                f"current version is {PAXMAN_VERSION}: "
                f"major version mismatch"
            ),
            context={
                "artifact_version": artifact.paxman_version,
                "current_version": PAXMAN_VERSION,
            },
        )

    if artifact_version > current_version:
        raise VersionMismatchError(
            message=(
                f"Artifact produced by Paxman {artifact.paxman_version}, "
                f"current version is {PAXMAN_VERSION}: "
                f"artifact is from a newer version"
            ),
            context={
                "artifact_version": artifact.paxman_version,
                "current_version": PAXMAN_VERSION,
            },
        )

    # ------------------------------------------------------------------
    # Check 3: Capability registration — every capability used to
    #          produce the artifact must still be registered.
    # ------------------------------------------------------------------
    for capability_id in artifact.capability_versions:
        capability: Capability | None = capability_registry.get(capability_id)
        if capability is None:
            raise CapabilityNotFoundError(
                message=(f"Capability {capability_id!r} is no longer registered"),
                context={
                    "capability_id": capability_id,
                    "artifact_version": artifact.paxman_version,
                },
            )

    # ------------------------------------------------------------------
    # Check 4: Hash integrity — recompute and compare.
    # ------------------------------------------------------------------
    expected_hash: str = compute_replay_hash(artifact)

    if artifact.replay_hash != expected_hash:
        raise HashMismatchError(
            message=(
                f"Artifact hash mismatch: expected {expected_hash}, got {artifact.replay_hash}"
            ),
            context={
                "expected_hash": expected_hash,
                "actual_hash": artifact.replay_hash,
            },
        )

    return artifact
