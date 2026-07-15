"""Canonicalization outcome status for Paxman v2."""

from __future__ import annotations

import enum


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
