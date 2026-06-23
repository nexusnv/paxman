"""Truth layer data models and the per-field resolved result.

This module defines the three truth layers (Contract / Candidate / Resolved)
and the :class:`ResolvedResult` data model — the Reconciler's authoritative
output for one field.

Per `ADR-0005` and ``PACKAGE_STRUCTURE.md`` §7.4, the three truth layers are:

- **Contract Truth** — what the caller requires (the canonical contract).
- **Candidate Truth** — what capabilities discovered (the per-field
  candidate results from the Executor).
- **Resolved Truth** — what the Reconciler accepts into the artifact.

The :class:`ResolvedResult` carries the Reconciler's decision for a single
field: the final value, the confidence float, the :class:`ConfidenceBand`,
the evidence, and the resolution status (``"RESOLVED"`` or
``"UNRESOLVED"``).

Per `ADR-0005`, the Reconciler is the **sole** subsystem that assigns
confidence. This module is the only place where
:class:`~paxman.types.ConfidenceBand` values are constructed on the
resolved-output side. (The capability subsystem may read the band for
routing decisions but never assigns it.)
"""

from __future__ import annotations

import enum
import typing

import attrs

from paxman.capabilities.result import Diagnostic, EvidenceRef
from paxman.types import ConfidenceBand

__all__ = ["ResolvedResult", "TruthLayer"]


@enum.unique
class TruthLayer(enum.Enum):
    """The three truth layers in Paxman's reconciliation model.

    Per ``PACKAGE_STRUCTURE.md`` §7.4:

    - :attr:`CONTRACT`: what the caller requires (the canonical contract).
    - :attr:`CANDIDATE`: what capabilities discovered (the per-field
      candidate results from the Executor).
    - :attr:`RESOLVED`: what the Reconciler accepts (the per-field
      :class:`ResolvedResult`).
    """

    CONTRACT = "CONTRACT"
    CANDIDATE = "CANDIDATE"
    RESOLVED = "RESOLVED"


