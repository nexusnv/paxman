"""ExecutionArtifact: the immutable result of a canonicalize call.

Mandate Laws 1, 2, 9, 12, 13 all converge here. The artifact is the
single thing that paxman produces and replays.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Protocol

import attrs

# Law 13 (artifact immutability): the artifact is frozen; these fields
# are set once at construction. Law 12 (replayability): the
# version stamp + evidence hash make the artifact byte-replayable.
from paxman._core.provenance import Evidence
from paxman._core.result import VersionStamp
from paxman._core.status import Status


class _ContractLike(Protocol):
    """What ExecutionArtifact needs from a Contract.

    The real Contract (in src/paxman/_contracts/contract.py) provides
    this and more. Keeping the dependency here as a Protocol avoids
    a forward import. `version` is a read-only property because
    `CanonicalEmailContract` (the real contract) is `@attrs.frozen`
    and its fields are read-only.
    """

    kind: str

    def as_dict(self) -> dict[str, Any]:
        raise NotImplementedError

    @property
    def version_field(self) -> int:
        raise NotImplementedError


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
    candidates: tuple[str, ...] | None = None
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

        Each `Evidence` entry serializes as a `(rule, detail, authority)`
        triple, where `authority` is the structured citation (or ``None``
        for the allow-listed dispatch invariants). Law 14 binds
        canonical-form derivations to a citation; the `authority` fields
        (name, version, kind, retrieved_at) are included so a changed or
        stale edition breaks the replay hash (mandate Law 12).

        The version stamp additionally records the editions of the
        externally-maintained authorities that produced this artifact's
        evidence, sorted for byte-stability.
        """
        payload = {
            "status": self.status.value,
            "value": self.value,
            "candidates": self.candidates,
            "evidence": [
                (
                    e.rule,
                    e.detail,
                    (
                        (
                            e.authority.name,
                            e.authority.version,
                            e.authority.kind,
                            e.authority.retrieved_at,
                        )
                        if e.authority is not None
                        else None
                    ),
                )
                for e in self.evidence
            ],
            "contract": self.contract.as_dict(),
            "version_stamp": {
                "paxman_version": self.version_stamp.paxman_version,
                "contract_version": self.version_stamp.contract_version,
                "capabilities_hash": self.version_stamp.capabilities_hash,
                "configuration_version": self.version_stamp.configuration_version,
                "spec_versions": dict(sorted(self.version_stamp.spec_versions.items())),
                "registry_versions": dict(sorted(self.version_stamp.registry_versions.items())),
            },
        }
        return json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
