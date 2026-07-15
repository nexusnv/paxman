"""Capability result and version stamp for Paxman v2."""

from __future__ import annotations

from typing import TYPE_CHECKING

import attrs

if TYPE_CHECKING:
    from paxman._core.provenance import Evidence
    from paxman._core.status import Status


@attrs.frozen
class VersionStamp:
    """The four-component version stamp recorded on every artifact.

    Replay (mandate Law 12) verifies all four components. Mandate §8
    makes the contract version a first-class component.
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
