"""ExecutionArtifact: the immutable result of a canonicalize call.

Mandate Laws 1, 2, 9, 12, 13 all converge here. The artifact is the
single thing that paxman produces and replays.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Protocol

import attrs

from paxman._core.types import Evidence, Status, VersionStamp


class _ContractLike(Protocol):
    """What ExecutionArtifact needs from a Contract.

    The real Contract (in src/paxman/_contracts/contract.py) provides
    this and more. Keeping the dependency here as a Protocol avoids
    a forward import.
    """

    def as_dict(self) -> dict[str, Any]: ...
    @property
    def version(self) -> int: ...


@attrs.frozen
class ExecutionArtifact:
    """The immutable result of `paxman.canonicalize`.

    Mandate Law 13: no field may be reassigned after construction. The
    only way to "modify" an artifact is to produce a new one via a new
    canonicalize call.
    """

    status: Status
    value: str | None
    evidence: tuple[Evidence, ...]
    contract: _ContractLike
    version_stamp: VersionStamp
    replay_hash: str = attrs.field(init=False, eq=False)

    def __attrs_post_init__(self) -> None:
        # The replay_hash is computed from the artifact's content
        # (excluding itself). It is set in __attrs_post_init__ so that
        # callers cannot forget to provide it.
        payload = {
            "status": self.status.value,
            "value": self.value,
            "evidence": [(e.rule, e.detail) for e in self.evidence],
            "contract": self.contract.as_dict(),
            "version_stamp": {
                "paxman_version": self.version_stamp.paxman_version,
                "contract_version": self.version_stamp.contract_version,
                "capabilities_hash": self.version_stamp.capabilities_hash,
                "configuration_version": self.version_stamp.configuration_version,
            },
        }
        canonical = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        digest = hashlib.sha256(canonical).hexdigest()
        object.__setattr__(self, "replay_hash", digest)

    def canonical_bytes(self) -> bytes:
        """The deterministic byte serialization used for replay_hash.

        Identical to the bytes used at construction time. Returned as a
        method (rather than cached) for simplicity; the cost is one
        json.dumps per call, which is acceptable for v1.0.0.
        """
        payload = {
            "status": self.status.value,
            "value": self.value,
            "evidence": [(e.rule, e.detail) for e in self.evidence],
            "contract": self.contract.as_dict(),
            "version_stamp": {
                "paxman_version": self.version_stamp.paxman_version,
                "contract_version": self.version_stamp.contract_version,
                "capabilities_hash": self.version_stamp.capabilities_hash,
                "configuration_version": self.version_stamp.configuration_version,
            },
        }
        return json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
