"""``executor`` subsystem — the deterministic plan runner (Sprint 4).

Per ``PACKAGE_STRUCTURE.md`` §6 and ``docs/sprints/sprint-04-executor-and-capabilities.md``,
the Executor:

- Walks the per-field plans in declaration order (sequential, per ADR-0006).
- Invokes the capability chain for each field, in plan order.
- Collects candidates + evidence + diagnostics (no confidence — per ADR-0005).
- Stops on chain exhaustion (V1 has no confidence-based early stop; the
  Reconciler assigns confidence in Sprint 5).
- Short-circuits on :class:`~paxman.budget.Budget` exhaustion with a
  ``BUDGET_EXCEEDED`` diagnostic.

The V1 surface:

- :class:`Executor` — the top-level runner. Stateful only about the
  :class:`FieldRunner` it is constructed with.
- :func:`run` — module-level convenience wrapper.
- :class:`CandidateResult` — the per-field output of a run.
- :class:`FieldRunner` — executes one :class:`FieldPlan`.
- :class:`ContextBuilder` — builds :class:`~paxman.capabilities.base.CapabilityContext`
  records.
- :class:`EvidenceCollector` — promotes run-level diagnostics.
- :class:`EarlyStop` — V1 chain-exhaustion gate.
- :class:`BudgetTracker` — tracks cost / latency / invocations.
- :class:`ExecutionState` — transient in-flight state.

The Executor is **deterministic** and **stateless** about cross-run
state. Multiple calls to :func:`run` with the same inputs produce
the same output, byte-for-byte.

Boundary rules
--------------

- :mod:`paxman.executor` may import from:
  :mod:`paxman.budget`, :mod:`paxman.capabilities.base`,
  :mod:`paxman.capabilities.result`, :mod:`paxman.capabilities.spec`,
  :mod:`paxman.capabilities.registry`, :mod:`paxman.contract.canonical`,
  :mod:`paxman.contract._types`, :mod:`paxman.errors`,
  :mod:`paxman.planner.field_plan`, :mod:`paxman.planner.input_profile`,
  and the other cross-cutting modules.
- :mod:`paxman.executor` may NOT import from:
  :mod:`paxman.contract.adapters.*` (the Executor does not know
  about external contract formats),
  :mod:`paxman.reconciler`, :mod:`paxman.artifact`, or
  :mod:`paxman.api`.

These rules are enforced by ``import-linter`` (see
``pyproject.toml``).
"""

from paxman.executor.executor import Executor, run
from paxman.executor.field_runner import CandidateResult, FieldRunner

__all__ = [
    "CandidateResult",
    "Executor",
    "FieldRunner",
    "run",
]
