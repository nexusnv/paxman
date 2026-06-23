"""Budget tracking — the Executor's cost / latency / invocation counter.

The :class:`BudgetTracker` answers one question: **given the current
cumulative spend, would invoking a capability with this cost exceed
any of the caller's caps?**

The :class:`BudgetTracker` is the **gatekeeper** for the Executor
loop. The Executor calls :meth:`would_exceed` *before* invoking
a capability; if it would, the Executor short-circuits with a
``BUDGET_EXCEEDED`` diagnostic and stops walking the plan (per
``ARCHITECTURE.md`` §7.1 and the Sprint 4 exit criteria).

Design notes
------------

- The :class:`BudgetTracker` is **stateless** about the cap set; the
  cap set is supplied at construction (or via :meth:`with_budget`).
  The tracker holds **mutable** state for the cumulative counters.
- The tracker does **not** know which capability tier costs what;
  the Executor (or :class:`CapabilityCostModel`) tells the tracker
  the cost. This keeps the tracker decoupled from
  :mod:`paxman.capabilities.spec`.
- All counters are **non-negative**. Negative inputs are rejected
  with :class:`ValueError`.
- The cost type is :class:`float` for USD and :class:`int` for
  latency / counts. The USD value is *not* converted to
  :class:`decimal.Decimal`; V1 uses float per
  :class:`paxman.budget.Budget` and :class:`paxman.capabilities.spec.CostHint`.
  Future sprints may switch to :class:`decimal.Decimal` if a
  precision issue surfaces.

The :class:`BudgetTracker` is **deterministic**: the same sequence
of :meth:`record` calls produces the same final counters.

Exit criteria (per the Sprint 4 spec):

- The Executor short-circuits when ``Budget.max_total_cost_usd``
  is exceeded. The tracker enforces this gate.
- The tracker must reject negative cost / latency / invocation
  counts to keep the budget arithmetic honest.
"""

from __future__ import annotations

import typing

from paxman.budget import Budget
from paxman.errors import InvalidBudgetError

__all__ = ["BudgetTracker"]


#: The 4 short-circuit reasons the Executor surfaces in a
#: ``BUDGET_EXCEEDED`` diagnostic. The tracker's :meth:`exceeded_reason`
#: returns one of these (or ``None`` if nothing is exceeded).
EXCEEDED_REASON_COST: typing.Final[str] = "max_total_cost_usd"
EXCEEDED_REASON_LATENCY: typing.Final[str] = "max_total_latency_ms"
EXCEEDED_REASON_REMOTE: typing.Final[str] = "max_remote_inference_calls"
EXCEEDED_REASON_INVOCATIONS: typing.Final[str] = "max_capability_invocations"