@attrs.frozen(slots=True)
class ResolvedResult:
    """Per-field resolved output from the Reconciler.

    The Reconciler's authoritative output for one field. Carries the
    final value, confidence, evidence, and resolution status.

    Per `ADR-0005`, the Reconciler is the sole authority for confidence.
    No other subsystem may construct a :class:`ResolvedResult`.

    Attributes:
        field_id: The :class:`~paxman.contract.canonical.CanonicalField.id`.
        field_path: The :class:`~paxman.contract.canonical.CanonicalField.path`
            (e.g., ``"supplier_name"``).
        field_type_name: The :class:`~paxman.types.FieldType` value name
            (e.g., ``"STRING"``).
        value: The resolved value, or ``None`` if the field is unresolved.
        confidence: Float in ``[0.0, 1.0]``. The Reconciler is the sole
            authority for this value (per ``ADR-0005``).
        confidence_band: The :class:`ConfidenceBand` derived from
            ``confidence``. Determined by the Reconciler.
        truth_layer: Always :attr:`TruthLayer.RESOLVED` for a successful
            resolution.
        evidence_refs: Tuple of :class:`EvidenceRef` supporting this
            resolution. Defaults to an empty tuple.
        diagnostics: Tuple of :class:`Diagnostic` notes attached to
            this resolution. Defaults to an empty tuple.
        status: ``"RESOLVED"`` or ``"UNRESOLVED"``. Defaults to
            ``"UNRESOLVED"``.
        conflict_detected: ``True`` if the underlying candidates had
            conflicting values. Defaults to ``False``.
        merge_strategy_used: The merge strategy that produced this
            result (e.g., ``"PREFER_BY_EVIDENCE"``). Defaults to ``""``.

    Raises:
        ValueError: If ``field_id`` / ``field_path`` / ``field_type_name``
            is not a non-empty string, if ``confidence`` is outside
            ``[0.0, 1.0]``, if ``status`` is not ``"RESOLVED"`` /
            ``"UNRESOLVED"``, or if status/value invariants are violated.
        TypeError: If any field has the wrong type.

    Examples:
        >>> from paxman.types import ConfidenceBand
        >>> r = ResolvedResult(
        ...     field_id="field_1",
        ...     field_path="supplier_name",
        ...     field_type_name="STRING",
        ...     value="ACME Corp",
        ...     confidence=0.95,
        ...     confidence_band=ConfidenceBand.CERTAIN,
        ...     status="RESOLVED",
        ... )
        >>> r.confidence_band
        <ConfidenceBand.CERTAIN: 'CERTAIN'>
    """

    field_id: str = attrs.field()
    field_path: str = attrs.field()
    field_type_name: str = attrs.field()
    value: typing.Any = None
    confidence: float = 0.0
    confidence_band: ConfidenceBand = ConfidenceBand.UNTRUSTED
    truth_layer: TruthLayer = TruthLayer.RESOLVED
    evidence_refs: tuple[EvidenceRef, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    status: str = "UNRESOLVED"
    conflict_detected: bool = False
    merge_strategy_used: str = ""

    def __attrs_post_init__(self) -> None:
        """Validate invariants.

        Raises:
            TypeError: If any field has the wrong type.
            ValueError: If a structural invariant is violated.
        """
        if not isinstance(self.field_id, str) or not self.field_id:
            raise ValueError(f"field_id must be a non-empty string, got {self.field_id!r}")
        if not isinstance(self.field_path, str) or not self.field_path:
            raise ValueError(f"field_path must be a non-empty string, got {self.field_path!r}")
        if not isinstance(self.field_type_name, str) or not self.field_type_name:
            raise ValueError(
                f"field_type_name must be a non-empty string, got {self.field_type_name!r}"
            )
        # Reject bool sneaking in as a number.
        if isinstance(self.confidence, bool) or not isinstance(self.confidence, (int, float)):
            raise TypeError(
                f"confidence must be a number, got {type(self.confidence).__name__}: "
                f"{self.confidence!r}"
            )
        confidence = float(self.confidence)
        if confidence < 0.0 or confidence > 1.0:
            raise ValueError(f"confidence must be in [0.0, 1.0], got {confidence}")
        if not isinstance(self.confidence_band, ConfidenceBand):
            raise TypeError(
                f"confidence_band must be a ConfidenceBand, got "
                f"{type(self.confidence_band).__name__}"
            )
        if not isinstance(self.truth_layer, TruthLayer):
            raise TypeError(
                f"truth_layer must be a TruthLayer, got {type(self.truth_layer).__name__}"
            )
        if not isinstance(self.evidence_refs, tuple):
            raise TypeError(
                f"evidence_refs must be a tuple, got {type(self.evidence_refs).__name__}"
            )
        if not isinstance(self.diagnostics, tuple):
            raise TypeError(f"diagnostics must be a tuple, got {type(self.diagnostics).__name__}")
        if self.status not in ("RESOLVED", "UNRESOLVED"):
            raise ValueError(f"status must be 'RESOLVED' or 'UNRESOLVED', got {self.status!r}")
        # RESOLVED status requires a non-None value.
        if self.status == "RESOLVED" and self.value is None:
            raise ValueError("status='RESOLVED' requires value to be not None")
        # UNRESOLVED status implies confidence == 0.0.
        if self.status == "UNRESOLVED" and confidence != 0.0:
            raise ValueError("status='UNRESOLVED' requires confidence to be 0.0")
        if not isinstance(self.conflict_detected, bool):
            raise TypeError(
                f"conflict_detected must be a bool, got {type(self.conflict_detected).__name__}"
            )
        if not isinstance(self.merge_strategy_used, str):
            raise TypeError(
                f"merge_strategy_used must be a str, got {type(self.merge_strategy_used).__name__}"
            )
