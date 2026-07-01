"""Capability metadata — ``CapabilitySpec`` and ``CostHint``.

Every capability exposes a :class:`CapabilitySpec` (input/output types,
version, cost, determinism, required providers). The planner uses the
spec to:

- pick the cheapest trustworthy path per field (per
  :class:`~paxman.capabilities.scoring` and the V1 heuristic chain in
  :mod:`~paxman.planner.heuristics`),
- compute budget estimates (per
  ``docs/specs/capability-cost-model.md`` §6),
- and serialize the plan for replay (the spec is recorded in the
  artifact's ``capability_versions`` list).

The :class:`CostHint` is the per-invocation cost estimate (tokens, ms,
USD). It is a **heuristic** for planner scoring, not a runtime
measurement. Per ``docs/specs/capability-cost-model.md`` §5.2, the
planner must NOT use wall-clock measurements to update cost.

See also
--------

- :mod:`paxman.capabilities.scoring` — the scoring formula.
- :class:`~paxman.planner.field_plan.FieldPlanStep` — the per-field
  capability invocation recorded in the plan.
"""

from __future__ import annotations

import enum
import math
from decimal import Decimal

import attrs

from paxman.contract._format_hint import FormatHint

__all__ = [
    "CapabilitySpec",
    "CapabilityTier",
    "CostHint",
]


# ---------------------------------------------------------------------------
# CostHint
# ---------------------------------------------------------------------------


def _to_usd_decimal(value: float | int | Decimal) -> Decimal:
    """Convert a USD cost input to :class:`decimal.Decimal`.

    Used as the ``attrs.field`` converter on :attr:`CostHint.usd` so
    callers can pass either a literal ``float`` (``0.001``) or a
    ``Decimal`` (``Decimal("0.001")``). The internal type is
    :class:`decimal.Decimal` per ADR-0004 / ADR-0010 — MONEY is Decimal,
    never float — but the float-literal call site pattern is preserved
    for backward compatibility.

    Rejects ``bool`` explicitly because ``isinstance(True, int)`` is
    ``True`` in Python (preserved from the prior float-based validation
    per Oracle review F17 / V1 acceptance §2.1 — no bool-as-int trap).
    Rejects NaN and Infinity (they would break cost comparisons
    downstream).

    The conversion is exact for the V1 USD domain ([0, 1] with up to
    3 decimal places). Floats are converted via ``Decimal(str(x))`` to
    avoid the binary-representation noise of ``Decimal(0.001)`` producing
    ``Decimal('0.0010000000000000000208166817117216851329430937767028808593750')``.
    """

    if isinstance(value, bool):
        raise TypeError(f"usd must be a number, got bool: {value!r}")
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError(f"usd must be a finite Decimal, got {value!r}")
        return value
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"usd must be a finite number, got {value!r}")
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    raise TypeError(f"usd must be float | int | Decimal, got {type(value).__name__}: {value!r}")


