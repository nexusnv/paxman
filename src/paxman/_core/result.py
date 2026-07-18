"""Capability result and version stamp for Paxman v2."""

from __future__ import annotations

from typing import TYPE_CHECKING

import attrs

if TYPE_CHECKING:
    from paxman._core.provenance import Evidence
    from paxman._core.status import Status


@attrs.frozen
class VersionStamp:
    """The version stamp recorded on every artifact (mandate Law 12).

    Replay (mandate Law 12) verifies every component. Mandate §8 makes the
    contract version a first-class component. The concrete authority editions
    that produced the artifact are recorded on the artifact itself
    (``ExecutionArtifact.authorities``) rather than here — a single source of
    truth that includes grammar, registry, policy, and platform-behaviour
    citations uniformly, and is byte-serialized into the replay hash.
    """

    paxman_version: str
    contract_version: int
    capabilities_hash: str
    configuration_version: str


@attrs.frozen
class CapabilityResult:
    """The value a capability returns from its canonicalize method.

    `value` is required only when status is CANONICALIZED. The engine
    (src/paxman/_core/engine.py) treats status other than
    CANONICALIZED as the authoritative outcome and ignores `value` in
    those cases.
    """

    status: Status
    value: str | None = None
    evidence: tuple[Evidence, ...] = ()
    candidates: tuple[str, ...] | None = None
    # When status is AMBIGUOUS, the sorted tuple of every surviving canonical
    # form (YYYY-MM-DD), exposing the ambiguity instead of guessing
    # (Law 3 — Never Guess). It is set ONLY for AMBIGUOUS outcomes that enumerate
    # finite calendar-day alternatives (e.g. MM/DD vs DD/MM, or century-expanded
    # 2-digit years). AMBIGUOUS outcomes whose ambiguity is not about enumerated
    # days (e.g. a naive datetime) carry candidates=None. For every non-AMBIGUOUS
    # status (CANONICALIZED / INVALID / UNSUPPORTED / MISSING) candidates is
    # always None. The engine enforces this contract in _build_artifact.
