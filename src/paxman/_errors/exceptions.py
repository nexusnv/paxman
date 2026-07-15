"""Error hierarchy for Paxman v2.

Mandate Law 8: exceptions are reserved for calls that *cannot proceed at
all*. Status values (`Invalid`, `Missing`, `Ambiguous`, `Unsupported`,
`Canonicalized`) are outcomes on a successfully-returned artifact, not
exceptions. The hierarchy below lists the cases where a call cannot
proceed and an exception is the right response.
"""

from __future__ import annotations


class PaxmanError(Exception):
    """Base class for all paxman-raised exceptions."""


class CanonicalizationError(PaxmanError):
    """Base class for runtime errors raised during canonicalization.

    A subclass of `PaxmanError`, distinct from the per-call
    `Status` values on a returned artifact.
    """


class AmbiguousInputError(CanonicalizationError):
    """The orchestrator detected multiple claimants; this is normally
    surfaced as `Status.AMBIGUOUS` on the artifact, not raised. Raised
    only in defensive paths that should never run."""


class ContractError(PaxmanError):
    """The contract is malformed or self-contradictory.

    Raised at parse time, not at canonicalize time. (The orchestrator
    catches `ContractError` raised inside the capability and maps to
    `Status.UNSUPPORTED` only when the error is about the *kind*, not
    about the field values.)"""


class UnsupportedContractError(CanonicalizationError):
    """Validation or classification was asked about a contract kind it
    does not know. The orchestrator catches this and yields
    `Status.UNSUPPORTED`."""


class VersionMismatchError(CanonicalizationError):
    """Replay against an artifact whose VersionStamp does not match the
    current environment. Raised by `paxman.replay`; never returned as a
    Status (replay either returns the artifact or raises)."""


class FrozenRegistryError(PaxmanError):
    """A capability was registered after the registry was frozen. Raised
    by `paxman.register_capability` after the first canonicalize call."""


class ConfigurationError(PaxmanError):
    """A capability is structurally invalid (missing `name`, missing
    methods, or duplicate registration). Raised at register time,
    before any canonicalize call."""
