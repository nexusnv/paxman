"""Apply field constraints and detect prompt-injection in candidates.

This module is part of the Reconciler's per-field pipeline (called
from :mod:`paxman.reconciler.reconciler`). It performs two checks on
each candidate:

1. **Constraint validation.** Run the candidate's value through every
   :class:`~paxman.contract._types.Constraint` attached to the field.
   The check is delegated to
   :func:`paxman.validation.constraints.check_constraint`, the
   pure helper used by the ``validation`` capability. The Reconciler
   does **not** invoke the capability — it calls the helper directly
   (per `ADR-0003`: the Reconciler never executes capabilities).

2. **Prompt-injection detection.** A heuristic check for common
   prompt-injection patterns in string values. The Reconciler
   rejects any candidate whose value matches a known injection
   pattern (per the sprint spec: "a prompt-injection candidate from
   prompt_injection.txt is rejected by the Reconciler").

Constraint validation vs the validation capability
--------------------------------------------------

The :class:`~paxman.capabilities.v1.validation.ValidationCapability`
is a *capability*: a capability invocation is part of a
:class:`~paxman.planner.field_plan.FieldPlan` and is invoked by the
Executor. The Reconciler does not run capabilities. Instead, it
imports the same underlying pure check
(:func:`paxman.validation.constraints.check_constraint`) used by the
capability. This is
deliberately the "honest" path: the Reconciler applies the same
rules the capability would, without going through the capability
machinery.

The :class:`ValidationResult` data class carries the outcome of
both checks. The Reconciler uses the result to:

- Filter out candidates that match prompt-injection patterns.
- Record a constraint-pass / constraint-fail diagnostic on the
  :class:`~paxman.reconciler.truth.ResolvedResult`.
- Set the ``has_validation_pass`` flag for the confidence assignment.
"""

from __future__ import annotations

import re
import typing

import attrs

from paxman.capabilities.result import Candidate
from paxman.contract._types import ConstraintKind
from paxman.contract.canonical import CanonicalField
from paxman.validation.constraints import check_constraint as _check_constraint

__all__ = [
    "PROMPT_INJECTION_PATTERNS",
    "ValidationResult",
    "is_prompt_injection",
    "validate_candidate",
    "validate_inference_candidates",
]


#: The closed set of prompt-injection patterns the V1 Reconciler
#: rejects. Each pattern is a case-insensitive substring match
#: (compiled with :func:`re.compile` and ``re.IGNORECASE``).
#:
#: The set is closed in V1 — adding a pattern requires an ADR. The
#: patterns are deliberately conservative (specific phrasings
#: commonly used in injection attempts); broader heuristics belong
#: in a future capability, not the Reconciler.
PROMPT_INJECTION_PATTERNS: typing.Final[tuple[str, ...]] = (
    "ignore all previous instructions",
    "ignore previous instructions",
    "you are now a",
    "disregard the schema",
    "output the literal string",
    "forget your previous instructions",
    "new task:",
    "system: you are",
)

#: Compiled regexes for the prompt-injection patterns.
_COMPILED_INJECTION_PATTERNS: typing.Final[tuple[re.Pattern[str], ...]] = tuple(
    re.compile(re.escape(p), re.IGNORECASE) for p in PROMPT_INJECTION_PATTERNS
)


@attrs.frozen(slots=True)
class ValidationResult:
    """Result of validating a candidate against field constraints.

    Attributes:
        passed: ``True`` if all constraints passed (or there are
            no constraints). ``False`` if any constraint failed.
        failures: Tuple of per-constraint failure records
            (``{"kind": str, "params": dict, "reason": str}``).
        is_prompt_injection: ``True`` if the value matched a known
            prompt-injection pattern. Defaults to ``False``.
    """

    passed: bool = True
    failures: tuple[dict[str, typing.Any], ...] = ()
    is_prompt_injection: bool = False

    def __attrs_post_init__(self) -> None:
        """Validate invariants.

        Raises:
            TypeError: If any field has the wrong type.
        """
        if not isinstance(self.passed, bool):
            raise TypeError(f"passed must be a bool, got {type(self.passed).__name__}")
        if not isinstance(self.failures, tuple):
            raise TypeError(f"failures must be a tuple, got {type(self.failures).__name__}")
        if not isinstance(self.is_prompt_injection, bool):
            raise TypeError(
                f"is_prompt_injection must be a bool, got {type(self.is_prompt_injection).__name__}"
            )
        for f in self.failures:
            if not isinstance(f, dict):
                raise TypeError(f"each failure must be a dict, got {type(f).__name__}: {f!r}")


