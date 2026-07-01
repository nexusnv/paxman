"""``regex_extraction`` V1 capability — pattern-based local extraction.

This capability extracts a value from raw input using an
ECMAScript-flavored regex (Python's :mod:`re` is ECMAScript-compatible
enough for V1). The pattern is supplied via :attr:`CapabilityContext.config`
as the ``"pattern"`` key (a string).

The capability produces **one candidate per match** in the input. If
the pattern contains a single **named group** ``(?P<name>...)``, the
matched value of that group is used (V1 simplification;
duplicate named groups are rejected). Otherwise the
whole match is used.

V1 surface:

- ``input_types`` = ``("STRING", "HTML_TEXT")``
- ``output_type`` = ``"STRING"``
- ``deterministic`` = ``True``
- ``cost_estimate`` = ``(tokens=0, ms=1, usd=0.0)`` (per
  ``docs/specs/capability-cost-model.md`` §3)

Reference constraints are **post-V1**
(per ``docs/reference/extending.md``); ``regex_extraction`` is purely a value-extraction step.
Validation is a separate capability.
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

__all__ = ["RegexExtractionCapability"]


class RegexExtractionCapability:
    """V1 ``regex_extraction`` capability.

    Extracts one or more values from raw input using a regex pattern.
    The pattern is supplied via :attr:`CapabilityContext.config`
    (``ctx.config["pattern"]``).

    Behavior:

    - The pattern is compiled once per call (per
      :class:`CapabilityContext`); the same compiled pattern is
      re-used for the whole input.
    - If the pattern contains exactly one named group
      ``(?P<name>...)``, the matched value of that group is used as
      the candidate value. The ``name`` is recorded in the evidence
      context.
    - If the pattern has no named groups, the whole match (``m.group(0)``)
      is used.
    - Multiple matches in the input produce multiple candidates (one
      per match), in left-to-right order.
    - If the pattern fails to compile, the capability returns a
      :class:`CapabilityResult` with an empty candidate list and an
      ``CAPABILITY_INVOKE_FAILED`` diagnostic.

    Examples:
        >>> cap = RegexExtractionCapability()
        >>> ctx = CapabilityContext(
        ...     raw_input=b"ACME Corp\\nInvoice #1234",
        ...     field_path="supplier_name",
        ...     field_type_name="STRING",
        ...     config={"pattern": r"^([A-Z][A-Za-z ]+)$"},
        ... )
        >>> result = cap.invoke(ctx)
        >>> [c.value for c in result.candidates]
        ['ACME Corp']
    """

    @property
    def spec(self) -> CapabilitySpec:
        """The :class:`CapabilitySpec` for ``regex_extraction@1.0``."""
        return _REGEX_EXTRACTION_SPEC

    def invoke(self, ctx: CapabilityContext) -> CapabilityResult:
        """Run the regex against the raw input.

        Args:
            ctx: The :class:`CapabilityContext`. ``ctx.config["pattern"]``
                must be a non-empty string.

        Returns:
            A :class:`CapabilityResult` with one :class:`Candidate`
            per match (or empty if no matches). Diagnostics:

            - ``PATTERN_NO_MATCH`` (INFO) if no match found.
            - ``CAPABILITY_INVOKE_FAILED`` (ERROR) if the pattern
              fails to compile.
        """
        pattern_str = ctx.config.get("pattern")
        if not isinstance(pattern_str, str) or not pattern_str:
            return CapabilityResult(
                candidates=(),
                diagnostics=(
                    Diagnostic(
                        code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                        severity=DiagnosticSeverity.ERROR,
                        message="regex_extraction: config['pattern'] must be a non-empty string",
                        context={"field_path": ctx.field_path},
                    ),
                ),
            )
        try:
            pattern = re.compile(pattern_str)
        except re.error as e:
            return CapabilityResult(
                candidates=(),
                diagnostics=(
                    Diagnostic(
                        code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                        severity=DiagnosticSeverity.ERROR,
                        message=f"regex_extraction: pattern failed to compile: {e}",
                        context={"field_path": ctx.field_path, "pattern": pattern_str},
                    ),
                ),
            )

        text = ctx.raw_input.decode("utf-8", errors="replace")
        named_groups = pattern.groupindex
        if len(named_groups) > 1:
            # V1 rejects multiple named groups (complexity guard).
            return CapabilityResult(
                candidates=(),
                diagnostics=(
                    Diagnostic(
                        code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                        severity=DiagnosticSeverity.ERROR,
                        message=(
                            "regex_extraction: V1 supports at most one named group per pattern, "
                            f"got {len(named_groups)}"
                        ),
                        context={
                            "field_path": ctx.field_path,
                            "group_names": list(named_groups.keys()),
                        },
                    ),
                ),
            )

        single_group_name: str | None = next(iter(named_groups)) if named_groups else None

        candidates: list[Candidate] = []
        evidence: list[EvidenceRef] = []
        for m in pattern.finditer(text):
            if single_group_name is not None:
                value = m.group(single_group_name)
                if value is None:
                    # Group did not participate in the match (e.g., in an
                    # alternation that didn't take this branch). Skip.
                    continue
            else:
                value = m.group(0)
            span = (m.start(), m.end())
            ev = EvidenceRef(
                capability_id="regex_extraction",
                capability_version="1.0",
                field_path=ctx.field_path,
                span=span,
                context={"group_name": single_group_name} if single_group_name else {},
            )
            evidence.append(ev)
            candidates.append(
                Candidate(
                    value=value,
                    evidence_refs=(ev,),
                )
            )

        if not candidates:
            return CapabilityResult(
                candidates=(),
                evidence=(),
                diagnostics=(
                    Diagnostic(
                        code=DiagnosticCode.PATTERN_NO_MATCH,
                        severity=DiagnosticSeverity.INFO,
                        message="regex_extraction: pattern did not match the input",
                        context={"field_path": ctx.field_path, "pattern": pattern_str},
                    ),
                ),
            )

        return CapabilityResult(
            candidates=tuple(candidates),
            evidence=tuple(evidence),
        )


#: Singleton spec for ``regex_extraction@1.0``. Reused across instances.
_REGEX_EXTRACTION_SPEC: typing.Final[CapabilitySpec] = CapabilitySpec(
    id="regex_extraction",
    version="1.0",
    input_types=("STRING", "HTML_TEXT"),
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

    registry.register(RegexExtractionCapability(), replace=True)


_register_on_import()
