"""``validation`` V1 capability — verify a candidate value against a constraint.

This capability checks a candidate value against one or more
:class:`~paxman.contract._types.Constraint` rules attached to the
target :class:`~paxman.contract.canonical.CanonicalField`. It does
**not** modify the value; it just reports pass / fail diagnostics.

V1 constraint coverage (per
``EXTENDING.md`` §2.5):

- :attr:`ConstraintKind.MIN_LENGTH` — string / array minimum length.
- :attr:`ConstraintKind.MAX_LENGTH` — string / array maximum length.
- :attr:`ConstraintKind.PATTERN` — string regex.
- :attr:`ConstraintKind.MIN_VALUE` — numeric minimum.
- :attr:`ConstraintKind.MAX_VALUE` — numeric maximum.
- :attr:`ConstraintKind.ENUM` — closed-set membership.
- :attr:`ConstraintKind.ISO_4217` — ISO-4217 currency code (3
  uppercase ASCII letters).

**Reference constraints** (e.g., "total == sum(line_items[].price)")
are **post-V1** (per ``EXTENDING.md``).

V1 surface:

- ``input_types`` = ``("STRING", "INTEGER", "DECIMAL", "BOOLEAN", "DATE",
  "ENUM", "MONEY", "ARRAY", "OBJECT")`` — every V1 type.
- ``output_type`` = ``"BOOLEAN"`` (the validation pass/fail).
- ``deterministic`` = ``True``.
- ``cost_estimate`` = ``(tokens=0, ms=1, usd=0.0)`` (per
  ``docs/specs/capability-cost-model.md`` §3).
"""

from __future__ import annotations

import re
import typing

from paxman.capabilities.base import CapabilityContext
from paxman.capabilities.result import (
    Candidate,
    CapabilityResult,
    Diagnostic,
    DiagnosticCode,
    DiagnosticSeverity,
    EvidenceRef,
)
from paxman.capabilities.spec import CapabilitySpec, CapabilityTier, CostHint
from paxman.contract._types import Constraint, ConstraintKind

__all__ = ["ValidationCapability"]


#: ISO-4217 currency code pattern. Three uppercase ASCII letters.
_ISO_4217_PATTERN: typing.Final[re.Pattern[str]] = re.compile(r"^[A-Z]{3}$")


class ValidationCapability:
    """V1 ``validation`` capability.

    Validates a candidate value against the constraints on the
    target field. The capability takes a single candidate value
    via :attr:`CapabilityContext.config` (``ctx.config["value"]``) and
    the constraints via :attr:`CapabilityContext.config`
    (``ctx.config["constraints"]``, a tuple of
    :class:`~paxman.contract._types.Constraint`).

    Returns:

    - A single :class:`Candidate` with the validated value and an
      ``EvidenceRef`` whose ``context["validation_passed"]`` is
      ``True`` if **all** constraints pass, or
    - A single :class:`Candidate` with the original value plus a
      ``VALIDATION_FAILED`` diagnostic listing the failing constraints.

    In V1, ``validation`` is a **truth-reporter**, not a value-producer:
    it does not transform the value, only confirms or denies. The
    Reconciler reads the diagnostic to decide whether to
    accept the value.

    Examples:
        >>> from paxman.contract._types import Constraint, ConstraintKind
        >>> cap = ValidationCapability()
        >>> ctx = CapabilityContext(
        ...     raw_input=b"",
        ...     field_path="supplier_name",
        ...     field_type_name="STRING",
        ...     config={
        ...         "value": "ACME Corp",
        ...         "constraints": (
        ...             Constraint(kind=ConstraintKind.MIN_LENGTH, params={"min": 1}),
        ...         ),
        ...     },
        ... )
        >>> result = cap.invoke(ctx)
        >>> result.candidates[0].value
        'ACME Corp'
    """

    @property
    def spec(self) -> CapabilitySpec:
        """The :class:`CapabilitySpec` for ``validation@1.0``."""
        return _VALIDATION_SPEC

    def invoke(self, ctx: CapabilityContext) -> CapabilityResult:
        """Run the validation checks.

        Args:
            ctx: The :class:`CapabilityContext`. ``ctx.config`` must
                contain:

                - ``"value"``: the candidate value to validate (any
                  type; the constraint kind determines the check).
                - ``"constraints"``: a tuple/list of
                  :class:`~paxman.contract._types.Constraint`.

        Returns:
            A :class:`CapabilityResult` with one :class:`Candidate`
            (the input value) and:

            - empty ``diagnostics`` on pass,
            - a single ``VALIDATION_FAILED`` diagnostic on fail.
        """
        value = ctx.config.get("value")
        constraints = ctx.config.get("constraints", ())
        if not isinstance(constraints, (tuple, list)):
            return CapabilityResult(
                candidates=(),
                diagnostics=(
                    Diagnostic(
                        code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                        severity=DiagnosticSeverity.ERROR,
                        message=(
                            "validation: config['constraints'] must be a tuple or list, "
                            f"got {type(constraints).__name__}"
                        ),
                        context={"field_path": ctx.field_path},
                    ),
                ),
            )

        failures: list[dict[str, typing.Any]] = []
        for c in constraints:
            if not _is_constraint(c):
                failures.append(
                    {
                        "kind": "<unknown>",
                        "params": {},
                        "reason": f"not a Constraint instance (got {type(c).__name__})",
                    }
                )
                continue
            ok, reason = _check_constraint(c, value)
            if not ok:
                failures.append(
                    {
                        "kind": c.kind.value,
                        "params": dict(c.params),
                        "reason": reason,
                    }
                )

        evidence = (
            EvidenceRef(
                capability_id="validation",
                capability_version="1.0",
                field_path=ctx.field_path,
                context={"validation_passed": not failures, "failure_count": len(failures)},
            ),
        )

        if not failures:
            return CapabilityResult(
                candidates=(Candidate(value=value, evidence_refs=evidence),),
                evidence=evidence,
            )

        return CapabilityResult(
            candidates=(Candidate(value=value, evidence_refs=evidence),),
            evidence=evidence,
            diagnostics=(
                Diagnostic(
                    code=DiagnosticCode.VALIDATION_FAILED,
                    severity=DiagnosticSeverity.WARNING,
                    message=(f"validation: {len(failures)} constraint(s) failed"),
                    context={"field_path": ctx.field_path, "failures": failures},
                ),
            ),
        )


