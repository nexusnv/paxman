"""Capability SPI — the Protocol for adding new capabilities.

A :class:`Capability` is a single atomic operation that produces
:class:`~paxman.capabilities.result.Candidate` values for one or more
field types. It carries a :class:`~paxman.capabilities.spec.CapabilitySpec`
declaring its metadata, and an ``invoke()`` method that runs against
a :class:`CapabilityContext`.

This module is the **only** capability-side interface; the Executor and the API talk to capabilities exclusively
through this Protocol. Third-party capabilities implement it
structurally (PEP 544) — no inheritance is required.

Public surface
--------------

- :class:`Capability` — the SPI Protocol. Re-exported in
  ``paxman.api.protocols``.
- :class:`CapabilityContext` — the input to ``invoke()``. The
  :class:`Capability` does not read raw input directly; the Executor
  builds the context.

Per ADR-0005 (Confidence Ownership), :class:`Capability.invoke` must
return a :class:`~paxman.capabilities.result.CapabilityResult` that
**does not** carry confidence. Confidence is the Reconciler's job.
"""

from __future__ import annotations

import typing

import attrs

from paxman.capabilities.result import CapabilityResult

__all__ = [
    "Capability",
    "CapabilityContext",
]


@attrs.frozen(slots=True)
class CapabilityContext:
    """The input to :meth:`Capability.invoke`.

    The Executor builds a :class:`CapabilityContext` per
    capability invocation. The capability never reads the raw input
    or the canonical contract directly — the context is its sole
    interface to the world (per ``PACKAGE_STRUCTURE.md`` §5.4
    invariant #6).

    Attributes:
        raw_input: The raw input bytes (UTF-8 encoded, replacement
            applied at the API layer). The capability may decode
            and parse this as needed; capabilities for HTML parse
            it, capabilities for regex match against its text
            form.
        field_path: The :class:`~paxman.contract.canonical.CanonicalField`
            path this invocation is solving (e.g., ``"supplier_name"``).
        field_type_name: The :class:`~paxman.types.FieldType` value
            (e.g., ``"STRING"``) of the field. Stored as ``str`` to
            avoid a circular import on :mod:`paxman.types` and to
            keep the context JSON-serializable.
        config: Optional capability-specific configuration (e.g.,
            the regex pattern for ``regex_extraction``). Defaults
            to an empty dict. Capabilities define their own
            ``config`` schema.
        input_profile_type: The :class:`InputProfile.input_type` for
            the raw input (``"text"``, ``"html"``, etc.). Stored as
            ``str`` for the same reason as ``field_type_name``.
            Defaults to ``"text"`` for backward-compat.
        span: Optional ``(start, end)`` byte-offset pair into
            ``raw_input`` indicating the candidate span to focus on.
            ``None`` means the whole input. Defaults to ``None``.

    Examples:
        >>> ctx = CapabilityContext(
        ...     raw_input=b"ACME Corp\\nInvoice #1234\\nTotal: $1,234.56 USD\\n",
        ...     field_path="supplier_name",
        ...     field_type_name="STRING",
        ... )
        >>> ctx.field_path
        'supplier_name'
    """

    raw_input: bytes = attrs.field()
    field_path: str = attrs.field()
    field_type_name: str = attrs.field()
    config: dict[str, typing.Any] = attrs.field(factory=dict)
    input_profile_type: str = "text"
    span: tuple[int, int] | None = None

    def __attrs_post_init__(self) -> None:
        """Validate invariants.

        Raises:
            TypeError: If ``raw_input`` is not bytes.
            ValueError: If ``field_path`` is empty, ``field_type_name``
                is empty, or ``span`` is malformed.
        """
        if not isinstance(self.raw_input, bytes):
            raise TypeError(f"raw_input must be bytes, got {type(self.raw_input).__name__}")
        if not isinstance(self.field_path, str) or not self.field_path:
            raise ValueError(f"field_path must be a non-empty string, got {self.field_path!r}")
        if not isinstance(self.field_type_name, str) or not self.field_type_name:
            raise ValueError(
                f"field_type_name must be a non-empty string, got {self.field_type_name!r}"
            )
        if self.span is not None:
            start, end = self.span
            if not isinstance(start, int) or not isinstance(end, int):
                raise TypeError(
                    f"span offsets must be ints, got ({type(start).__name__}, {type(end).__name__})"
                )
            if start < 0 or end < 0:
                raise ValueError(f"span offsets must be non-negative, got {self.span!r}")
            if start > end:
                raise ValueError(f"span start must be <= end, got {self.span!r}")


class Capability(typing.Protocol):
    """SPI: an atomic operation producing candidates and evidence.

    Implementations declare a :class:`~paxman.capabilities.spec.CapabilitySpec`
    via the ``spec`` property and accept a :class:`CapabilityContext`
    via ``invoke()``. The contract is purely structural (PEP 544):
    no inheritance is required.

    Per ADR-0005, ``invoke()`` MUST return a
    :class:`~paxman.capabilities.result.CapabilityResult` that does
    **not** carry a ``confidence`` field. The Reconciler
    is the sole confidence assigner.

    Public
        Re-exported in ``paxman.api.protocols``.
    """

    @property
    def spec(self) -> object:
        """Metadata describing the capability (:class:`CapabilitySpec`).

        The spec is used by the planner to select and configure
        capabilities for each :class:`~paxman.planner.FieldPlan`.
        It is also a stable identifier for the capability's
        determinism, cost, and input/output contract.
        """
        ...

    def invoke(self, ctx: CapabilityContext) -> CapabilityResult:
        """Execute the capability against a :class:`CapabilityContext`.

        Args:
            ctx: The capability context carrying the raw input,
                field path, field type, and any configuration needed
                for execution.

        Returns:
            A :class:`~paxman.capabilities.result.CapabilityResult`
            containing candidates, evidence, and diagnostics — but
            **no** confidence values. Per ADR-0005, capabilities
            never assign confidence.

        Raises:
            paxman.errors.CapabilityError: If the capability cannot
                complete (e.g., a non-recoverable error during
                execution). Recoverable issues (no matches, no
                candidates) are encoded as diagnostics, not
                exceptions.
        """
        ...
