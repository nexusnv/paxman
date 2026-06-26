"""Budget, Policy, and CurrencyPolicy types for paxman.normalize().

Defines the configuration models per ARCHITECTURE.md §7 and
PACKAGE_STRUCTURE.md §10 (line 523). These are public types re-exported
in ``api/types.py``.
"""

from __future__ import annotations

import enum
import math
from decimal import Decimal

import attrs


class CurrencyPolicy(enum.Enum):
    """How the Reconciler handles cross-currency MONEY candidates.

    Values:
        STRICT_MATCH (default): reject cross-currency candidates
            (e.g., USD + EUR → UNRESOLVED).
        ALLOW_FX: apply an explicit FX rate (requires an ``fx_rate`` field).
        REJECT_WITHOUT_RATE: require an explicit FX rate or reject.
    """

    STRICT_MATCH = "STRICT_MATCH"
    ALLOW_FX = "ALLOW_FX"
    REJECT_WITHOUT_RATE = "REJECT_WITHOUT_RATE"


def _to_decimal_optional(
    value: float | int | Decimal | None,
) -> Decimal | None:
    """Convert a USD cost input to ``Decimal`` (or pass ``None`` through).

    Used as the ``attrs.field`` converter on :attr:`Budget.max_total_cost_usd`
    so callers can pass either a literal ``float`` (``0.10``) or a
    ``Decimal`` (``Decimal("0.10")``). The internal type is
    :class:`decimal.Decimal` per ADR-0004 / ADR-0010 — MONEY is Decimal,
    never float — but the float-literal call site pattern is preserved
    for backward compatibility.

    The accepted input contract is ``float | int | Decimal | None``;
    everything else is rejected with ``TypeError``. ``bool`` is
    rejected explicitly because ``isinstance(True, int)`` is ``True``
    in Python (preserved from the prior float-based validation per
    Oracle review F17 / V1 acceptance §2.1 — no bool-as-int trap).
    NaN and Infinity are rejected with ``ValueError`` (they would
    break budget comparisons downstream).

    Floats and ints are converted via ``Decimal(str(x))`` to avoid
    the binary-representation noise of ``Decimal(0.1)`` producing
    ``Decimal('0.1000000000000000055511151231257827021181583404541015625')``.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        raise TypeError(f"max_total_cost_usd must be a number, got bool: {value!r}")
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError(f"max_total_cost_usd must be a finite Decimal, got {value!r}")
        return value
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"max_total_cost_usd must be a finite number, got {value!r}")
        return Decimal(str(value))
    raise TypeError(
        f"max_total_cost_usd must be float | int | Decimal | None, "
        f"got {type(value).__name__}: {value!r}"
    )


@attrs.frozen(slots=True)
class Budget:
    """Hard caps on cost, latency, and capability invocations.

    All fields default to ``None`` (no cap). When any cap is exceeded, the
    Executor short-circuits per ARCHITECTURE.md §7.1 and returns the partial
    artifact with status ``PARTIAL_SUCCESS``.

    Attributes:
        max_total_cost_usd: Hard cap on cost in USD (Decimal per
            ADR-0004 / ADR-0010); aborts when exceeded. The constructor
            accepts ``float | int | Decimal | None`` and coerces to
            ``Decimal`` for backward compatibility.
        max_total_latency_ms: Hard cap on wall-clock latency.
        max_remote_inference_calls: Cap on remote inference invocations.
        max_capability_invocations: Cap on total capability invocations.
    """

    max_total_cost_usd: Decimal | None = attrs.field(default=None, converter=_to_decimal_optional)
    max_total_latency_ms: int | None = attrs.field(default=None)
    max_remote_inference_calls: int | None = attrs.field(default=None)
    max_capability_invocations: int | None = attrs.field(default=None)

    def __attrs_post_init__(self) -> None:
        """Validate all caps are non-negative (when set)."""
        if self.max_total_cost_usd is not None and self.max_total_cost_usd < 0:
            raise ValueError("max_total_cost_usd must be non-negative")
        if self.max_total_latency_ms is not None and self.max_total_latency_ms < 0:
            raise ValueError("max_total_latency_ms must be non-negative")
        if self.max_remote_inference_calls is not None and self.max_remote_inference_calls < 0:
            raise ValueError("max_remote_inference_calls must be non-negative")
        if self.max_capability_invocations is not None and self.max_capability_invocations < 0:
            raise ValueError("max_capability_invocations must be non-negative")


@attrs.frozen(slots=True)
class Policy:
    """Behavior configuration for a single ``paxman.normalize()`` call.

    All opt-in fields default to safe values (no raw input logged, no
    inference I/O recorded, no evidence payload embedded, no metrics emitted).

    Attributes:
        allow_remote_inference: If False, planner excludes step 6 (remote
            inference) of the heuristic chain. Default: True.
        allow_local_inference: If False, planner excludes step 5 (local
            inference). Default: True.
        confidence_floor: Minimum confidence to mark a field SUCCESS;
            below this is PARTIAL_SUCCESS. Default: 0.80.
        unresolved_acceptable: If False, artifact status is UNRESOLVED when
            any required field is unresolved. Default: False.
        currency_policy: For MONEY fields: behavior on cross-currency
            arithmetic. Default: CurrencyPolicy.STRICT_MATCH.
        emit_metrics: Opt-in metric emission. Default: False.
        log_raw_input: If True, raw input is written to logs. Default: False.
        record_inference_io: If True, inference prompts/completions are
            recorded in evidence. Default: False.
        embed_evidence_payload: If True, full evidence payloads are stored
            in the artifact. Default: False.
    """

    allow_remote_inference: bool = True
    allow_local_inference: bool = True
    confidence_floor: float = attrs.field(default=0.80)
    unresolved_acceptable: bool = False
    currency_policy: CurrencyPolicy = CurrencyPolicy.STRICT_MATCH
    emit_metrics: bool = False
    log_raw_input: bool = False
    record_inference_io: bool = False
    embed_evidence_payload: bool = False

    def __attrs_post_init__(self) -> None:
        """Validate ``confidence_floor`` is in [0.0, 1.0]."""
        if not 0.0 <= self.confidence_floor <= 1.0:
            raise ValueError("confidence_floor must be in [0.0, 1.0]")


__all__ = ["Budget", "CurrencyPolicy", "Policy"]