def _is_constraint(obj: object) -> bool:
    """Return True if *obj* looks like a Constraint (duck-typed)."""
    return hasattr(obj, "kind") and hasattr(obj, "params")


def _to_float(value: object) -> float | None:
    """Convert *value* to ``float``; return ``None`` on failure.

    Accepts ``int``, ``float``, ``str`` (decimal), and any
    :class:`numbers.Real` (via :func:`float`). Returns ``None``
    for non-numeric values so the caller can produce a clear
    diagnostic.
    """
    if isinstance(value, bool):
        return None  # bool is technically numeric; reject to avoid surprises
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _to_length(value: object) -> int | None:
    """Return the length of *value*; ``None`` if it has no length.

    Accepts ``str``, ``bytes``, ``list``, ``tuple``, ``dict``, and
    any other :class:`collections.abc.Sized` (via :func:`len`).
    Returns ``None`` for non-sized values so the caller can produce
    a clear diagnostic.
    """
    from collections.abc import Sized

    if isinstance(value, Sized):
        return len(value)
    return None


def _check_constraint(c: Constraint, value: object) -> tuple[bool, str]:
    """Run a single constraint check.

    Args:
        c: A :class:`Constraint`.
        value: The value to check.

    Returns:
        ``(True, "")`` on pass, ``(False, reason)`` on fail. For
        kinds with no V1 implementation, returns ``(True, "")``
        (no-op) so the caller does not block on a missing check.
    """
    kind = c.kind
    params = c.params

    if kind is ConstraintKind.MIN_LENGTH:
        n = _to_length(value)
        if n is None:
            return False, "value has no length"
        if n < int(params.get("min", 0)):
            return False, f"length {n} < min {params.get('min')}"
        return True, ""

    if kind is ConstraintKind.MAX_LENGTH:
        n = _to_length(value)
        if n is None:
            return False, "value has no length"
        if n > int(params.get("max", 0)):
            return False, f"length {n} > max {params.get('max')}"
        return True, ""

    if kind is ConstraintKind.PATTERN:
        if not isinstance(value, str):
            return False, f"value is not a string (got {type(value).__name__})"
        regex = params.get("regex")
        if not isinstance(regex, str):
            return False, "PATTERN constraint has no 'regex' param"
        try:
            if not re.search(regex, value):
                return False, f"value does not match pattern {regex!r}"
        except re.error as e:
            return False, f"invalid regex {regex!r}: {e}"
        return True, ""

    if kind is ConstraintKind.MIN_VALUE:
        n_f = _to_float(value)
        if n_f is None:
            return False, f"value is not numeric (got {type(value).__name__})"
        min_v = float(params.get("min", 0))
        if n_f < min_v:
            return False, f"value {value!r} < min {params.get('min')}"
        return True, ""

    if kind is ConstraintKind.MAX_VALUE:
        n2 = _to_float(value)
        if n2 is None:
            return False, f"value is not numeric (got {type(value).__name__})"
        max_v = float(params.get("max", 0))
        if n2 > max_v:
            return False, f"value {value!r} > max {params.get('max')}"
        return True, ""

    if kind is ConstraintKind.ENUM:
        values = params.get("values", ())
        if not isinstance(values, (tuple, list)):
            return False, "ENUM constraint has no 'values' list"
        if value not in values:
            return False, f"value {value!r} not in enum {list(values)!r}"
        return True, ""

    if kind is ConstraintKind.ISO_4217:
        if not isinstance(value, str) or not _ISO_4217_PATTERN.match(value):
            return False, f"value {value!r} is not a valid ISO-4217 code"
        return True, ""

    # Unknown constraint kinds: no-op (V1: should not happen; the
    # validator catches unknown kinds at the contract layer).
    return True, ""


#: Singleton spec for ``validation@1.0``. Reused across instances.
_VALIDATION_SPEC: typing.Final[CapabilitySpec] = CapabilitySpec(
    id="validation",
    version="1.0",
    input_types=(
        "STRING",
        "INTEGER",
        "DECIMAL",
        "BOOLEAN",
        "DATE",
        "ENUM",
        "MONEY",
        "ARRAY",
        "OBJECT",
    ),
    output_type="BOOLEAN",
    cost_estimate=CostHint(tokens=0, ms=1, usd=0.0),
    tier=CapabilityTier.LOCAL_DETERMINISTIC,
    deterministic=True,
    required_providers=(),
)
