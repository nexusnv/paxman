"""Field plan data models — ``FieldPlan``, ``FieldPlanStep``, ``ExecutionPlan``.

Per `ADR-0001` (Field-Centric Planning), the planner emits **one
:class:`FieldPlan` per required field**. Each :class:`FieldPlan`
contains an ordered list of :class:`FieldPlanStep` records (the
capability chain the Executor will walk) plus a
``target_confidence`` (read from the field's
``confidence_threshold``) and a ``fallback_policy``.

The :class:`ExecutionPlan` is the plan's container: a tuple of
:class:`FieldPlan` plus the planner version (for replay; per
``REPLAY_AND_DETERMINISM.md`` §2.1).

These data models are **frozen attrs with slots** (per
``DEPENDENCIES.md`` §3.2). Validation lives in
``__attrs_post_init__``. They are JSON-serializable via the
:mod:`paxman.serialization` module.
"""

from __future__ import annotations

import types
import typing

import attrs

from paxman.contract._types import ResolutionPolicy
from paxman.versioning import PLANNER_VERSION

__all__ = [
    "ExecutionPlan",
    "FieldPlan",
    "FieldPlanStep",
    "PlanDiagnostic",
]


#: Valid lowercase hex characters (0-9, a-f) for content-hash validation.
_HEX_LOWER: typing.Final[frozenset[str]] = frozenset("0123456789abcdef")


def _freeze_config(config: object) -> types.MappingProxyType[str, object]:
    """Validate and freeze a ``FieldPlanStep.config`` mapping.

    Returns a read-only :class:`types.MappingProxyType` view of a
    *copy* of the input. The copy is required so that subsequent
    mutations of the caller's dict do not leak into the frozen
    plan. If the input is already a mapping (e.g. a previous
    ``MappingProxyType``), it is unwrapped via ``dict(...)``.
    """
    if not isinstance(config, typing.Mapping):
        raise TypeError(f"config must be a dict or mapping, got {type(config).__name__}")
    return types.MappingProxyType(dict(config))


@attrs.frozen(slots=True)
class FieldPlanStep:
    """A single capability invocation in a :class:`FieldPlan`'s chain.

    The Executor walks the chain in order; each step is one
    capability invocation. V1 records the bare minimum to drive
    execution and replay: capability id, version, the capability
    config (e.g., the regex pattern for ``regex_extraction``),
    and a human-readable note.

    Attributes:
        capability_id: The capability's id (e.g.,
            ``"regex_extraction"``). Must be lowercase ASCII.
        capability_version: The capability's version (e.g., ``"1.0"``).
        config: Capability-specific configuration. Defaults to ``{}``.
        note: Optional human-readable note (e.g., a short reason
            for selecting this step). Defaults to ``""``.

    Examples:
        >>> FieldPlanStep(
        ...     capability_id="regex_extraction",
        ...     capability_version="1.0",
        ...     config={"pattern": r"^([A-Z][A-Za-z ]+)$"},
        ... )
        FieldPlanStep(capability_id='regex_extraction', capability_version='1.0', config={...}, note='')
    """

    capability_id: str = attrs.field()
    capability_version: str = attrs.field()
    # Wrap the user-supplied dict in a MappingProxyType so callers
    # cannot mutate the configuration after the plan is frozen.
    # Without this, the field would be a frozen attrs class
    # containing a mutable inner dict, breaking the immutability
    # contract that downstream consumers (e.g. the artifact hash)
    # rely on.
    config: typing.Mapping[str, object] = attrs.field(
        converter=_freeze_config,
        factory=lambda: types.MappingProxyType({}),
    )
    note: str = ""

    def __attrs_post_init__(self) -> None:
        """Validate invariants."""
        if not isinstance(self.capability_id, str) or not self.capability_id:
            raise ValueError(
                f"capability_id must be a non-empty string, got {self.capability_id!r}"
            )
        if not self.capability_id.isascii() or not self.capability_id.islower():
            raise ValueError(f"capability_id must be lowercase ASCII, got {self.capability_id!r}")
        if not isinstance(self.capability_version, str) or not self.capability_version:
            raise ValueError(
                f"capability_version must be a non-empty string, got {self.capability_version!r}"
            )
        if not isinstance(self.config, typing.Mapping):
            raise TypeError(f"config must be a mapping, got {type(self.config).__name__}")


