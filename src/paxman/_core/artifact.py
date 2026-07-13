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
    a forward import. `version` is a read-only property because
    `CanonicalEmailContract` (the real contract) is `@attrs.frozen`
    and its fields are read-only.
    """

    kind: str

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
        # The replay_hash is computed from the artifact's canonical
        # bytes (the single source of truth for the artifact's
        # deterministic serialization). It is set in __attrs_post_init__
        # so callers cannot forget to provide it.
        object.__setattr__(
            self,
            "replay_hash",
            hashlib.sha256(self.canonical_bytes()).hexdigest(),
        )

    def canonical_bytes(self) -> bytes:
        """The deterministic byte serialization used for replay_hash.

        `sort_keys=True` and no insignificant whitespace make the output
        byte-stable across runs; `ensure_ascii=False` preserves UTF-8
        characters (mandate Law 1 — same input -> same bytes).
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