def is_prompt_injection(value: object) -> bool:
    """Detect common prompt-injection patterns in string values.

    The check is a case-insensitive substring search against the
    closed set of :data:`PROMPT_INJECTION_PATTERNS`. Non-string
    values return ``False`` (the V1 heuristic is text-only).

    Args:
        value: Any candidate value.

    Returns:
        ``True`` if *value* is a string and matches a known
        prompt-injection pattern. ``False`` otherwise.
    """
    if not isinstance(value, str):
        return False
    for pattern in _COMPILED_INJECTION_PATTERNS:
        if pattern.search(value):
            return True
    return False


def _is_constraint_like(obj: object) -> bool:
    """Duck-type check for Constraint-shaped objects.

    The Reconciler accepts either a real
    :class:`~paxman.contract._types.Constraint` or any object with
    ``.kind`` and ``.params`` attributes (for tests and adapters
    that produce duck-typed constraint-like objects).
    """
    return hasattr(obj, "kind") and hasattr(obj, "params")


def validate_candidate(
    candidate: Candidate,
    *,
    field: CanonicalField,
) -> ValidationResult:
    """Validate a candidate value against the field's constraints.

    Runs every :class:`Constraint` attached to *field* through
    :func:`~paxman.validation.constraints.check_constraint`.
    Also runs the prompt-injection heuristic on string values.

    Args:
        candidate: The :class:`Candidate` to validate.
        field: The :class:`CanonicalField` whose constraints apply.

    Returns:
        A :class:`ValidationResult` with pass/fail status, per-constraint
        failure details, and the prompt-injection flag.

    Raises:
        TypeError: If ``candidate`` is not a Candidate or ``field`` is
            not a CanonicalField.
    """
    if not isinstance(candidate, Candidate):
        raise TypeError(f"candidate must be a Candidate, got {type(candidate).__name__}")
    if not isinstance(field, CanonicalField):
        raise TypeError(f"field must be a CanonicalField, got {type(field).__name__}")

    # Prompt-injection check first (text-only, fast).
    injection = is_prompt_injection(candidate.value)

    failures: list[dict[str, typing.Any]] = []
    for c in field.constraints:
        if not _is_constraint_like(c):
            failures.append(
                {
                    "kind": "<unknown>",
                    "params": {},
                    "reason": f"not a Constraint instance (got {type(c).__name__})",
                }
            )
            continue
        try:
            ok, reason = _check_constraint(c, candidate.value)
        except Exception as e:
            ok = False
            reason = f"constraint check raised: {e!r}"
        if not ok:
            kind = getattr(c, "kind", None)
            kind_name = kind.value if isinstance(kind, ConstraintKind) else str(kind)
            params = getattr(c, "params", {})
            failures.append(
                {
                    "kind": kind_name,
                    "params": dict(params) if isinstance(params, dict) else {},
                    "reason": reason,
                }
            )

    return ValidationResult(
        passed=not failures,
        failures=tuple(failures),
        is_prompt_injection=injection,
    )


def validate_inference_candidates(
    candidates: tuple[Candidate, ...],
    *,
    field: CanonicalField,
) -> tuple[Candidate, ...]:
    """Filter candidates through validation.

    Behavior:

    - **Prompt-injection candidates are dropped** (the Reconciler
      never accepts them). The caller is expected to record a
      diagnostic noting the rejection.
    - **Candidates that fail constraints are kept** but flagged —
      the Reconciler still considers them, but records the
      constraint-fail diagnostic and downgrades confidence.
    - **Candidates that pass both checks are kept unchanged.**

    This function does not modify the input candidates; it returns
    a new tuple.

    Args:
        candidates: Tuple of :class:`Candidate` to filter.
        field: The :class:`CanonicalField` to validate against.

    Returns:
        A tuple of :class:`Candidate` with prompt-injection
        candidates removed.

    Raises:
        TypeError: If inputs are of the wrong type.
    """
    if not isinstance(candidates, tuple):
        raise TypeError(f"candidates must be a tuple, got {type(candidates).__name__}")
    if not isinstance(field, CanonicalField):
        raise TypeError(f"field must be a CanonicalField, got {type(field).__name__}")
    kept: list[Candidate] = []
    for c in candidates:
        if not isinstance(c, Candidate):
            raise TypeError(f"all candidates must be Candidate, got {type(c).__name__}")
        if is_prompt_injection(c.value):
            continue
        kept.append(c)
    return tuple(kept)
