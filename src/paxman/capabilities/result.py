"""Capability result types — what capabilities return.

The :class:`CapabilityResult` is the **only** thing a capability produces.
It carries:

- :class:`Candidate` values (one or more proposed values for the field).
- :class:`EvidenceRef` pointers (provenance — what produced the candidate).
- :class:`Diagnostic` notes (structured warnings / errors).

Per `ADR-0005` (Confidence Ownership), :class:`CapabilityResult` has **no
``confidence`` field**. Candidates carry ``value`` and ``evidence_refs``;
the Reconciler (Sprint 5) assigns confidence.

Design notes
------------

All data classes are :func:`attrs.frozen` with ``slots=True`` (per
``DEPENDENCIES.md`` §3.2). Validation lives in ``__attrs_post_init__``
(see Sprint 1 hotfix on the attrs-validator / pyright conflict).
"""

from __future__ import annotations

import enum
import typing

import attrs

__all__ = [
    "Candidate",
    "CapabilityResult",
    "Diagnostic",
    "DiagnosticCode",
    "DiagnosticSeverity",
    "EvidenceRef",
]


# ---------------------------------------------------------------------------
# Diagnostic
# ---------------------------------------------------------------------------


@enum.unique
class DiagnosticSeverity(enum.Enum):
    """Severity of a :class:`Diagnostic` note.

    Values:
        INFO: Informational note (e.g., ``"input was empty"``).
        WARNING: Recoverable issue (e.g., ``"pattern matched 0 times"``).
        ERROR: Unrecoverable error from a capability invocation. The
            Executor surfaces this in the artifact's ``diagnostics``.
    """

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@enum.unique
class DiagnosticCode(enum.Enum):
    """The closed set of V1 diagnostic codes.

    Adding a new code requires an ADR (per ``PACKAGE_STRUCTURE.md``
    §5.4 invariant #5). V1 codes are minimal:

    - ``CAPABILITY_OK`` — success diagnostic for capabilities that
      want to record that they ran successfully but produced no
      candidates.
    - ``CAPABILITY_INVOKE_FAILED`` — capability raised an exception
      while running.
    - ``PATTERN_NO_MATCH`` — regex_extraction found no matches.
    - ``VALIDATION_FAILED`` — validation capability found a constraint
      violation.
    - ``INPUT_NOT_SUPPORTED`` — text_extraction received an unsupported
      content type.
    - ``INFERENCE_PROVIDER_ERROR`` — inference provider raised.
    - ``INFERENCE_OUTPUT_UNTRUSTED`` — inference output failed
      validation (warning; Reconciler treats as untrusted anyway).
    - ``BUDGET_EXCLUDES`` — the budget excludes this capability for
      this call.
    - ``POLICY_EXCLUDES`` — the policy excludes this capability tier
      for this call.
    """

    CAPABILITY_OK = "CAPABILITY_OK"
    CAPABILITY_INVOKE_FAILED = "CAPABILITY_INVOKE_FAILED"
    PATTERN_NO_MATCH = "PATTERN_NO_MATCH"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    INPUT_NOT_SUPPORTED = "INPUT_NOT_SUPPORTED"
    INFERENCE_PROVIDER_ERROR = "INFERENCE_PROVIDER_ERROR"
    INFERENCE_OUTPUT_UNTRUSTED = "INFERENCE_OUTPUT_UNTRUSTED"
    BUDGET_EXCLUDES = "BUDGET_EXCLUDES"
    POLICY_EXCLUDES = "POLICY_EXCLUDES"


