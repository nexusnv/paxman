"""``lookup`` V1 capability — structured / retrieval-based extraction.

The V1 ``lookup`` capability is a **deterministic in-memory dict
backend**. It looks up a value in a
pre-configured table by the value of the current input (or a
literal key supplied via the capability's config).

Use case
--------

The V1 ``lookup`` is intended for **structured retrieval** — looking
up a value in a known table (e.g., a vendor master, a country code
mapping, a unit conversion table). It is **not** a vector search,
**not** an embedding-based lookup, and **not** an external database
query (those are V2).

Configuration
-------------

The table is supplied via :attr:`CapabilityContext.config`:

- ``"table"``: a ``dict[str, str]`` mapping lookup key to value.
- ``"key"``: optional ``str`` to use as the lookup key. If
  ``None`` (the default), the capability uses the full raw input
  decoded as UTF-8 as the key.
- ``"case_sensitive"``: optional ``bool`` (default ``True``). If
  ``False``, the lookup is case-insensitive; both the key and the
  table keys are lowercased before the comparison.

If the key is in the table, the capability returns one
:class:`Candidate` with the mapped value. If the key is not in the
table, the capability returns zero candidates and a
:class:`Diagnostic` with code ``PATTERN_NO_MATCH`` (the same code
``regex_extraction`` uses for misses — the contract is the same:
"no match, try the next step").

V1 surface:

- ``input_types`` = ``("STRING",)`` (the key is treated as a string).
- ``output_type`` = ``"STRING"`` (the looked-up value).
- ``deterministic`` = ``True``.
- ``cost_estimate`` = ``(tokens=0, ms=1, usd=0.0)`` (in-memory
  dict lookup is effectively free).
- ``tier`` = ``CapabilityTier.STRUCTURED_LOOKUP``.

The capability is **deterministic** by construction: the same
input bytes + the same config table → the same output, byte-for-byte.
Property tests pin this.

Examples:
    >>> cap = LookupCapability()
    >>> ctx = CapabilityContext(
    ...     raw_input=b"US",
    ...     field_path="country_name",
    ...     field_type_name="STRING",
    ...     config={"table": {"US": "United States", "DE": "Germany"}},
    ... )
    >>> result = cap.invoke(ctx)
    >>> result.candidates[0].value
    'United States'
"""

from __future__ import annotations

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

__all__ = ["LookupCapability"]


