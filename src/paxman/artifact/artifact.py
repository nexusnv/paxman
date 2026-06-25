"""Execution artifact — the output bundle of a ``paxman.normalize()`` call.

This module defines the two central data models that flow through the
rest of the ``artifact/`` subsystem:

- :class:`FieldResult` — the outcome for one field (value, confidence,
  candidates, provenance).
- :class:`ExecutionArtifact` — the complete output of a normalize call,
  including the resolved data, evidence trail, diagnostics, execution
  plan, and replay hash.

Per ``ADR-0001`` (Field-Centric Planning), results are indexed by field
path. Per ``REPLAY_AND_DETERMINISM.md``, the artifact carries enough
information to rehydrate itself without re-execution — the ``replay_hash``
is the deterministic signature of the captured truth.

Ownership
---------
This module is part of the ``artifact/`` subsystem (Sprint 6). It is
allowed to import from:

- ``paxman.types`` — ``Status``, ``ConfidenceBand`` enum.
- ``paxman.ids`` — ``ARTIFACT_PREFIX``, ``generate_artifact_id``.
- ``paxman.versioning`` — ``PAXMAN_VERSION``, ``PLANNER_VERSION``.
- ``paxman.clock`` — ``Clock``, ``SystemClock`` for timestamp generation.
- ``paxman.capabilities.result`` — ``EvidenceRef``, ``Candidate``, ``Diagnostic``.
- ``paxman.planner.field_plan`` — ``ExecutionPlan``.

It must NOT import from ``paxman.api`` (api layer depends on artifact,
not the other way around).
"""

from __future__ import annotations

import typing

import attrs

from paxman.artifact.statistics import Statistics
from paxman.capabilities.result import Candidate, Diagnostic, EvidenceRef
from paxman.clock import SystemClock
from paxman.ids import generate_artifact_id
from paxman.planner.field_plan import ExecutionPlan
from paxman.types import ConfidenceBand, Status
from paxman.versioning import PAXMAN_VERSION, PLANNER_VERSION

# ---------------------------------------------------------------------------
# FieldResult
# ---------------------------------------------------------------------------

# Field-level status: not all Status values are meaningful per-field.
# SUCCESS, PARTIAL_SUCCESS, and UNRESOLVED are the common ones.
# EXECUTION_FAILED is used when a field's capability chain errors fatally.

_FIELD_VALID_STATUSES: typing.Final[frozenset[str]] = frozenset(
    {
        "SUCCESS",
        "PARTIAL_SUCCESS",
        "UNRESOLVED",
        "EXECUTION_FAILED",
    }
)


@attrs.frozen(slots=True)
class FieldResult:
    """The outcome of resolving one field.

    A :class:`FieldResult` bundles the resolved value (or ``None`` if
    unresolved), the :class:`ConfidenceBand` assigned by the Reconciler,
    the list of :class:`Candidate` values produced by capabilities, and
    the :class:`EvidenceRef` pointers that back the resolution.

    Attributes:
        field_path: The canonical field path (e.g., ``"supplier_name"``).
        value: The resolved value. ``None`` if the field is unresolved
            or the value could not be determined.
        confidence: The :class:`ConfidenceBand` assigned by the
            Reconciler. Defaults to ``UNTRUSTED``.
        candidates: Tuple of :class:`Candidate` records produced by
            capabilities during execution. May be empty.
        evidence_refs: Tuple of :class:`EvidenceRef` pointers that
            support this field's resolution.
        status: The field-level :class:`Status`. One of ``SUCCESS``,
            ``PARTIAL_SUCCESS``, ``UNRESOLVED``, or
            ``EXECUTION_FAILED``.

    Examples:
        >>> FieldResult(
        ...     field_path="supplier_name",
        ...     value="ACME Corp",
        ...     confidence=ConfidenceBand.HIGH,
        ... )
        FieldResult(field_path='supplier_name', value='ACME Corp', ...)
    """

    field_path: str = attrs.field()
    value: typing.Any = None
    confidence: ConfidenceBand = ConfidenceBand.UNTRUSTED
    # V1: always empty — Reconciler consumes candidates during merge.
    # Reserved for future use when per-field candidate history is needed.
    candidates: tuple[Candidate, ...] = ()
    evidence_refs: tuple[EvidenceRef, ...] = ()
    status: Status = Status.UNRESOLVED

    def __attrs_post_init__(self) -> None:
        """Validate invariants."""
        if not isinstance(self.field_path, str) or not self.field_path:
            raise ValueError(f"field_path must be a non-empty string, got {self.field_path!r}")
        if not isinstance(self.status, Status):
            raise TypeError(f"status must be a Status enum, got {type(self.status).__name__}")
        if self.status.value not in _FIELD_VALID_STATUSES:
            raise ValueError(
                f"status must be one of SUCCESS/PARTIAL_SUCCESS/UNRESOLVED/"
                f"EXECUTION_FAILED, got {self.status.value}"
            )
        if not isinstance(self.confidence, ConfidenceBand):
            raise TypeError(
                f"confidence must be a ConfidenceBand, got {type(self.confidence).__name__}"
            )
        if not isinstance(self.candidates, tuple):
            raise TypeError(f"candidates must be a tuple, got {type(self.candidates).__name__}")
        if not isinstance(self.evidence_refs, tuple):
            raise TypeError(
                f"evidence_refs must be a tuple, got {type(self.evidence_refs).__name__}"
            )
        for cand in self.candidates:
            if not isinstance(cand, Candidate):
                raise TypeError(
                    f"candidates must contain Candidate instances, got {type(cand).__name__}"
                )
        for ev_ref in self.evidence_refs:
            if not isinstance(ev_ref, EvidenceRef):
                raise TypeError(
                    f"evidence_refs must contain EvidenceRef instances, got {type(ev_ref).__name__}"
                )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _is_hex64(value: str) -> bool:
    """Return True if *value* is 64 lowercase hex characters."""
    if len(value) != 64:
        return False
    _HEX: typing.Final[frozenset[str]] = frozenset("0123456789abcdef")
    return all(c in _HEX for c in value)