@attrs.frozen(slots=True)
class FieldPlan:
    """A plan for resolving one :class:`~paxman.contract.canonical.CanonicalField`.

    Per `ADR-0001`, the planner emits one :class:`FieldPlan` per
    required field. The Executor walks the field plans in
    deterministic order; per `ADR-0006`, this walk is sequential.

    The :class:`FieldPlan` carries:

    - ``field_id`` — the :class:`CanonicalField.id` this plan
      resolves. (Not the path; the path is for human display; the
      id is the stable identifier.)
    - ``capability_chain`` — the ordered list of
      :class:`FieldPlanStep` records. Empty means ``UNRESOLVED``
      (no capability can satisfy this field under the current
      policy / budget).
    - ``target_confidence`` — the float threshold the Reconciler
      uses to decide whether a field is ``SUCCESS`` vs
      ``PARTIAL_SUCCESS``. Mirrors
      :attr:`~paxman.contract.canonical.CanonicalField.confidence_threshold`.
    - ``fallback_policy`` — the per-field
      :class:`ResolutionPolicy` used when the chain is exhausted.
    - ``early_stop`` — if ``True`` (the default), the Executor
      stops invoking capabilities once a candidate meets
      ``target_confidence``; if ``False``, the Executor walks the
      entire chain.

    Attributes:
        field_id: The :class:`CanonicalField.id` (e.g.,
            ``"field_a1b2c3d4e5f6"``).
        capability_chain: Ordered tuple of :class:`FieldPlanStep`.
        target_confidence: Float threshold in ``[0.0, 1.0]``.
        fallback_policy: The :class:`ResolutionPolicy`.
        early_stop: Whether to short-circuit on threshold met.

    Examples:
        >>> FieldPlan(
        ...     field_id="field_a1b2c3d4e5f6",
        ...     capability_chain=(
        ...         FieldPlanStep(
        ...             capability_id="regex_extraction",
        ...             capability_version="1.0",
        ...         ),
        ...     ),
        ...     target_confidence=0.8,
        ... )
        FieldPlan(field_id='field_a1b2c3d4e5f6', ...)
    """

    field_id: str = attrs.field()
    capability_chain: tuple[FieldPlanStep, ...] = attrs.field(factory=tuple)
    target_confidence: float = 0.8
    fallback_policy: ResolutionPolicy = attrs.field(default=attrs.Factory(ResolutionPolicy))
    early_stop: bool = True

    def __attrs_post_init__(self) -> None:
        """Validate invariants."""
        if not isinstance(self.field_id, str) or not self.field_id:
            raise ValueError(f"field_id must be a non-empty string, got {self.field_id!r}")
        if not isinstance(self.capability_chain, tuple):
            raise TypeError(
                f"capability_chain must be a tuple, got {type(self.capability_chain).__name__}"
            )
        for step in self.capability_chain:
            if not isinstance(step, FieldPlanStep):
                raise TypeError(
                    f"capability_chain entries must be FieldPlanStep, got {type(step).__name__}"
                )
        if not isinstance(self.target_confidence, (int, float)) or isinstance(
            self.target_confidence, bool
        ):
            raise TypeError(
                f"target_confidence must be a number, got {type(self.target_confidence).__name__}"
            )
        if not 0.0 <= float(self.target_confidence) <= 1.0:
            raise ValueError(
                f"target_confidence must be in [0.0, 1.0], got {self.target_confidence}"
            )
        if not isinstance(self.fallback_policy, ResolutionPolicy):
            raise TypeError(
                f"fallback_policy must be a ResolutionPolicy, "
                f"got {type(self.fallback_policy).__name__}"
            )
        if not isinstance(self.early_stop, bool):
            raise TypeError(f"early_stop must be a bool, got {type(self.early_stop).__name__}")


@attrs.frozen(slots=True)
class PlanDiagnostic:
    """A planner-emitted diagnostic attached to an :class:`ExecutionPlan`.

    Plan-level diagnostics are produced by the planner during
    planning (e.g., "budget excludes inference; fields requiring
    inference will be UNRESOLVED"). They are surfaced in the
    artifact's ``diagnostics`` by the Executor.

    Attributes:
        code: The diagnostic code (e.g.,
            ``"BUDGET_EXCLUDES_INFERENCE"``).
        message: A human-readable description.
        field_id: Optional :class:`FieldPlan.field_id` this
            diagnostic pertains to. ``None`` for plan-level
            (non-field-specific) diagnostics. Defaults to ``None``.
        context: Optional structured details. Defaults to ``{}``.
    """

    code: str = attrs.field()
    message: str = attrs.field()
    field_id: str | None = None
    context: dict[str, object] = attrs.field(factory=dict)

    def __attrs_post_init__(self) -> None:
        """Validate invariants."""
        if not isinstance(self.code, str) or not self.code:
            raise ValueError(f"code must be a non-empty string, got {self.code!r}")
        if not isinstance(self.message, str):
            raise TypeError(f"message must be a str, got {type(self.message).__name__}")
        if not isinstance(self.context, dict):
            raise TypeError(f"context must be a dict, got {type(self.context).__name__}")