class LookupCapability:
    """V1 ``lookup`` capability.

    Performs a deterministic lookup in an in-memory ``dict``. The
    table is supplied via :attr:`CapabilityContext.config`.

    Behavior:

    - If ``config["key"]`` is set, use it as the lookup key.
    - Otherwise, decode ``ctx.raw_input`` as UTF-8 and use the
      decoded text as the key (trailing newlines and
      surrounding whitespace are stripped).
    - If the key is in the table, return one :class:`Candidate`
      with the mapped value plus an :class:`EvidenceRef` whose
      ``context`` records the lookup key (for provenance).
    - If the key is not in the table, return an empty
      :class:`CapabilityResult` with a ``PATTERN_NO_MATCH``
      diagnostic.
    - If the config is missing the ``"table"`` key, return an
      empty :class:`CapabilityResult` with a
      ``CAPABILITY_INVOKE_FAILED`` diagnostic.
    - If the table is malformed (e.g., not a dict, values are
      not strings), return an empty :class:`CapabilityResult`
      with a ``CAPABILITY_INVOKE_FAILED`` diagnostic.
    """

    @property
    def spec(self) -> CapabilitySpec:
        """The :class:`CapabilitySpec` for ``lookup@1.0``."""
        return _LOOKUP_SPEC

    def invoke(self, ctx: CapabilityContext) -> CapabilityResult:
        """Run the lookup.

        Args:
            ctx: The :class:`CapabilityContext`. ``ctx.config`` may
                contain:

                - ``"table"`` (required): a ``dict[str, str]``
                  mapping keys to values.
                - ``"key"`` (optional): an explicit lookup key.
                - ``"case_sensitive"`` (optional): a ``bool``
                  defaulting to ``True``.

        Returns:
            A :class:`CapabilityResult`:

            - One :class:`Candidate` on hit (with an
              :class:`EvidenceRef` recording the key + value).
            - Empty candidates + a ``PATTERN_NO_MATCH`` diagnostic
              on miss.
            - Empty candidates + a ``CAPABILITY_INVOKE_FAILED``
              diagnostic on malformed config.
        """
        table = ctx.config.get("table")
        if not isinstance(table, dict):
            return CapabilityResult(
                candidates=(),
                diagnostics=(
                    Diagnostic(
                        code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                        severity=DiagnosticSeverity.ERROR,
                        message=(
                            f"lookup: config['table'] must be a dict, got {type(table).__name__}"
                        ),
                        context={"field_path": ctx.field_path},
                    ),
                ),
            )
        # Validate that every value is a string. The capability's
        # declared output_type is STRING; non-string values
        # are a contract violation we surface as a diagnostic.
        bad_value: tuple[str, object] | None = next(
            ((k, v) for k, v in table.items() if not isinstance(v, str)),
            None,
        )
        if bad_value is not None:
            k, v = bad_value
            return CapabilityResult(
                candidates=(),
                diagnostics=(
                    Diagnostic(
                        code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                        severity=DiagnosticSeverity.ERROR,
                        message=(
                            "lookup: config['table'] values must be str, "
                            f"got {type(v).__name__} for key {k!r}"
                        ),
                        context={"field_path": ctx.field_path, "key": k},
                    ),
                ),
            )

        # Resolve the lookup key.
        key_raw = ctx.config.get("key")
        if key_raw is None:
            # Default: use the raw input, decoded and stripped.
            key_raw = ctx.raw_input.decode("utf-8", errors="replace").strip()
        if not isinstance(key_raw, str) or not key_raw:
            return CapabilityResult(
                candidates=(),
                diagnostics=(
                    Diagnostic(
                        code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                        severity=DiagnosticSeverity.ERROR,
                        message=(
                            "lookup: resolved key is empty "
                            "(config['key'] is empty and raw_input is empty)"
                        ),
                        context={"field_path": ctx.field_path},
                    ),
                ),
            )

        case_sensitive = ctx.config.get("case_sensitive", True)
        if not isinstance(case_sensitive, bool):
            return CapabilityResult(
                candidates=(),
                diagnostics=(
                    Diagnostic(
                        code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                        severity=DiagnosticSeverity.ERROR,
                        message=(
                            "lookup: config['case_sensitive'] must be a bool, "
                            f"got {type(case_sensitive).__name__}"
                        ),
                        context={"field_path": ctx.field_path},
                    ),
                ),
            )

        lookup_key = key_raw if case_sensitive else key_raw.lower()
        # Build a case-normalized view of the table for the
        # case-insensitive path. The view is computed per call
        # because the table is supplied via ctx.config; in V1
        # we do not cache (the Executor builds a fresh context
        # per invocation).
        if case_sensitive:
            value: str | None = table.get(lookup_key)
        else:
            value = next(
                (v for k, v in table.items() if k.lower() == lookup_key),
                None,
            )

        if value is None:
            return CapabilityResult(
                candidates=(),
                diagnostics=(
                    Diagnostic(
                        code=DiagnosticCode.PATTERN_NO_MATCH,
                        severity=DiagnosticSeverity.INFO,
                        message=(f"lookup: key {key_raw!r} not found in table"),
                        context={
                            "field_path": ctx.field_path,
                            "key": key_raw,
                            "case_sensitive": case_sensitive,
                            "table_size": len(table),
                        },
                    ),
                ),
            )

        evidence = (
            EvidenceRef(
                capability_id="lookup",
                capability_version="1.0",
                field_path=ctx.field_path,
                context={
                    "key": key_raw,
                    "case_sensitive": case_sensitive,
                    "table_size": len(table),
                },
            ),
        )
        return CapabilityResult(
            candidates=(Candidate(value=value, evidence_refs=evidence),),
            evidence=evidence,
        )


#: Singleton spec for ``lookup@1.0``. Reused across instances.
_LOOKUP_SPEC: typing.Final[CapabilitySpec] = CapabilitySpec(
    id="lookup",
    version="1.0",
    input_types=("STRING",),
    output_type="STRING",
    cost_estimate=CostHint(tokens=0, ms=1, usd=0.0),
    tier=CapabilityTier.STRUCTURED_LOOKUP,
    deterministic=True,
    required_providers=(),
)


# Self-register.
def _register_on_import() -> None:
    from paxman.capabilities import registry

    registry.register(LookupCapability(), replace=True)


_register_on_import()