def _now_iso() -> str:
    """Return current UTC time as ISO-8601 string."""
    clock: SystemClock = SystemClock()
    return clock.now().isoformat()


# ---------------------------------------------------------------------------
# ExecutionArtifact
# ---------------------------------------------------------------------------


@attrs.frozen(slots=True)
class ExecutionArtifact:
    """The complete output of a :func:`paxman.normalize()` call.

    An :class:`ExecutionArtifact` captures everything produced during
    normalization — the resolved data, per-field results, evidence
    trail, diagnostics, execution plan, statistics, and a deterministic
    ``replay_hash`` that can later verify the artifact's integrity.

    Per ``REPLAY_AND_DETERMINISM.md`` §2-§3, replay rehydrates the
    artifact from its serialized JSON form and verifies that the hash
    matches. If any field is modified after construction, replay raises
    :class:`HashMismatchError`.

    Required fields per Sprint 6 exit criterion #8:
    ``normalized_data``, ``field_results``, ``unresolved_fields``,
    ``evidence``, ``diagnostics``, ``execution_plan``, ``replay_hash``,
    ``statistics``.

    Attributes:
        id: A unique prefixed identifier (e.g., ``"art_a1b2c3d4e5f6"``).
            Auto-generated if not provided.
        status: The overall :class:`Status` of the normalize call.
        normalized_data: The resolved field values as a flat dict
            keyed by ``field_path``.
        field_results: Dict of ``field_path`` → :class:`FieldResult`.
        unresolved_fields: List of field paths that could not be
            resolved (labels only; full results are in ``field_results``).
        evidence: Tuple of :class:`EvidenceRef` collected across all
            capability invocations.
        diagnostics: Tuple of :class:`Diagnostic` notes from the
            planner, capabilities, executor, and reconciler.
        execution_plan: The :class:`ExecutionPlan` that was executed.
        replay_hash: SHA-256 hex digest covering all hash-relevant
            fields. Empty string before finalisation.
        statistics: An :class:`~paxman.artifact.statistics.Statistics`
            instance measuring execution cost, duration, etc.
        contract_id: The :class:`~paxman.contract.canonical.CanonicalContract.id`
            this artifact was produced from.
        paxman_version: The Paxman library version at creation time.
        planner_version: The planner algorithm version.
        capability_versions: Mapping of capability id → version string
            for all capabilities used during execution.
        metadata: Free-form metadata dict for extensibility.
            Defaults to ``{}``.
        created_at: ISO-8601 UTC timestamp of artifact creation.
            Auto-generated if not provided.
    """

    status: Status = attrs.field()
    id: str = attrs.field(factory=generate_artifact_id)
    normalized_data: dict[str, typing.Any] = attrs.field(factory=dict)
    field_results: dict[str, FieldResult] = attrs.field(factory=dict)
    unresolved_fields: list[str] = attrs.field(factory=list)
    evidence: tuple[EvidenceRef, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    execution_plan: ExecutionPlan | None = None
    replay_hash: str = ""
    statistics: Statistics | None = None
    contract_id: str = ""
    paxman_version: str = PAXMAN_VERSION
    planner_version: str = PLANNER_VERSION
    capability_versions: dict[str, str] = attrs.field(factory=dict)
    metadata: dict[str, typing.Any] = attrs.field(factory=dict)
    created_at: str = attrs.field(
        factory=_now_iso,
    )

    def __attrs_post_init__(self) -> None:
        """Validate invariants."""
        if not isinstance(self.id, str) or not self.id:
            raise ValueError(f"id must be a non-empty string, got {self.id!r}")
        if not isinstance(self.status, Status):
            raise TypeError(f"status must be a Status enum, got {type(self.status).__name__}")
        if not isinstance(self.normalized_data, dict):
            raise TypeError(
                f"normalized_data must be a dict, got {type(self.normalized_data).__name__}"
            )
        if not isinstance(self.field_results, dict):
            raise TypeError(
                f"field_results must be a dict, got {type(self.field_results).__name__}"
            )
        for fp, fr in self.field_results.items():
            if not isinstance(fp, str):
                raise TypeError(f"field_results keys must be strings, got {type(fp).__name__}")
            if not isinstance(fr, FieldResult):
                raise TypeError(
                    f"field_results values must be FieldResult, got "
                    f"{type(fr).__name__} for key {fp!r}"
                )
        if not isinstance(self.evidence, tuple):
            raise TypeError(f"evidence must be a tuple, got {type(self.evidence).__name__}")
        if not isinstance(self.diagnostics, tuple):
            raise TypeError(f"diagnostics must be a tuple, got {type(self.diagnostics).__name__}")
        if not isinstance(self.replay_hash, str):
            raise TypeError(f"replay_hash must be a str, got {type(self.replay_hash).__name__}")
        if self.replay_hash and not _is_hex64(self.replay_hash):
            raise ValueError(
                f"replay_hash must be 64 lowercase hex chars (or empty), got {self.replay_hash!r}"
            )
        if not isinstance(self.paxman_version, str):
            raise TypeError(
                f"paxman_version must be a str, got {type(self.paxman_version).__name__}"
            )
        if not isinstance(self.metadata, dict):
            raise TypeError(f"metadata must be a dict, got {type(self.metadata).__name__}")
        if not isinstance(self.created_at, str) or not self.created_at:
            raise ValueError(
                f"created_at must be a non-empty ISO-8601 string, got {self.created_at!r}"
            )
        if self.execution_plan is not None and not isinstance(self.execution_plan, ExecutionPlan):
            raise TypeError(
                f"execution_plan must be an ExecutionPlan or None, got "
                f"{type(self.execution_plan).__name__}"
            )
        if not isinstance(self.unresolved_fields, list):
            raise TypeError(
                f"unresolved_fields must be a list, got {type(self.unresolved_fields).__name__}"
            )
        for uf in self.unresolved_fields:
            if not isinstance(uf, str):
                raise TypeError(
                    f"unresolved_fields items must be strings, got {type(uf).__name__}"
                )
        if not isinstance(self.contract_id, str):
            raise TypeError(
                f"contract_id must be a string, got {type(self.contract_id).__name__}"
            )
        if not isinstance(self.planner_version, str):
            raise TypeError(
                f"planner_version must be a string, got {type(self.planner_version).__name__}"
            )
        if not isinstance(self.capability_versions, dict):
            raise TypeError(
                f"capability_versions must be a dict, got {type(self.capability_versions).__name__}"
            )
        for k, v in self.capability_versions.items():
            if not isinstance(k, str):
                raise TypeError(
                    f"capability_versions keys must be strings, got {type(k).__name__}"
                )
            if not isinstance(v, str):
                raise TypeError(
                    f"capability_versions values must be strings, got {type(v).__name__}"
                )
        if self.statistics is not None and not isinstance(self.statistics, Statistics):
            raise TypeError(
                f"statistics must be a Statistics or None, got {type(self.statistics).__name__}"
            )


__all__ = [
    "ExecutionArtifact",
    "FieldResult",
]