class BudgetTracker:
    """Tracks cumulative cost / latency / invocations against a :class:`Budget`.

    Attributes:
        budget: The :class:`Budget` to enforce. ``None`` means no
            cap (any cost is allowed).
        total_cost_usd: Cumulative USD cost recorded via
            :meth:`record`. Defaults to ``0.0``.
        total_latency_ms: Cumulative wall-clock latency in ms.
            Defaults to ``0``.
        invocation_count: Total capability invocations recorded.
            Defaults to ``0``.
        remote_inference_count: Total remote-inference invocations
            recorded. Defaults to ``0``.

    Examples:
        >>> tracker = BudgetTracker(budget=Budget(max_total_cost_usd=0.10))
        >>> tracker.would_exceed(cost_usd=0.05)
        False
        >>> tracker.record(cost_usd=0.05, latency_ms=10)
        >>> tracker.would_exceed(cost_usd=0.06)
        True
        >>> tracker.exceeded_reason()
        'max_total_cost_usd'
    """

    def __init__(self, budget: Budget | None = None) -> None:
        """Initialize the tracker.

        Args:
            budget: The :class:`Budget` to enforce. ``None`` means
                no cap (any cost is allowed). Defaults to ``None``.
        """
        if budget is not None and not isinstance(budget, Budget):
            raise TypeError(f"budget must be a Budget or None, got {type(budget).__name__}")
        self.budget: Budget | None = budget
        self.total_cost_usd: float = 0.0
        self.total_latency_ms: int = 0
        self.invocation_count: int = 0
        self.remote_inference_count: int = 0

    # --- record ----------------------------------------------------------

    def record(
        self,
        *,
        cost_usd: float = 0.0,
        latency_ms: int = 0,
        is_remote_inference: bool = False,
    ) -> None:
        """Record a capability invocation's cost / latency / tier.

        Args:
            cost_usd: The USD cost of the invocation (non-negative).
                Defaults to ``0.0``.
            latency_ms: The wall-clock latency in ms (non-negative).
                Defaults to ``0``.
            is_remote_inference: ``True`` if this invocation was a
                remote-inference call. Defaults to ``False``.

        Raises:
            ValueError: If ``cost_usd`` or ``latency_ms`` is negative.
            TypeError: If a numeric field is not a number.
        """
        cost = float(cost_usd)
        if cost < 0:
            raise ValueError(f"cost_usd must be non-negative, got {cost_usd!r}")
        if not isinstance(latency_ms, int) or isinstance(latency_ms, bool):
            raise TypeError(
                f"latency_ms must be an int, got {type(latency_ms).__name__}: {latency_ms!r}"
            )
        if latency_ms < 0:
            raise ValueError(f"latency_ms must be non-negative, got {latency_ms}")
        self.total_cost_usd += cost
        self.total_latency_ms += latency_ms
        self.invocation_count += 1
        if is_remote_inference:
            self.remote_inference_count += 1

    # --- gate ------------------------------------------------------------

    def would_exceed(
        self,
        *,
        cost_usd: float = 0.0,
        latency_ms: int = 0,
        is_remote_inference: bool = False,
    ) -> bool:
        """Return ``True`` if recording the given invocation would exceed a cap.

        The check is **simulated**: counters are not mutated. Call
        :meth:`record` separately to actually book the cost.

        Args:
            cost_usd: The USD cost of the would-be invocation.
            latency_ms: The wall-clock latency in ms.
            is_remote_inference: ``True`` if the invocation would
                be a remote-inference call.

        Returns:
            ``True`` if any cap would be exceeded by the simulated
            invocation; ``False`` otherwise. When no budget is set,
            this is always ``False``.
        """
        return (
            self.would_exceed_reason(
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                is_remote_inference=is_remote_inference,
            )
            is not None
        )

    def would_exceed_reason(
        self,
        *,
        cost_usd: float = 0.0,
        latency_ms: int = 0,
        is_remote_inference: bool = False,
    ) -> str | None:
        """Return the cap that would be exceeded by a simulated invocation.

        Like :meth:`would_exceed`, this is a **simulated** check:
        counters are not mutated. The return value is the same
        shape as :meth:`exceeded_reason` (one of the
        ``EXCEEDED_REASON_*`` constants), but it answers the
        counterfactual "what would be the cap that this invocation
        exceeds?" — useful when the caller wants to know which
        cap blocked the invocation *before* recording it.

        Returns:
            The cap that would be exceeded, or ``None`` if
            nothing would be exceeded. When no budget is set,
            always returns ``None``.
        """
        if self.budget is None:
            return None
        b = self.budget
        if (
            b.max_total_cost_usd is not None
            and (self.total_cost_usd + cost_usd) > b.max_total_cost_usd
        ):
            return EXCEEDED_REASON_COST
        if (
            b.max_total_latency_ms is not None
            and (self.total_latency_ms + latency_ms) > b.max_total_latency_ms
        ):
            return EXCEEDED_REASON_LATENCY
        if (
            b.max_remote_inference_calls is not None
            and is_remote_inference
            and (self.remote_inference_count + 1) > b.max_remote_inference_calls
        ):
            return EXCEEDED_REASON_REMOTE
        if (
            b.max_capability_invocations is not None
            and (self.invocation_count + 1) > b.max_capability_invocations
        ):
            return EXCEEDED_REASON_INVOCATIONS
        return None

    def exceeded_reason(self) -> str | None:
        """Return the cap that has been exceeded, or ``None`` if none.

        Returns:
            One of the four ``EXCEEDED_REASON_*`` constants
            (e.g., ``"max_total_cost_usd"``), or ``None`` if no
            cap is currently exceeded. Order of checks (cost,
            latency, remote, invocations) is deterministic.
        """
        if self.budget is None:
            return None
        b = self.budget
        if b.max_total_cost_usd is not None and self.total_cost_usd > b.max_total_cost_usd:
            return EXCEEDED_REASON_COST
        if b.max_total_latency_ms is not None and self.total_latency_ms > b.max_total_latency_ms:
            return EXCEEDED_REASON_LATENCY
        if (
            b.max_remote_inference_calls is not None
            and self.remote_inference_count > b.max_remote_inference_calls
        ):
            return EXCEEDED_REASON_REMOTE
        if (
            b.max_capability_invocations is not None
            and self.invocation_count > b.max_capability_invocations
        ):
            return EXCEEDED_REASON_INVOCATIONS
        return None

    def is_exceeded(self) -> bool:
        """Return ``True`` if any cap has been exceeded (post-record).

        Equivalent to ``self.exceeded_reason() is not None``.
        """
        return self.exceeded_reason() is not None

    def mark_exhausted(self) -> None:
        """Force the tracker into the "exceeded" state.

        The :class:`FieldRunner` calls this when a capability's
        would-be cost exceeds a cap (so the invocation is
        skipped). Without this, the Executor's pre-loop gate
        (which calls :meth:`is_exceeded`) would not see the
        short-circuit and would re-enter the FieldRunner for
        the next field.

        The implementation is a side-effect: we record a
        zero-cost, zero-latency, non-remote invocation, which
        preserves the existing ``is_exceeded`` semantics
        (``total_cost_usd > max_total_cost_usd`` becomes
        ``True`` only when an actual exceeding cost is
        recorded).

        A more direct way is to add an explicit
        ``self._exhausted: bool`` flag, but the existing
        counter-based check is more uniform and easier to
        reason about.
        """
        # Bump the invocation count so the
        # ``max_capability_invocations`` cap (if any) starts
        # ticking. The cost-based and latency-based caps are
        # set by recording the actual cost; if those are
        # ``None``, no cap is in effect and the flag will not
        # flip (this is fine — the FieldRunner's
        # ``would_exceed`` gate is the authoritative check).
        if self.budget is None:
            return
        if self.budget.max_total_cost_usd is not None:
            # Bump the cost counter strictly above the cap so
            # ``exceeded_reason()`` returns the cap (its check
            # is ``total_cost_usd > max_total_cost_usd``).
            self.total_cost_usd = max(self.total_cost_usd, self.budget.max_total_cost_usd + 1e-9)
        if self.budget.max_total_latency_ms is not None:
            self.total_latency_ms = max(self.total_latency_ms, self.budget.max_total_latency_ms + 1)
        if self.budget.max_remote_inference_calls is not None:
            self.remote_inference_count = max(
                self.remote_inference_count,
                self.budget.max_remote_inference_calls + 1,
            )
        if self.budget.max_capability_invocations is not None:
            self.invocation_count = max(
                self.invocation_count, self.budget.max_capability_invocations + 1
            )

    # --- factory ---------------------------------------------------------

    @classmethod
    def from_budget(cls, budget: Budget | None) -> BudgetTracker:
        """Build a tracker from a :class:`Budget` (or ``None``).

        Convenience constructor for the common case:

        >>> from paxman.budget import Budget
        >>> tracker = BudgetTracker.from_budget(Budget(max_total_cost_usd=0.10))
        >>> tracker.budget is not None
        True
        """
        if budget is None:
            return cls(budget=None)
        if not isinstance(budget, Budget):
            raise InvalidBudgetError(
                f"budget must be a Budget or None, got {type(budget).__name__}",
                error_code="INVALID_BUDGET",
                context={"got_type": type(budget).__name__},
            )
        return cls(budget=budget)