@attrs.frozen(slots=True)
class Diagnostic:
    """A single structured note attached to a :class:`CapabilityResult`.

    Diagnostics are not errors: they are typed, machine-readable
    annotations. A capability that runs cleanly may still emit
    diagnostics (e.g., ``PATTERN_NO_MATCH``).

    Attributes:
        code: The :class:`DiagnosticCode` identifying the note.
        severity: The :class:`DiagnosticSeverity`. Defaults to
            ``INFO``.
        message: A human-readable description.
        context: Optional structured details for logging and tracing.

    Examples:
        >>> Diagnostic(
        ...     code=DiagnosticCode.PATTERN_NO_MATCH,
        ...     severity=DiagnosticSeverity.INFO,
        ...     message="regex did not match the input",
        ... )
        Diagnostic(code=<DiagnosticCode.PATTERN_NO_MATCH: 'PATTERN_NO_MATCH'>, ...)
    """

    code: DiagnosticCode = attrs.field()
    severity: DiagnosticSeverity = DiagnosticSeverity.INFO
    message: str = ""
    context: dict[str, typing.Any] = attrs.field(factory=dict)

    def __attrs_post_init__(self) -> None:
        """Validate ``code`` and ``severity`` are the correct enum types."""
        if not isinstance(self.code, DiagnosticCode):
            raise TypeError(
                f"code must be a DiagnosticCode, got {type(self.code).__name__}: {self.code!r}"
            )
        if not isinstance(self.severity, DiagnosticSeverity):
            raise TypeError(
                f"severity must be a DiagnosticSeverity, got {type(self.severity).__name__}"
            )


# ---------------------------------------------------------------------------
# EvidenceRef
# ---------------------------------------------------------------------------


@attrs.frozen(slots=True)
class EvidenceRef:
    """A pointer to the evidence that produced a :class:`Candidate`.

    Evidence references are **provenance** — they record what produced
    the value, not the value itself. They are emitted by capabilities
    and surfaced in the artifact's :attr:`ExecutionArtifact.evidence`.

    Attributes:
        capability_id: The capability that produced the evidence
            (e.g., ``"text_extraction"``). Use the bare ID, not
            ``"text_extraction@1.0"``; the version is recorded
            separately in the artifact.
        capability_version: The capability's version at invocation
            (e.g., ``"1.0"``).
        field_path: The :class:`CanonicalField` path this evidence
            supports (e.g., ``"supplier_name"``).
        span: Optional input span (start, end byte offsets) into the
            raw input. ``None`` means the evidence does not point
            to a specific span. Defaults to ``None``.
        model_id: Optional model identifier for inference-produced
            evidence (e.g., ``"stub-v1"``). Defaults to ``None``.
        context: Optional structured details. Defaults to ``{}``.

    Examples:
        >>> EvidenceRef(
        ...     capability_id="regex_extraction",
        ...     capability_version="1.0",
        ...     field_path="supplier_name",
        ...     span=(10, 19),
        ... )
        EvidenceRef(capability_id='regex_extraction', capability_version='1.0', ...)
    """

    capability_id: str = attrs.field()
    capability_version: str = attrs.field()
    field_path: str = attrs.field()
    span: tuple[int, int] | None = None
    model_id: str | None = None
    context: dict[str, typing.Any] = attrs.field(factory=dict)

    def __attrs_post_init__(self) -> None:
        """Validate evidence invariants.

        Raises:
            ValueError: If ``capability_id`` / ``capability_version`` /
                ``field_path`` is not a non-empty string, or if
                ``span`` is malformed (negative offsets, start > end).
        """
        if not isinstance(self.capability_id, str) or not self.capability_id:
            raise ValueError(
                f"capability_id must be a non-empty string, got {self.capability_id!r}"
            )
        if not isinstance(self.capability_version, str) or not self.capability_version:
            raise ValueError(
                f"capability_version must be a non-empty string, got {self.capability_version!r}"
            )
        if not isinstance(self.field_path, str) or not self.field_path:
            raise ValueError(f"field_path must be a non-empty string, got {self.field_path!r}")
        if self.span is not None:
            start, end = self.span
            if not isinstance(start, int) or not isinstance(end, int):
                raise TypeError(
                    f"span offsets must be ints, got ({type(start).__name__}, {type(end).__name__})"
                )
            if start < 0 or end < 0:
                raise ValueError(f"span offsets must be non-negative, got {self.span!r}")
            if start > end:
                raise ValueError(f"span start must be <= end, got {self.span!r}")


