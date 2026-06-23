"""Planner subsystem — field-centric plan synthesis (deterministic, rule-based).

The planner is the **deterministic brain** of Paxman. It does NOT
execute anything (per ``PACKAGE_STRUCTURE.md`` §4.4 invariant #2).

It reads the canonical contract, analyzes the input profile, and
produces a **field-by-field execution plan** — one plan per required
field, not one plan per document (per `ADR-0001`).

This module is the top-level package init; it re-exports the public
planner types (:class:`ExecutionPlan`, :class:`FieldPlan`) for
ergonomic use, but the heavy lifting lives in the submodules.

See also
--------

- :mod:`paxman.planner.planner` — the top-level :func:`plan` function.
- :mod:`paxman.planner.heuristics` — the 7-step heuristic chain.
- :mod:`paxman.planner.scoring` — the cost-based scoring formula.
- :mod:`paxman.planner.policies` — budget / policy application.
- :mod:`paxman.planner.input_profile` — the lightweight input
  classifier (no capability invocation).
- :mod:`paxman.planner.field_plan` — :class:`FieldPlan` /
  :class:`FieldPlanStep` / :class:`ExecutionPlan` data models.
"""

from __future__ import annotations

from paxman.planner.field_plan import (
    ExecutionPlan,
    FieldPlan,
    FieldPlanStep,
    PlanDiagnostic,
)

__all__ = [
    "ExecutionPlan",
    "FieldPlan",
    "FieldPlanStep",
    "PlanDiagnostic",
]
