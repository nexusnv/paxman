"""``CapabilityContext`` builder — converts a per-field invocation into a context.

The :class:`CapabilityContext` (defined in
:mod:`paxman.capabilities.base`) is the **only** input capabilities see.
The Executor builds a fresh :class:`CapabilityContext` for every
``Capability.invoke()`` call. This module isolates the construction
logic so the rest of the Executor can stay focused on walking the plan.

Design notes
------------

- Capabilities never read the raw input directly; they receive a
  :class:`CapabilityContext` whose ``raw_input`` is the executor's
  view of the input (per ``PACKAGE_STRUCTURE.md`` §5.4 invariant #6).
- Capabilities never read the canonical contract directly; the
  :class:`CapabilityContext` carries only the per-field metadata
  (path, type, and the per-step config from the :class:`FieldPlan`).
- The :class:`CapabilityContext` is **frozen** (per Sprint 3
  :class:`CapabilityContext` invariants). The Executor must not
  attempt to mutate it after construction.

The :class:`ContextBuilder` is a tiny class — it exists for two
reasons:

1. To keep the construction logic in one place (so changes to the
   context shape touch one file).
2. To make the construction **deterministic**: the same field plan
   step and the same input profile produce the same context,
   byte-for-byte.
"""

from __future__ import annotations

import typing

from paxman.capabilities.base import CapabilityContext
from paxman.capabilities.spec import CapabilityTier
from paxman.planner.field_plan import FieldPlanStep

__all__ = ["ContextBuilder"]


class ContextBuilder:
    """Builds :class:`CapabilityContext` records for capability invocations.

    Stateless and pure: :meth:`build` takes the per-step metadata and
    the executor's input view and returns a fresh
    :class:`CapabilityContext`. The builder itself holds no state
    across calls.

    Examples:
        >>> builder = ContextBuilder()
        >>> ctx = builder.build(
        ...     step=FieldPlanStep(
        ...         capability_id="regex_extraction",
        ...         capability_version="1.0",
        ...         config={"pattern": r"^ACME"},
        ...     ),
        ...     raw_input=b"ACME Corp",
        ...     field_path="supplier_name",
        ...     field_type_name="STRING",
        ...     input_profile_type="text",
        ...     tier=CapabilityTier.LOCAL_DETERMINISTIC,
        ... )
        >>> ctx.field_path
        'supplier_name'
    """

    def build(
        self,
        *,
        step: FieldPlanStep,
        raw_input: bytes,
        field_path: str,
        field_type_name: str,
        input_profile_type: str,
        tier: CapabilityTier,
        span: tuple[int, int] | None = None,
    ) -> CapabilityContext:
        """Build a :class:`CapabilityContext` for one capability invocation.

        Args:
            step: The :class:`FieldPlanStep` being executed. Its
                ``config`` is passed through to the capability.
            raw_input: The raw input bytes the capability may decode
                and parse. (The Executor owns the input; capabilities
                only see this view.)
            field_path: The :class:`CanonicalField` path being
                resolved (e.g., ``"supplier_name"``).
            field_type_name: The :class:`FieldType` value name
                (e.g., ``"STRING"``).
            input_profile_type: The :class:`InputProfile.input_type`
                (``"text"``, ``"html"``, etc.).
            tier: The :class:`CapabilityTier` of the capability
                being invoked.
            span: Optional ``(start, end)`` byte-offset pair into
                ``raw_input``. ``None`` means the whole input.
                Defaults to ``None``.

        Returns:
            A frozen :class:`CapabilityContext` ready to pass to
            ``capability.invoke(ctx)``.

        Raises:
            TypeError: If ``raw_input`` is not ``bytes`` or any other
                argument has the wrong type.
            ValueError: If a string field is empty.
        """
        # Oracle review F3: validate inputs up front so failures
        # surface as a structured diagnostic, not an
        # ``AttributeError`` deep in the capability.
        if not isinstance(raw_input, bytes):
            raise TypeError(f"raw_input must be bytes, got {type(raw_input).__name__}")
        if not isinstance(field_path, str) or not field_path:
            raise ValueError(f"field_path must be a non-empty string, got {field_path!r}")
        if not isinstance(field_type_name, str) or not field_type_name:
            raise ValueError(f"field_type_name must be a non-empty string, got {field_type_name!r}")
        if not isinstance(input_profile_type, str) or not input_profile_type:
            raise TypeError(
                f"input_profile_type must be a non-empty str, got {input_profile_type!r}"
            )
        if not isinstance(tier, CapabilityTier):
            raise TypeError(f"tier must be a CapabilityTier, got {type(tier).__name__}")

        # The step's config is a MappingProxyType (immutable view); the
        # CapabilityContext accepts a dict, so we copy the mapping
        # into a fresh dict. The capability is allowed to mutate
        # ``ctx.config`` (the Executor never reuses a context), and
        # we don't want a capability to be able to affect the plan.
        config: dict[str, typing.Any] = dict(step.config)
        # Tag the tier into the config so capabilities that care
        # (e.g., ``inference``) can short-circuit on tier without
        # re-reading the spec.
        config.setdefault("tier", tier.name)

        return CapabilityContext(
            raw_input=raw_input,
            field_path=field_path,
            field_type_name=field_type_name,
            config=config,
            input_profile_type=input_profile_type,
            span=span,
        )
