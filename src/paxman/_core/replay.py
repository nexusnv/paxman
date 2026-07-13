"""Replay: byte-equal rehydration of an ExecutionArtifact (mandate Law 12).

`replay(artifact, contract)`:
1. Re-parses the contract from its DSL form.
2. Verifies the artifact's VersionStamp matches the current environment.
3. Verifies the artifact's replay_hash matches sha256(canonical_bytes()).
4. Returns the artifact.

Replay either returns the artifact (byte-equal) or raises
`VersionMismatchError` / `CanonicalizationError`. There is no `Status`
on the replay path — the input artifact is already complete.
"""
from __future__ import annotations

import hashlib
from typing import Any

import paxman as _paxman_version

from paxman._contracts.contract import parse_contract
from paxman._core.artifact import ExecutionArtifact
from paxman._errors import (
    CanonicalizationError,
    ContractError,
    VersionMismatchError,
)
from paxman import _orchestrator_runtime


def replay(artifact: ExecutionArtifact, contract: Any) -> ExecutionArtifact:
    """Rehydrate `artifact` from its stored form, without re-execution.

    Mandate Law 12: `replay(artifact) == artifact` byte-for-byte.
    """
    try:
        parsed_contract = parse_contract(contract)
    except ContractError as exc:
        # Replay requires a contract the parser accepts; otherwise the
        # artifact's stored contract and the caller's contract are
        # effectively from different versions. Map to VersionMismatchError
        # per mandate Law 8 (fail informatively, totality-preserving on
        # rejection).
        raise VersionMismatchError(
            f"cannot replay: contract could not be parsed: {exc}"
        ) from exc

    # Verify the VersionStamp.
    expected_paxman = _paxman_version.__version__
    if artifact.version_stamp.paxman_version != expected_paxman:
        raise VersionMismatchError(
            f"paxman version mismatch: artifact is {artifact.version_stamp.paxman_version!r}, "
            f"current is {expected_paxman!r}"
        )
    if artifact.version_stamp.contract_version != parsed_contract.version:
        raise VersionMismatchError(
            f"contract version mismatch: artifact is {artifact.version_stamp.contract_version}, "
            f"contract is {parsed_contract.version}"
        )

    current_hash = _orchestrator_runtime.default_registry.capabilities_hash()
    if artifact.version_stamp.capabilities_hash != current_hash:
        raise VersionMismatchError(
            f"capabilities hash mismatch: artifact is {artifact.version_stamp.capabilities_hash!r}, "
            f"current is {current_hash!r}"
        )

    # Verify the replay_hash.
    if artifact.replay_hash != _compute_replay_hash(artifact):
        raise CanonicalizationError(
            "replay_hash mismatch: artifact content does not match its stored hash"
        )

    return artifact


def _compute_replay_hash(artifact: ExecutionArtifact) -> str:
    """Independently recompute the replay_hash from the artifact's
    canonical bytes (mandate Law 12).

    This is the verification side of the hash. The constructor stored
    `artifact.replay_hash` from the same `canonical_bytes()` at
    construction time, so the two values must match. Recomputing
    independently — rather than reading the stored value — means a
    forged artifact with mismatched fields is detected at replay time,
    not just trusted because the field is frozen.
    """
    return hashlib.sha256(artifact.canonical_bytes()).hexdigest()