@attrs.frozen(slots=True)
class CostHint:
    """Approximate cost estimate for a single capability invocation.

    The :class:`CostHint` is a three-tuple of approximate token count,
    wall-clock latency in milliseconds, and USD cost. Values are
    **heuristics for planner scoring**, not runtime measurements
    (per ``docs/specs/capability-cost-model.md`` §1).

    All fields are non-negative:

    - ``tokens`` — approximate token count (prompt + completion).
      Zero for non-LLM capabilities. Defaults to ``0``.
    - ``ms`` — approximate wall-clock latency in milliseconds.
      Defaults to ``1`` (the V1 minimum; a 1 ms floor prevents the
      planner from treating capabilities as instantaneous).
    - ``usd`` — approximate USD cost per invocation. Zero for free
      capabilities. Defaults to ``Decimal("0")`` (MONEY is Decimal,
      per ADR-0004 / ADR-0010).

    Attributes:
        tokens: Approximate token count (non-negative int).
        ms: Approximate wall-clock latency in ms (non-negative int).
        usd: Approximate USD cost (non-negative Decimal).

    Examples:
        >>> CostHint(tokens=0, ms=1, usd=0.0)
        CostHint(tokens=0, ms=1, usd=Decimal('0'))
        >>> CostHint(tokens=500, ms=1500, usd=0.001)
        CostHint(tokens=500, ms=1500, usd=Decimal('0.001'))
    """

    tokens: int = 0
    ms: int = 1
    usd: Decimal = attrs.field(default=Decimal("0"), converter=_to_usd_decimal)

    def __attrs_post_init__(self) -> None:
        """Validate non-negativity of all three fields.

        Raises:
            ValueError: If any field is negative.
            TypeError: If ``tokens`` or ``ms`` is not an int (e.g.,
                ``bool``), or ``usd`` is not a number.
        """
        # Oracle review F17: reject bool as a sneaky int subclass.
        if type(self.tokens) is not int:
            raise TypeError(
                f"tokens must be an int, got {type(self.tokens).__name__}: {self.tokens!r}"
            )
        if type(self.ms) is not int:
            raise TypeError(f"ms must be an int, got {type(self.ms).__name__}: {self.ms!r}")
        if not isinstance(self.usd, (int, float, Decimal)) or isinstance(self.usd, bool):
            raise TypeError(f"usd must be a number, got {type(self.usd).__name__}: {self.usd!r}")
        if self.tokens < 0:
            raise ValueError(f"tokens must be non-negative, got {self.tokens}")
        if self.ms < 0:
            raise ValueError(f"ms must be non-negative, got {self.ms}")
        if self.usd < 0:
            raise ValueError(f"usd must be non-negative, got {self.usd}")


# ---------------------------------------------------------------------------
# CapabilityTier
# ---------------------------------------------------------------------------


@enum.unique
class CapabilityTier(enum.Enum):
    """The V1 heuristic tier for a capability.

    Per ``docs/specs/capability-cost-model.md`` §4.1, the planner
    assigns each capability to one of 7 tiers (0 = explicit evidence,
    ..., 6 = ``UNRESOLVED`` terminal). The tier dominates scoring
    (``TIER_WEIGHT = 10000``): a capability in tier N always scores
    lower than any capability in tier N+1, regardless of cost.

    V1 tier mapping (per ``docs/specs/capability-cost-model.md`` §3
    and the V1 capability set):

    - ``LOCAL_DETERMINISTIC`` (1) — ``regex_extraction``, ``validation``.
    - ``STRUCTURED_LOOKUP`` (2) — ``lookup`` (deterministic backend).
    - ``LOCAL_INFERENCE`` (4) — ``inference`` (local model; V2).
    - ``REMOTE_INFERENCE`` (5) — ``inference`` (remote provider).

    Note: tier 0 (Explicit Evidence) is not a capability — it is a
    planner rule on the :class:`InputProfile`; tier 3 (Derived
    Computation) and tier 6 (Unresolved) are not capabilities in V1.

    Attributes:
        LOCAL_DETERMINISTIC: Tier 1. Local, deterministic, free.
        STRUCTURED_LOOKUP: Tier 2. Deterministic lookup table.
        LOCAL_INFERENCE: Tier 4. Local model (V2 in the V1 spec).
        REMOTE_INFERENCE: Tier 5. Remote LLM provider.

    Note
    ----
    The ``value`` of each enum member is the integer tier rank from
    the cost-model spec. This makes the scoring formula (per
    ``docs/specs/capability-cost-model.md`` §4.2) a direct lookup.
    """

    LOCAL_DETERMINISTIC = 1
    STRUCTURED_LOOKUP = 2
    LOCAL_INFERENCE = 4
    REMOTE_INFERENCE = 5


# ---------------------------------------------------------------------------
# CapabilitySpec
# ---------------------------------------------------------------------------


