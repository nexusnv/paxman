"""Top-level :func:`replay` function.

Replay verifies the integrity of a captured
:class:`~paxman.artifact.artifact.ExecutionArtifact` without
re-executing capabilities. Per ``REPLAY_AND_DETERMINISM.md``,
replay is **pure deserialisation**: it rehydrates the artifact
from its serialised form and checks the deterministic
``replay_hash``.
"""

from __future__ import annotations

import logging as _logging

from paxman.protocols import Capability
from paxman.artifact.artifact import ExecutionArtifact
from paxman.artifact.replay import replay_artifact
from paxman.capabilities.registry import get_latest
from paxman.contract.canonical import CanonicalContract
from paxman.contract.registry import adapt as _adapt_contract
from paxman.errors import InvalidContractError

from .normalize import _detect_format

__all__ = [
    "replay",
]


def _detect_and_adapt(contract: object) -> CanonicalContract:
    """Detect format and adapt *contract* to a :class:`CanonicalContract`.

    Duplicated from :mod:`paxman.api.normalize` to avoid a cross-module
    dependency on implementation details.

    Args:
        contract: The external contract.

    Returns:
        The adapted :class:`CanonicalContract`.

    Raises:
        InvalidContractError: If detection or adaptation fails.
    """
    format_id = _detect_format(contract)
    return _adapt_contract(contract, format_id=format_id)


def replay(
    artifact: ExecutionArtifact,
    contract: object,
) -> ExecutionArtifact:
    """Replay a captured artifact against *contract*.

    Replay verifies that the artifact's contents are consistent with
    the original contract and have not been tampered with. It does
    **not** re-execute capabilities, re-plan, or re-reconcile — it
    rehydrates the captured truth from the artifact's serialised
    form and checks the deterministic ``replay_hash``.

    Args:
        artifact: The :class:`~paxman.artifact.artifact.ExecutionArtifact`
            to replay. Must carry a ``replay_hash``.
        contract: The original contract used during normalisation
            (Pydantic ``BaseModel``, :class:`dict`, or :class:`str`).

    Returns:
        The verified :class:`~paxman.artifact.artifact.ExecutionArtifact`
        if replay succeeds.

    Raises:
        ReplayError: If replay fails — version mismatch, hash
            mismatch, or a required capability is no longer
            registered.
        InvalidContractError: If *contract* cannot be adapted to a
            :class:`CanonicalContract`.

    Examples:
        >>> from paxman.api.normalize import normalize
        >>> result = normalize(b"data", {"type": "object", "properties": {}})
        >>> replayed = replay(result, {"type": "object", "properties": {}})
        >>> replayed.replay_hash == result.replay_hash
        True
    """
    # Step 1: Adapt contract for replay verification.
    canonical = _detect_and_adapt(contract)

    # Step 2: Verify artifact integrity.
    registry = _GlobalCapabilityRegistry()
    verified = replay_artifact(artifact, canonical, registry)

    return verified


class _GlobalCapabilityRegistry:
    """Wraps :func:`~paxman.capabilities.registry.get_latest` as a
    :class:`~paxman.artifact.replay.CapabilityRegistry`.
    """

    __slots__ = ()

    def get(self, capability_id: str) -> Capability | None:
        try:
            return get_latest(capability_id)  # type: ignore[return-value]  # paxman.protocols.Capability vs capabilities.base.Capability
        except InvalidContractError:
            _logging.getLogger(__name__).debug(
                "Capability not found during replay", extra={"capability_id": capability_id}
            )
            return None