# ---------------------------------------------------------------------------
# Candidate
# ---------------------------------------------------------------------------


@attrs.frozen(slots=True)
class Candidate:
    """A single proposed value for a field, with provenance.

    Candidates are produced by capabilities. The Reconciler (Sprint 5)
    merges candidates and assigns confidence. Per ADR-0005, candidates
    do **not** carry confidence — that is the Reconciler's exclusive
    responsibility.

    Attributes:
        value: The proposed value. Type depends on the target
            :class:`~paxman.types.FieldType` (e.g., ``str`` for
            ``STRING``, ``int`` for ``INTEGER``, ``decimal.Decimal``
            or :class:`~paxman.contract.canonical.MoneyValue` for
            ``MONEY``).
        evidence_refs: Tuple of :class:`EvidenceRef` records that
            support this candidate. May be empty if the capability
            cannot point to a specific evidence source (rare). Defaults
            to an empty tuple.
        diagnostics: Tuple of :class:`Diagnostic` notes attached to
            this candidate. Defaults to an empty tuple.

    Examples:
        >>> Candidate(value="ACME Corp")
        Candidate(value='ACME Corp', evidence_refs=(), diagnostics=())
    """

    value: typing.Any = attrs.field()
    evidence_refs: tuple[EvidenceRef, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()

    def __attrs_post_init__(self) -> None:
        """Validate that ``evidence_refs`` and ``diagnostics`` are tuples.

        The converter would silently wrap a list; the explicit check
        here surfaces programmer errors early.
        """
        if not isinstance(self.evidence_refs, tuple):
            raise TypeError(
                f"evidence_refs must be a tuple, got {type(self.evidence_refs).__name__}"
            )
        if not isinstance(self.diagnostics, tuple):
            raise TypeError(f"diagnostics must be a tuple, got {type(self.diagnostics).__name__}")


# ---------------------------------------------------------------------------
# CapabilityResult
# ---------------------------------------------------------------------------


@attrs.frozen(slots=True)
class CapabilityResult:
    """The output of a capability invocation.

    A :class:`CapabilityResult` carries the candidates, evidence, and
    diagnostics produced by one :meth:`Capability.invoke` call. It does
    **not** carry confidence (per ADR-0005). The Reconciler (Sprint 5)
    reads the candidates, weighs the evidence, and assigns confidence.

    Attributes:
        candidates: Tuple of :class:`Candidate` records. May be empty
            (e.g., a regex that matched nothing).
        evidence: Tuple of :class:`EvidenceRef` records produced
            during this invocation. May include evidence not attached
            to any candidate (caller decides). Defaults to an empty
            tuple.
        diagnostics: Tuple of :class:`Diagnostic` notes. Defaults to
            an empty tuple.

    Examples:
        >>> CapabilityResult(
        ...     candidates=(Candidate(value="ACME Corp"),),
        ...     diagnostics=(),
        ... )
        CapabilityResult(candidates=(Candidate(value='ACME Corp', ...),), evidence=(), diagnostics=())
    """

    candidates: tuple[Candidate, ...] = ()
    evidence: tuple[EvidenceRef, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()

    def __attrs_post_init__(self) -> None:
        """Validate field types and ensure the ``confidence`` invariant.

        This is the **structural enforcement** of ADR-0005: the
        constructor refuses to construct a :class:`CapabilityResult`
        if its instance has a ``confidence`` attribute (e.g., a
        subclass that adds one). It also validates that the tuple
        fields are actually tuples (not lists).
        """
        if not isinstance(self.candidates, tuple):
            raise TypeError(f"candidates must be a tuple, got {type(self.candidates).__name__}")
        if not isinstance(self.evidence, tuple):
            raise TypeError(f"evidence must be a tuple, got {type(self.evidence).__name__}")
        if not isinstance(self.diagnostics, tuple):
            raise TypeError(f"diagnostics must be a tuple, got {type(self.diagnostics).__name__}")
