"""Leaf value types shared across the paxman v2 core.

All types in this module are immutable. They are the smallest units of
state paxman manipulates and the boundary at which mandate Laws 1, 2, 9,
and 12 are enforced.
"""

from __future__ import annotations

import enum
from typing import Literal

import attrs


class Status(enum.Enum):
    """The five mutually-exclusive outcomes of a canonicalize call.

    Mandate Law 8: every failure is deterministic. Status values are the
    *outcomes* recorded on a successful ExecutionArtifact; they are not
    exceptions. Exceptions are reserved for calls that cannot proceed at
    all (broken contract, version mismatch, internal invariant violation).
    """

    CANONICALIZED = "canonicalized"
    INVALID = "invalid"
    MISSING = "missing"
    AMBIGUOUS = "ambiguous"
    UNSUPPORTED = "unsupported"


@attrs.frozen
class Evidence:
    """One entry on an ExecutionArtifact's evidence list (mandate Law 9)."""

    rule: str
    detail: str = ""


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

    `value` is required only when status is CANONICALIZED. The orchestrator
    (src/paxman/_core/orchestrator.py) treats status other than
    CANONICALIZED as the authoritative outcome and ignores `value` in
    those cases.
    """

    status: Status
    value: str | None = None
    evidence: tuple[Evidence, ...] = ()


# Closed enum for provider_aliases in the v1.0.0 contract (mandate §6
# openness about deliberate scope).
ProviderAliasesPolicy = Literal["none", "gmail"]
