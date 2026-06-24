"""Explicit UNRESOLVED state handling for the Reconciler.

When the Reconciler cannot produce a value meeting the field's
``confidence_threshold``, it must emit an explicit ``UNRESOLVED``
:class:`~paxman.reconciler.truth.ResolvedResult` (per
``PACKAGE_STRUCTURE.md`` §7.4 invariant #6: "Unresolved fields are
explicit, never silent").

The :func:`apply_fallback` function consults the field's
:class:`~paxman.contract._types.ResolutionPolicy` to decide what to do
with an unresolvable field:

- :attr:`ResolutionStrategy.UNRESOLVED` (default): mark the field
  ``UNRESOLVED`` with ``UNTRUSTED`` confidence and a diagnostic.
- :attr:`ResolutionStrategy.USE_DEFAULT`: if the field has a default,
  use the default with ``MEDIUM`` confidence. Otherwise, mark
  ``UNRESOLVED`` (defensive).
- :attr:`ResolutionStrategy.REQUIRE_HUMAN`: mark ``UNRESOLVED`` with
  an additional diagnostic noting that human review is required.

This module never assigns confidence freely; it only constructs
:class:`ResolvedResult` instances that conform to the truth.py
invariants (status="UNRESOLVED" → confidence=0.0,
confidence_band=UNTRUSTED; status="RESOLVED" → confidence > 0 and
value != None).
"""

from __future__ import annotations

from paxman.capabilities.result import Diagnostic, DiagnosticCode, DiagnosticSeverity
from paxman.contract._types import ResolutionStrategy
from paxman.contract.canonical import CanonicalField
from paxman.reconciler.truth import ResolvedResult
from paxman.types import ConfidenceBand

__all__ = ["apply_fallback", "make_unresolved_result", "should_use_default"]


def make_unresolved_result(
    *,
    field: CanonicalField,
    reason: str,
    diagnostics: tuple[Diagnostic, ...] = (),
) -> ResolvedResult:
    """Create a :class:`ResolvedResult` for an unresolved field.

    The returned result has:

    - ``status = "UNRESOLVED"``
    - ``confidence = 0.0``
    - ``confidence_band = ConfidenceBand.UNTRUSTED``
    - ``value = None``
    - A diagnostic explaining the reason (if ``reason`` is non-empty)

    Args:
        field: The :class:`CanonicalField` that could not be resolved.
        reason: A short reason string (e.g., ``"no_candidates"``,
            ``"below_threshold"``, ``"validation_failed"``). Used
            only for diagnostics; the caller can override.
        diagnostics: Additional pre-built diagnostics to attach.

    Returns:
        A :class:`ResolvedResult` with status ``"UNRESOLVED"``.

    Raises:
        TypeError: If ``field`` is not a :class:`CanonicalField`.
    """
    if not isinstance(field, CanonicalField):
        raise TypeError(f"field must be a CanonicalField, got {type(field).__name__}")
    diags: list[Diagnostic] = list(diagnostics)
    if reason:
        diags.append(
            Diagnostic(
                code=DiagnosticCode.CAPABILITY_OK,
                severity=DiagnosticSeverity.INFO,
                message=f"field unresolved: {reason}",
                context={"field_path": field.path, "reason": reason},
            )
        )
    return ResolvedResult(
        field_id=field.id,
        field_path=field.path,
        field_type_name=field.type.name,
        value=None,
        confidence=0.0,
        confidence_band=ConfidenceBand.UNTRUSTED,
        diagnostics=tuple(diags),
        status="UNRESOLVED",
    )


def should_use_default(field: CanonicalField) -> bool:
    """Check if the field's fallback policy allows using the default value.

    Returns ``True`` if and only if:

    - ``field.fallback_policy.strategy is ResolutionStrategy.USE_DEFAULT``, AND
    - ``field.default`` is not ``None``.

    Args:
        field: The :class:`CanonicalField` to inspect.

    Returns:
        ``True`` if the field should use its default on fallback.

    Raises:
        TypeError: If ``field`` is not a :class:`CanonicalField`.
    """
    if not isinstance(field, CanonicalField):
        raise TypeError(f"field must be a CanonicalField, got {type(field).__name__}")
    if field.fallback_policy.strategy is not ResolutionStrategy.USE_DEFAULT:
        return False
    return field.default is not None


def apply_fallback(
    *,
    field: CanonicalField,
    reason: str,
    diagnostics: tuple[Diagnostic, ...] = (),
) -> ResolvedResult:
    """Apply the field's fallback policy to produce a :class:`ResolvedResult`.

    If :func:`should_use_default` returns ``True`` for *field*, returns
    a ``RESOLVED`` result with the field's default value and
    ``ConfidenceBand.MEDIUM`` (the "best we have is the default"
    signal). Otherwise, returns an explicit ``UNRESOLVED`` result.

    The ``REQUIRE_HUMAN`` strategy also falls through to
    ``UNRESOLVED`` in V1, but adds a diagnostic noting that human
    review is required.

    Args:
        field: The :class:`CanonicalField` to apply fallback to.
        reason: Reason string for the diagnostic (if unresolved).
        diagnostics: Additional pre-built diagnostics to attach.

    Returns:
        A :class:`ResolvedResult` — either ``RESOLVED`` (with default)
        or ``UNRESOLVED``.

    Raises:
        TypeError: If ``field`` is not a :class:`CanonicalField`.
    """
    if not isinstance(field, CanonicalField):
        raise TypeError(f"field must be a CanonicalField, got {type(field).__name__}")
    if should_use_default(field):
        # Use the default. Confidence is MEDIUM (0.60) by convention.
        diags: list[Diagnostic] = list(diagnostics)
        diags.append(
            Diagnostic(
                code=DiagnosticCode.CAPABILITY_OK,
                severity=DiagnosticSeverity.INFO,
                message="used field default (fallback policy: USE_DEFAULT)",
                context={"field_path": field.path, "fallback": "USE_DEFAULT"},
            )
        )
        return ResolvedResult(
            field_id=field.id,
            field_path=field.path,
            field_type_name=field.type.name,
            value=field.default,
            confidence=0.60,
            confidence_band=ConfidenceBand.MEDIUM,
            diagnostics=tuple(diags),
            status="RESOLVED",
            merge_strategy_used="USE_DEFAULT",
        )
    diags = list(diagnostics)
    if field.fallback_policy.strategy is ResolutionStrategy.REQUIRE_HUMAN:
        diags.append(
            Diagnostic(
                code=DiagnosticCode.CAPABILITY_OK,
                severity=DiagnosticSeverity.WARNING,
                message="field requires human review (fallback policy: REQUIRE_HUMAN)",
                context={"field_path": field.path, "fallback": "REQUIRE_HUMAN"},
            )
        )
    return make_unresolved_result(field=field, reason=reason, diagnostics=tuple(diags))
