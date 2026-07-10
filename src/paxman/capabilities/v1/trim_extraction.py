"""``trim_extraction`` V1 capability — strip leading/trailing junk from a value.

This is one of the two **post-extraction cleanup** capabilities
introduced in V1.1.0 (sub-issue #69 of #67). It operates on a
string value that has already been resolved by an upstream
extraction step (``text_extraction``, ``regex_extraction``,
``json_path_extraction``, ``csv_extraction``, ``xpath_extraction``,
or any other tier-1 capability).

The capability does **not** parse, does **not** look at the raw
input, does **not** read the canonical contract. It is a pure
string transform that reads its input from
``ctx.config["value"]`` (the same shape ``validation@1.0`` already
uses) and an optional ``chars`` set in ``ctx.config["chars"]``.

The default ``chars`` set is the **whitespace + common-punctuation
set** documented in the issue #69 spec. This default matches
``str.strip()`` semantics extended with the common punctuation that
real text extraction produces: ``:;. ,-_/\\|()[]{}`` plus
zero-width spaces ``\\u200b\\u200c\\u200d`` and the BOM ``\\ufeff``.

V1 surface:

- ``input_types`` = ``("STRING",)``
- ``output_type`` = ``"STRING"``
- ``deterministic`` = ``True``
- ``cost_estimate`` = ``(tokens=0, ms=1, usd=0.0)``
- ``tier`` = ``CapabilityTier.LOCAL_DETERMINISTIC``

Failure modes (each surfaces as a structured :class:`Diagnostic`):

- ``CAPABILITY_INVOKE_FAILED`` (ERROR) — ``config["value"]`` missing
  or not a string.
- ``CAPABILITY_INVOKE_FAILED`` (ERROR) — ``config["chars"]`` is set
  but is not a string (the chars are the literal characters to
  strip, not a regex).
- ``CAPABILITY_INVOKE_FAILED`` (ERROR) — ``config["chars"]`` is set
  but is empty (would be a programmer mistake).

Per V1 capability convention (mirroring :mod:`regex_extraction` and
the V1.1.0 format extractors), this module
:func:`_register_on_import` on import (ADR-0012). Third-party
capabilities use :func:`paxman.register_capability`.

Examples:
    >>> cap = TrimExtractionCapability()
    >>> ctx = CapabilityContext(
    ...     raw_input=b"",
    ...     field_path="supplier_name",
    ...     field_type_name="STRING",
    ...     config={"value": "  ACME Corp :"},
    ... )
    >>> result = cap.invoke(ctx)
    >>> result.candidates[0].value
    'ACME Corp'
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

__all__ = ["TrimExtractionCapability"]


#: The default character set stripped by ``trim_extraction@1.0``.
#:
#: This is the **whitespace + common-punctuation** set documented in
#: the issue #69 spec. It matches ``str.strip()`` semantics extended
#: with the punctuation that real text extraction produces and the
#: zero-width characters that sneak in from copy-paste pipelines.
#:
#: The set is intentionally fixed and documented. ``str.strip()``'s
#: default (whitespace only) leaves trailing colons, trailing dashes,
#: and trailing brackets in place; that is the gap this capability
#: closes. A caller can pass ``config["chars"]`` to override the
#: default.
#:
#: The set is a ``frozenset`` of single-character strings, *not* a
#: regex. ``str.strip(chars)`` is used directly.
_DEFAULT_CHARS: typing.Final[frozenset[str]] = frozenset(
    " \t\n\r\v\f"  # ASCII whitespace (matches str.strip() default)
    "\u200b\u200c\u200d"  # zero-width space, ZWNJ, ZWJ
    "\ufeff"  # BOM
    ":;.,"  # common sentence punctuation
    "-_/\\|"  # common separators
    "()[]{}"  # common brackets
)


class TrimExtractionCapability:
    """V1 ``trim_extraction`` capability.

    Strips leading and trailing characters from a pre-resolved
    string value. The character set defaults to the V1
    whitespace + common-punctuation set (``_DEFAULT_CHARS``) and
    can be overridden via ``ctx.config["chars"]``.

    The capability never reads ``ctx.raw_input``; that field is
    unused. The capability never reads the contract. The
    capability is a pure string transform.

    Behavior:

    - ``chars`` not set → strip the default
      ``_DEFAULT_CHARS`` set.
    - ``chars`` set to a non-empty string → strip exactly those
      characters (each character in *chars* is treated as a literal
      to strip, not as a regex).
    - ``chars`` set to an empty string → hard error
      (``CAPABILITY_INVOKE_FAILED``); the caller almost certainly
      made a mistake.

    Returns one :class:`Candidate` whose value is the trimmed
    form. The :class:`EvidenceRef.context` carries
    ``{"original_value": ..., "trimmed_chars": ..., "stripped_count": N}``
    so replay can reproduce the exact transform.

    On any failure mode the capability returns a
    :class:`CapabilityResult` with an empty ``candidates`` list and
    a single structured :class:`Diagnostic`; it never raises.
    """

    @property
    def spec(self) -> CapabilitySpec:
        """The :class:`CapabilitySpec` for ``trim_extraction@1.0``."""
        return _TRIM_EXTRACTION_SPEC

    @staticmethod
    def _failed(message: str, field_path: str, **ctx: object) -> CapabilityResult:
        """Build a ``CAPABILITY_INVOKE_FAILED`` result with one Diagnostic."""
        return CapabilityResult(
            candidates=(),
            diagnostics=(
                Diagnostic(
                    code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                    severity=DiagnosticSeverity.ERROR,
                    message=f"trim_extraction: {message}",
                    context={"field_path": field_path, **ctx},
                ),
            ),
        )

    @staticmethod
    def _normalize_chars(
        chars: object, field_path: str
    ) -> tuple[frozenset[str] | None, CapabilityResult | None]:
        """Validate and normalize the ``chars`` config.

        Returns ``(resolved, error_result)``. ``resolved`` is a
        ``frozenset`` of single-character strings, or ``None`` to
        fall back to ``_DEFAULT_CHARS``. ``error_result`` is
        non-``None`` if validation failed.
        """
        if chars is None:
            return None, None
        if not isinstance(chars, str):
            return None, TrimExtractionCapability._failed(
                "config['chars'] must be a str (literal characters to strip), "
                f"got {type(chars).__name__}",
                field_path,
            )
        if chars == "":
            return None, TrimExtractionCapability._failed(
                "config['chars'] is an empty string (use the default by omitting the key)",
                field_path,
            )
        return frozenset(chars), None

    def invoke(self, ctx: CapabilityContext) -> CapabilityResult:
        """Strip leading/trailing characters from a pre-resolved value.

        Args:
            ctx: The :class:`CapabilityContext`. Reads from
                ``ctx.config``:

                - ``"value"`` (required, ``str``) — the pre-resolved
                  string to trim.
                - ``"chars"`` (optional, ``str``) — literal
                  characters to strip. Defaults to
                  :data:`_DEFAULT_CHARS`.

                ``ctx.raw_input`` is **not** read.

        Returns:
            A :class:`CapabilityResult` with one :class:`Candidate`
            (the trimmed value) or, on failure, an empty
            ``candidates`` list and a single
            ``CAPABILITY_INVOKE_FAILED`` diagnostic.
        """
        # 1. Validate the value (post-resolution input pattern).
        value = ctx.config.get("value")
        if not isinstance(value, str):
            return self._failed(
                "config['value'] must be a str (post-resolution input)",
                ctx.field_path,
                got_type=type(value).__name__,
            )

        # 2. Validate the chars set.
        chars_set, err = self._normalize_chars(ctx.config.get("chars"), ctx.field_path)
        if err is not None:
            return err
        resolved_chars: frozenset[str] = chars_set if chars_set is not None else _DEFAULT_CHARS

        # 3. Apply the transform. ``str.strip(chars)`` treats each
        #    character in *chars* as a literal to strip; we adapt
        #    that to the frozenset representation by joining.
        chars_arg: str = "".join(sorted(resolved_chars))
        trimmed = value.strip(chars_arg)

        # 4. Compute the stripped-character count for evidence.
        #    This is informational (replay uses ``original_value`` +
        #    ``trimmed_chars`` to reproduce the transform), but it is
        #    useful for the caller to assert "did the trim actually
        #    do anything" in tests.
        stripped_count = len(value) - len(trimmed)

        evidence = (
            EvidenceRef(
                capability_id="trim_extraction",
                capability_version="1.0",
                field_path=ctx.field_path,
                context={
                    "original_value": value,
                    "trimmed_chars": sorted(resolved_chars),
                    "stripped_count": stripped_count,
                },
            ),
        )
        return CapabilityResult(
            candidates=(Candidate(value=trimmed, evidence_refs=evidence),),
            evidence=evidence,
        )


#: Singleton spec for ``trim_extraction@1.0``. Reused across instances.
_TRIM_EXTRACTION_SPEC: typing.Final[CapabilitySpec] = CapabilitySpec(
    id="trim_extraction",
    version="1.0",
    input_types=("STRING",),
    output_type="STRING",
    cost_estimate=CostHint(tokens=0, ms=1, usd=0.0),
    tier=CapabilityTier.LOCAL_DETERMINISTIC,
    deterministic=True,
    required_providers=(),
)


# Self-register. See ADR-0012: all V1 capabilities self-register on
# import for symmetry with the contract adapter side. Third-party
# capabilities use ``paxman.register_capability()`` (see
# ``docs/reference/extending.md`` §2.3).
def _register_on_import() -> None:
    from paxman.capabilities import registry

    registry.register(TrimExtractionCapability(), replace=True)


_register_on_import()
