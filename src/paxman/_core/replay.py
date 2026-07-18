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
from paxman import _orchestrator_runtime
from paxman._core.artifact import ExecutionArtifact
from paxman._core.engine_env import Engine, _verify_recorded_authorities
from paxman._dsl.parser import parse_contract
from paxman._errors import (
    CanonicalizationError,
    ContractError,
    VersionMismatchError,
)


def replay(artifact: ExecutionArtifact, contract: Any) -> ExecutionArtifact:
    """Rehydrate `artifact` from its stored form, without re-execution.

    Mandate Law 12: `replay(artifact) == artifact` byte-for-byte.

    Replay reconstructs the exact production Engine from the editions
    recorded on the artifact (``Engine.from_artifact``), so a newer edition
    shipped since the artifact was produced does not change the result. A
    recorded edition that is neither the active edition nor a known historical
    edition is rejected (``UnknownAuthorityEdition`` surfaces as the replay
    failure), protecting artifact integrity.
    """
    try:
        parsed_contract = parse_contract(contract)
    except ContractError as exc:
        # Replay requires a contract the parser accepts; otherwise the
        # artifact's stored contract and the caller's contract are
        # effectively from different versions. Map to VersionMismatchError
        # per mandate Law 8 (fail informatively, totality-preserving on
        # rejection).
        raise VersionMismatchError(f"cannot replay: contract could not be parsed: {exc}") from exc

    # Verify the VersionStamp.
    expected_paxman = _paxman_version.__version__
    if artifact.version_stamp.paxman_version != expected_paxman:
        raise VersionMismatchError(
            f"paxman version mismatch: artifact is {artifact.version_stamp.paxman_version!r}, "
            f"current is {expected_paxman!r}"
        )
    if artifact.version_stamp.contract_version != parsed_contract.version_field:
        raise VersionMismatchError(
            f"contract version mismatch: artifact is {artifact.version_stamp.contract_version}, "
            f"contract is {parsed_contract.version_field}"
        )

    current_hash = _orchestrator_runtime.default_registry.capabilities_hash()
    if artifact.version_stamp.capabilities_hash != current_hash:
        raise VersionMismatchError(
            f"capabilities hash mismatch: "
            f"artifact is {artifact.version_stamp.capabilities_hash!r}, "
            f"current is {current_hash!r}"
        )

    # Verify the replay_hash (mandate Law 12): independently recompute from the
    # canonical bytes rather than trusting the stored value. This is the
    # authoritative integrity guard and runs before any edition interpretation.
    if artifact.replay_hash != _compute_replay_hash(artifact):
        raise CanonicalizationError(
            "replay_hash mismatch: artifact content does not match its stored hash"
        )

    # Reconstruct the exact production Engine from the recorded editions
    # (Concern 2): recorded editions are reused verbatim, merged over the
    # active roster, so a newer edition shipped since production does not
    # change the result. This runs after the hash guard so a hash failure
    # surfaces first (the artifact is already proven intact).
    Engine.from_artifact(artifact.authorities)

    # Verify the recorded authority editions are still known. This is the
    # informative (Law 8) failure path: it names *which* authority is
    # retired/forged rather than leaving the caller to diff the replay hash.
    _verify_recorded_authorities(artifact.authorities)

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