@attrs.frozen(slots=True)
class ExecutionPlan:
    """The planner's output — a list of :class:`FieldPlan` records.

    The :class:`ExecutionPlan` is what the planner emits. The
Executor walks it; replay rehydrates it from the
artifact. The plan is **frozen** and **immutable**;
    the Executor must not mutate it.

    The plan is keyed on:

    - ``planner_version`` — embedded in the artifact for replay
      (defaults to :data:`paxman.versioning.PLANNER_VERSION`).
    - ``field_plans`` — the ordered tuple of :class:`FieldPlan`,
      one per required field. Required fields are deduplicated by
      ``field_id`` at construction time.
    - ``diagnostics`` — :class:`PlanDiagnostic` records emitted
      during planning (e.g., budget exclusions).
    - ``input_content_hash`` — the SHA-256 of the input bytes
      (mirrored from :attr:`InputProfile.content_hash`). Used by
      the artifact's replay hash composition.
    - ``contract_id`` — the :class:`CanonicalContract.id` (for
      artifact hash composition).

    Attributes:
        field_plans: Ordered tuple of :class:`FieldPlan`.
        planner_version: The planner's algorithm version.
        diagnostics: Tuple of :class:`PlanDiagnostic`.
        input_content_hash: SHA-256 of the raw input (hex).
        contract_id: The :class:`CanonicalContract.id`.

    Examples:
        >>> plan = ExecutionPlan(
        ...     field_plans=(
        ...         FieldPlan(
        ...             field_id="f1",
        ...             capability_chain=(
        ...                 FieldPlanStep(
        ...                     capability_id="regex_extraction",
        ...                     capability_version="1.0",
        ...                 ),
        ...             ),
        ...         ),
        ...     ),
        ...     input_content_hash="a" * 64,
        ...     contract_id="invoice-v1",
        ... )
        >>> plan.planner_version
        '1'
    """

    field_plans: tuple[FieldPlan, ...] = attrs.field()
    planner_version: str = PLANNER_VERSION
    diagnostics: tuple[PlanDiagnostic, ...] = ()
    input_content_hash: str = ""
    contract_id: str = ""

    def __attrs_post_init__(self) -> None:
        """Validate invariants.

        Raises:
            ValueError: If a field plan's ``field_id`` is empty or
                ``input_content_hash`` is not 64 lowercase hex chars
                (or empty).
            TypeError: If a field plan is not a :class:`FieldPlan`.
        """
        if not isinstance(self.field_plans, tuple):
            raise TypeError(f"field_plans must be a tuple, got {type(self.field_plans).__name__}")
        if not isinstance(self.planner_version, str) or not self.planner_version:
            raise ValueError(
                f"planner_version must be a non-empty string, got {self.planner_version!r}"
            )
        if not isinstance(self.diagnostics, tuple):
            raise TypeError(f"diagnostics must be a tuple, got {type(self.diagnostics).__name__}")
        for d in self.diagnostics:
            if not isinstance(d, PlanDiagnostic):
                raise TypeError(
                    f"diagnostics entries must be PlanDiagnostic, got {type(d).__name__}"
                )
        if not isinstance(self.input_content_hash, str):
            raise TypeError(
                f"input_content_hash must be a str, got {type(self.input_content_hash).__name__}"
            )
        if self.input_content_hash:
            if len(self.input_content_hash) != 64:
                raise ValueError(
                    f"input_content_hash must be 64 hex chars or empty, got "
                    f"{len(self.input_content_hash)} chars"
                )
            if not all(c in _HEX_LOWER for c in self.input_content_hash):
                raise ValueError(
                    f"input_content_hash must be 64 lowercase hex chars, got "
                    f"{self.input_content_hash!r}"
                )
        if not isinstance(self.contract_id, str):
            raise TypeError(f"contract_id must be a str, got {type(self.contract_id).__name__}")

        seen_ids: set[str] = set()
        for fp in self.field_plans:
            if not isinstance(fp, FieldPlan):
                raise TypeError(f"field_plans entries must be FieldPlan, got {type(fp).__name__}")
            if fp.field_id in seen_ids:
                raise ValueError(f"duplicate field_id in plan: {fp.field_id!r}")
            seen_ids.add(fp.field_id)