@attrs.frozen(slots=True)
class CapabilitySpec:
    """Metadata describing a :class:`~paxman.capabilities.base.Capability`.

    The :class:`CapabilitySpec` is the **stable public surface** of
    a capability: it declares the capability's id, version, the
    V1 :class:`~paxman.types.FieldType` values it accepts and
    produces, the :class:`CostHint`, the tier (for planner scoring),
    the determinism flag, and any required provider classes.

    The spec is what the planner reads to make decisions; it is also
    what the artifact records for replay (the executor's
    ``capability_versions`` list).

    Attributes:
        id: Stable capability identifier (e.g., ``"regex_extraction"``).
            Must be lowercase ASCII, no whitespace.
        version: The capability's semver (e.g., ``"1.0"``). Bumped on
            any change to the capability's input/output/cost contract.
        input_types: Tuple of V1 :class:`~paxman.types.FieldType` value
            names (e.g., ``("STRING", "HTML_TEXT")``) the capability
            accepts as the field's type. Stored as ``str`` to avoid
            a circular import on :mod:`paxman.types`. Defaults to
            an empty tuple.
        output_type: The V1 :class:`~paxman.types.FieldType` value
            name (e.g., ``"STRING"``) the capability produces. Stored
            as ``str``.
        cost_estimate: The :class:`CostHint`. Defaults to a free
            zero-cost hint (``tokens=0, ms=1, usd=0.0``).
        tier: The :class:`CapabilityTier` for planner scoring.
            Defaults to ``LOCAL_DETERMINISTIC``.
        deterministic: ``True`` if the capability always produces
            the same output for the same input. ``False`` for
            capabilities that may vary (e.g., remote inference).
            Defaults to ``True``.
        required_providers: Tuple of provider-class identifiers the
            capability depends on (e.g., ``("openai",)`` for a
            remote-inference capability). Empty for self-contained
            capabilities. Defaults to an empty tuple.
        format_hint: Wire-format hint declaring which :class:`FormatHint`
            this capability consumes. ``None`` for capabilities that do
            not consume raw input bytes (cleanup transforms, lookup,
            inference, validation). Defaults to ``None``. See
            `ADR-0015 <../adr/0015-format-aware-executor-auto-dispatch.md>`_
            and `issue #73
            <https://github.com/nexusnv/paxman/issues/73>`_.

    Examples:
        >>> CapabilitySpec(
        ...     id="regex_extraction",
        ...     version="1.0",
        ...     input_types=("STRING",),
        ...     output_type="STRING",
        ...     cost_estimate=CostHint(tokens=0, ms=1, usd=0.0),
        ... )
        CapabilitySpec(id='regex_extraction', ...)
    """

    id: str = attrs.field()
    version: str = attrs.field()
    input_types: tuple[str, ...] = ()
    output_type: str = "STRING"
    cost_estimate: CostHint = attrs.field(default=attrs.Factory(CostHint))
    tier: CapabilityTier = CapabilityTier.LOCAL_DETERMINISTIC
    deterministic: bool = True
    required_providers: tuple[str, ...] = ()
    format_hint: FormatHint | None = None

    def __attrs_post_init__(self) -> None:
        """Validate invariants.

        Raises:
            TypeError: If a field has the wrong type.
            ValueError: If ``id`` is not lowercase ASCII, ``version``
                is empty, or ``output_type`` is empty.
        """
        if not isinstance(self.id, str) or not self.id:
            raise ValueError(f"id must be a non-empty string, got {self.id!r}")
        # Accept lowercase ASCII letters, digits, and underscores. Reject
        # whitespace, hyphens, uppercase, and any non-ASCII character.
        if not all(c.isascii() and (c.islower() or c.isdigit() or c == "_") for c in self.id):
            raise ValueError(
                f"id must be lowercase ASCII (letters, digits, underscores; no whitespace), "
                f"got {self.id!r}"
            )
        if not isinstance(self.version, str) or not self.version:
            raise ValueError(f"version must be a non-empty string, got {self.version!r}")
        if not isinstance(self.output_type, str) or not self.output_type:
            raise ValueError(f"output_type must be a non-empty string, got {self.output_type!r}")
        if not isinstance(self.cost_estimate, CostHint):
            raise TypeError(
                f"cost_estimate must be a CostHint, got {type(self.cost_estimate).__name__}"
            )
        if not isinstance(self.tier, CapabilityTier):
            raise TypeError(f"tier must be a CapabilityTier, got {type(self.tier).__name__}")
        if not isinstance(self.input_types, tuple):
            raise TypeError(f"input_types must be a tuple, got {type(self.input_types).__name__}")
        if not isinstance(self.required_providers, tuple):
            raise TypeError(
                f"required_providers must be a tuple, got {type(self.required_providers).__name__}"
            )
        if self.format_hint is not None and not isinstance(self.format_hint, FormatHint):
            raise TypeError(
                f"format_hint must be a FormatHint or None, got {type(self.format_hint).__name__}"
            )
