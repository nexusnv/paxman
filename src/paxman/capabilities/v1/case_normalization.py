"""``case_normalization`` V1 capability — case-transform a pre-resolved value.

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
uses) and a ``mode`` declared in ``ctx.config["mode"]``.

Supported modes (V1):

- ``"lower"`` — ``str.lower()``.
- ``"upper"`` — ``str.upper()``.
- ``"title"`` — ``str.title()`` (word-initial upper, rest lower).
- ``"preserve"`` — return the input verbatim (no-op identity).

An unknown mode is a hard error (``CAPABILITY_INVOKE_FAILED``
diagnostic), never a silent no-op. This matches the project's
"validation rejects, doesn't guess" philosophy.

V1 surface:

- ``input_types`` = ``("STRING",)``
- ``output_type`` = ``"STRING"``
- ``deterministic`` = ``True``
- ``cost_estimate`` = ``(tokens=0, ms=1, usd=0.0)``
- ``tier`` = ``CapabilityTier.LOCAL_DETERMINISTIC``

Failure modes (each surfaces as a structured :class:`Diagnostic`):

- ``CAPABILITY_INVOKE_FAILED`` (ERROR) — ``config["value"]`` missing
  or not a string.
- ``CAPABILITY_INVOKE_FAILED`` (ERROR) — ``config["mode"]`` missing
  or not in the supported set.
- ``CAPABILITY_INVOKE_FAILED`` (ERROR) — ``config["value"]`` is not
  a string (e.g. ``None`` or ``bytes``).

Per V1 capability convention (mirroring :mod:`regex_extraction` and
the V1.1.0 format extractors), this module
:func:`_register_on_import` on import (ADR-0012). Third-party
capabilities use :func:`paxman.register_capability`.

Examples:
    >>> cap = CaseNormalizationCapability()
    >>> ctx = CapabilityContext(
    ...     raw_input=b"",
    ...     field_path="supplier_name",
    ...     field_type_name="STRING",
    ...     config={"value": "ACME Corp", "mode": "lower"},
    ... )
    >>> result = cap.invoke(ctx)
    >>> result.candidates[0].value
    'acme corp'
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

__all__ = ["CaseNormalizationCapability"]


#: The closed set of supported case-normalization modes (V1).
#:
#: The set is closed on purpose: an unknown mode is a
#: ``CAPABILITY_INVOKE_FAILED`` diagnostic, not a silent no-op. This
#: matches the project's "validation rejects, doesn't guess"
#: philosophy — a misspelled mode key in a contract should fail
#: loudly, not silently pass the value through.
_SUPPORTED_MODES: typing.Final[frozenset[str]] = frozenset({"lower", "upper", "title", "preserve"})


def _normalize(value: str, mode: str) -> str:
    """Apply *mode* to *value*.

    Pure function; no I/O; no exception handling. The caller is
    responsible for validating *mode* and *value* type first
    (this function trusts its inputs).
    """
    if mode == "lower":
        return value.lower()
    if mode == "upper":
        return value.upper()
    if mode == "title":
        return value.title()
    # mode == "preserve" is the explicit no-op identity.
    return value


class CaseNormalizationCapability:
    """V1 ``case_normalization`` capability.

    Normalizes the case of a pre-resolved string value. The input
    is read from ``ctx.config["value"]`` (the post-resolution
    pattern) and the target case from ``ctx.config["mode"]``.

    The capability never reads ``ctx.raw_input``; that field is
    unused. The capability never reads the contract. The
    capability is a pure string transform.

    Behavior:

    - ``mode == "lower"`` → ``value.lower()``.
    - ``mode == "upper"`` → ``value.upper()``.
    - ``mode == "title"`` → ``value.title()``.
    - ``mode == "preserve"`` → the input value returned verbatim.

    Returns one :class:`Candidate` whose value is the case-normalized
    form. The :class:`EvidenceRef.context` carries
    ``{"original_value": ..., "mode": ...}`` so replay can
    reproduce the exact transform.

    On any failure mode the capability returns a
    :class:`CapabilityResult` with an empty ``candidates`` list and
    a single structured :class:`Diagnostic`; it never raises.
    """

    @property
    def spec(self) -> CapabilitySpec:
        """The :class:`CapabilitySpec` for ``case_normalization@1.0``."""
        return _CASE_NORMALIZATION_SPEC

    @staticmethod
    def _failed(message: str, field_path: str, **ctx: object) -> CapabilityResult:
        """Build a ``CAPABILITY_INVOKE_FAILED`` result with one Diagnostic."""
        return CapabilityResult(
            candidates=(),
            diagnostics=(
                Diagnostic(
                    code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                    severity=DiagnosticSeverity.ERROR,
                    message=f"case_normalization: {message}",
                    context={"field_path": field_path, **ctx},
                ),
            ),
        )

    def invoke(self, ctx: CapabilityContext) -> CapabilityResult:
        """Normalize the case of a pre-resolved value.

        Args:
            ctx: The :class:`CapabilityContext`. Reads from
                ``ctx.config``:

                - ``"value"`` (required, ``str``) — the pre-resolved
                  string to normalize.
                - ``"mode"`` (required, ``str``) — one of
                  ``{"lower", "upper", "title", "preserve"}``.

                ``ctx.raw_input`` is **not** read.

        Returns:
            A :class:`CapabilityResult` with one :class:`Candidate`
            (the case-normalized value) or, on failure, an empty
            ``candidates`` list and a single
            ``CAPABILITY_INVOKE_FAILED`` diagnostic.
        """
        # 1. Validate the value. We require a string; everything else
        #    is a hard error (no coercion from bytes, no None, no
        #    silent no-op). This is the post-resolution input
        #    pattern — the value has already been produced by an
        #    upstream capability, so any non-string here is a real
        #    bug, not a recoverable condition.
        value = ctx.config.get("value")
        if not isinstance(value, str):
            return self._failed(
                "config['value'] must be a str (post-resolution input)",
                ctx.field_path,
                got_type=type(value).__name__,
            )

        # 2. Validate the mode. Unknown mode is a hard error, not
        #    a silent no-op — the project explicitly rejects "guess
        #    and pass" behavior (see the case_normalization spec in
        #    issue #69).
        mode = ctx.config.get("mode")
        if not isinstance(mode, str) or mode not in _SUPPORTED_MODES:
            return self._failed(
                f"config['mode'] must be one of {sorted(_SUPPORTED_MODES)}, got {mode!r}",
                ctx.field_path,
                mode=mode,
                supported_modes=sorted(_SUPPORTED_MODES),
            )

        # 3. Apply the transform. The pure helper trusts its
        #    inputs; we have already validated both arguments.
        normalized = _normalize(value, mode)

        evidence = (
            EvidenceRef(
                capability_id="case_normalization",
                capability_version="1.0",
                field_path=ctx.field_path,
                context={"original_value": value, "mode": mode},
            ),
        )
        return CapabilityResult(
            candidates=(Candidate(value=normalized, evidence_refs=evidence),),
            evidence=evidence,
        )


#: Singleton spec for ``case_normalization@1.0``. Reused across instances.
_CASE_NORMALIZATION_SPEC: typing.Final[CapabilitySpec] = CapabilitySpec(
    id="case_normalization",
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

    registry.register(CaseNormalizationCapability(), replace=True)


_register_on_import()
