"""``xpath_extraction`` V1 capability — limited-XPath XML/HTML extraction.

Extracts one :class:`Candidate` per matched element of an XML or HTML
document using a documented subset of XPath. The path is supplied via
:attr:`CapabilityContext.config` as the ``"xpath"`` key (a string).

The capability owns XML parsing and path evaluation via
:mod:`xml.etree.ElementTree`. The planner does not need to know
about XML.

The path vocabulary is intentionally narrower than full XPath 1.0:

- Absolute paths: ``/root/child/grandchild``.
- Child element names.
- Attribute predicates: ``[@attr="value"]``.
- Positional indexes: ``[N]``.

Namespace handling is explicit: prefixes must be declared in
``ctx.config["namespaces"]`` (a ``dict[str, str]``); undeclared
prefixes are an unsupported-syntax failure, not a silent drop.

Unsupported syntax (functions, axes, wildcards, ``text()``) returns
a ``CAPABILITY_INVOKE_FAILED`` diagnostic — never a silent miss.

V1 surface:

- ``input_types`` = ``("STRING", "HTML_TEXT", "MIXED")``
- ``output_type`` = ``"STRING"``
- ``deterministic`` = ``True``
- ``cost_estimate`` = ``(tokens=0, ms=1, usd=0.0)``
- ``tier`` = ``CapabilityTier.LOCAL_DETERMINISTIC``

Failure modes:

- ``CAPABILITY_INVOKE_FAILED`` (ERROR) — ``config["xpath"]`` missing
  or empty.
- ``CAPABILITY_INVOKE_FAILED`` (ERROR) — input is not valid XML.
- ``CAPABILITY_INVOKE_FAILED`` (ERROR) — XPath syntax outside the
  documented subset, or an undeclared namespace prefix.
- ``PATTERN_NO_MATCH`` (INFO) — XPath matches no elements.

Per V1 capability convention (mirroring :mod:`regex_extraction`),
this module does **not** self-register. Callers must register it
explicitly via :func:`paxman.capabilities.registry.register` or
:func:`paxman.register_capability`. The :mod:`paxman.capabilities.v1`
package imports it for type resolution / importability only.

Examples:
    >>> cap = XPathExtractionCapability()
    >>> ctx = CapabilityContext(
    ...     raw_input=b"<root><supplier>ACME</supplier></root>",
    ...     field_path="supplier_name",
    ...     field_type_name="STRING",
    ...     config={"xpath": "/root/supplier"},
    ... )
    >>> result = cap.invoke(ctx)
    >>> [c.value for c in result.candidates]
    ['ACME']
"""

from __future__ import annotations

import typing
import xml.etree.ElementTree as _stdlib_ET  # nosec B405  (stdlib fallback only; defusedxml path is the hardened one)

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
from paxman.logging import get_logger

__all__ = ["XPathExtractionCapability"]


_log = get_logger("paxman.capabilities.xpath_extraction")


# --- XML backend feature-detect (ADR-0013) -----------------------------------
# Prefer ``defusedxml.ElementTree`` when the ``xml-secure`` extra is installed;
# fall back to stdlib with a one-shot INFO log otherwise. ``defusedxml`` is
# the canonical fix for bandit B314 / ruff S314 (see ADR-0013). The fallback
# is observable via the log so callers who care about XML security can
# detect the unhardened mode at startup.
try:
    from defusedxml.common import (  # type: ignore[import-untyped]
        DefusedXmlException as _DefusedXmlException,
    )
    from defusedxml.ElementTree import (  # type: ignore[import-untyped]
        fromstring as _defused_fromstring,
    )
except ImportError:  # pragma: no cover  (defusedxml is always installed in the test env)
    _defused_fromstring = None
    _DefusedXmlException = None


if _defused_fromstring is not None and _DefusedXmlException is not None:
    _fromstring = _defused_fromstring
    _XML_BACKEND: str = "defusedxml"
    _XML_PARSE_ERRORS: tuple[type[BaseException], ...] = (
        _stdlib_ET.ParseError,
        _DefusedXmlException,
    )
else:  # pragma: no cover  (defusedxml is always installed in the test env)
    _fromstring = _stdlib_ET.fromstring
    _XML_BACKEND = "stdlib"
    _XML_PARSE_ERRORS = (_stdlib_ET.ParseError,)
    _log.info(
        "xpath_extraction: using stdlib XML parser "
        "(install paxman[xml-secure] for hardened parsing)",
        backend="stdlib",
        hint="pip install paxman[xml-secure]",
    )


#: Singleton spec for ``xpath_extraction@1.0``. Reused across instances.
_XPATH_EXTRACTION_SPEC: typing.Final[CapabilitySpec] = CapabilitySpec(
    id="xpath_extraction",
    version="1.0",
    input_types=("STRING", "HTML_TEXT", "MIXED"),
    output_type="STRING",
    cost_estimate=CostHint(tokens=0, ms=1, usd=0.0),
    tier=CapabilityTier.LOCAL_DETERMINISTIC,
    deterministic=True,
    required_providers=(),
)


#: Tokens that, if present in the xpath, mean we are outside the
#: documented subset. We reject the xpath before calling
#: :func:`Element.findall`.
_UNSUPPORTED_TOKENS: typing.Final[tuple[str, ...]] = (
    "(",
    "text()",
    "node()",
    "::",
    "*[",
    # The ``//`` abbreviation (descendant-or-self axis) is not in the
    # V1 documented subset. V1 supports absolute child-element paths
    # only. ``if "//" in xpath`` is a safe substring check: a valid
    # absolute path like ``/root/item`` does not contain ``//``.
    "//",
)


class XPathExtractionCapability:
    """V1 ``xpath_extraction`` capability.

    Extracts one value per matched XML element using a documented
    subset of XPath.
    """

    @property
    def spec(self) -> CapabilitySpec:
        """The :class:`CapabilitySpec` for ``xpath_extraction@1.0``."""
        return _XPATH_EXTRACTION_SPEC

    @staticmethod
    def _check_unsupported(xpath: str) -> str | None:
        """Return an error message if *xpath* uses unsupported syntax, else ``None``."""
        for token in _UNSUPPORTED_TOKENS:
            if token in xpath:
                return f"unsupported xpath syntax: contains {token!r}"
        if not xpath.startswith("/"):
            return f"unsupported xpath syntax {xpath!r} (V1 supports absolute paths only)"
        return None

    @staticmethod
    def _check_undeclared_prefixes(xpath: str, namespaces: dict[str, str]) -> str | None:
        """Return an error message if any namespace prefix is undeclared, else ``None``."""
        for token in xpath.split("/"):
            if ":" not in token or token.startswith("@"):
                continue
            prefix = token.split("[", 1)[0].split(":", 1)[0]
            if prefix and prefix not in namespaces:
                return (
                    f"undeclared namespace prefix {prefix!r} (declare it in config['namespaces'])"
                )
        return None

    def invoke(self, ctx: CapabilityContext) -> CapabilityResult:
        """Parse the input as XML and evaluate the XPath expression.

        Args:
            ctx: The :class:`CapabilityContext`. ``ctx.config["xpath"]``
                must be a non-empty string. ``ctx.config["namespaces"]``
                (optional) is a ``dict[str, str]`` of prefix → URI.

        Returns:
            A :class:`CapabilityResult` with one :class:`Candidate` per
            matched element.
        """
        xpath_obj = ctx.config.get("xpath")
        if not isinstance(xpath_obj, str) or not xpath_obj:
            return CapabilityResult(
                candidates=(),
                diagnostics=(
                    Diagnostic(
                        code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                        severity=DiagnosticSeverity.ERROR,
                        message=("xpath_extraction: config['xpath'] must be a non-empty string"),
                        context={"field_path": ctx.field_path},
                    ),
                ),
            )
        xpath: str = xpath_obj

        if not ctx.raw_input:
            return CapabilityResult(
                candidates=(),
                diagnostics=(
                    Diagnostic(
                        code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                        severity=DiagnosticSeverity.ERROR,
                        message="xpath_extraction: raw_input is empty",
                        context={"field_path": ctx.field_path, "xpath": xpath},
                    ),
                ),
            )

        namespaces_obj = ctx.config.get("namespaces", {})
        if not isinstance(namespaces_obj, dict):
            return CapabilityResult(
                candidates=(),
                diagnostics=(
                    Diagnostic(
                        code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                        severity=DiagnosticSeverity.ERROR,
                        message=(
                            "xpath_extraction: config['namespaces'] must be a dict, "
                            f"got {type(namespaces_obj).__name__}"
                        ),
                        context={"field_path": ctx.field_path, "xpath": xpath},
                    ),
                ),
            )
        namespaces: dict[str, str] = dict(namespaces_obj)

        unsupported_msg = self._check_unsupported(xpath)
        if unsupported_msg is not None:
            return CapabilityResult(
                candidates=(),
                diagnostics=(
                    Diagnostic(
                        code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                        severity=DiagnosticSeverity.ERROR,
                        message=f"xpath_extraction: {unsupported_msg}",
                        context={"field_path": ctx.field_path, "xpath": xpath},
                    ),
                ),
            )

        undeclared_msg = self._check_undeclared_prefixes(xpath, namespaces)
        if undeclared_msg is not None:
            return CapabilityResult(
                candidates=(),
                diagnostics=(
                    Diagnostic(
                        code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                        severity=DiagnosticSeverity.ERROR,
                        message=f"xpath_extraction: {undeclared_msg}",
                        context={
                            "field_path": ctx.field_path,
                            "xpath": xpath,
                            "namespaces": namespaces,
                        },
                    ),
                ),
            )

        try:
            # ``_fromstring`` is selected at module import time by the
            # feature-detect block above. When ``defusedxml`` is installed
            # (the ``xml-secure`` extra), this call is hardened against
            # entity-expansion attacks (billion laughs, DTD retrieval).
            # When ``defusedxml`` is not installed, the call falls back to
            # the stdlib parser; the ``# nosec B314`` below acknowledges
            # that the unhardened path is the residual attack surface
            # (see ADR-0013 for the full rationale).
            root = _fromstring(ctx.raw_input)  # nosec B314
        except _XML_PARSE_ERRORS as exc:
            # ``_XML_PARSE_ERRORS`` is ``(ParseError, DefusedXmlException)``
            # when hardened, or ``(ParseError,)`` otherwise. ``ParseError``
            # exposes ``.position``; ``DefusedXmlException`` does not, so
            # we fall back to ``None`` for hardened-rejection paths.
            position = getattr(exc, "position", None)
            return CapabilityResult(
                candidates=(),
                diagnostics=(
                    Diagnostic(
                        code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                        severity=DiagnosticSeverity.ERROR,
                        message=f"xpath_extraction: input is not valid XML: {exc}",
                        context={
                            "field_path": ctx.field_path,
                            "xpath": xpath,
                            "position": position,
                        },
                    ),
                ),
            )

        try:
            # ElementTree's findall expects paths relative to the root
            # element (which is what ET.fromstring returns). Strip the
            # leading "/<root_tag>" so the user can pass an absolute
            # xpath like ``/root/item`` and it resolves correctly.
            # If the user's path does not start with the document
            # root, we fall through to PATTERN_NO_MATCH below.
            relative_xpath = xpath
            root_tag = root.tag
            root_matched = False
            if root_tag is not None and xpath.startswith("/"):
                first_segment = xpath.split("/", 2)[1]
                if first_segment:
                    root_local = root_tag.split("}", 1)[-1] if "}" in root_tag else root_tag
                    if "}" in first_segment:
                        tag_local = first_segment.split("}", 1)[-1]
                    else:
                        tag_local = first_segment
                    if tag_local == root_local:
                        relative_xpath = xpath[len(first_segment) + 2 :]
                        root_matched = True
            if not root_matched and xpath.startswith("/"):
                # The xpath references a different root than the document.
                # ElementTree will raise ``SyntaxError``; convert that to
                # PATTERN_NO_MATCH at the call site below.
                elements: list[_stdlib_ET.Element] = []
            else:
                elements = root.findall(relative_xpath, namespaces)
        except (_stdlib_ET.ParseError, SyntaxError) as exc:
            return CapabilityResult(
                candidates=(),
                diagnostics=(
                    Diagnostic(
                        code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                        severity=DiagnosticSeverity.ERROR,
                        message=(f"xpath_extraction: xpath failed to evaluate: {exc}"),
                        context={"field_path": ctx.field_path, "xpath": xpath},
                    ),
                ),
            )

        if not elements:
            return CapabilityResult(
                candidates=(),
                diagnostics=(
                    Diagnostic(
                        code=DiagnosticCode.PATTERN_NO_MATCH,
                        severity=DiagnosticSeverity.INFO,
                        message=f"xpath_extraction: xpath {xpath!r} matched no elements",
                        context={"field_path": ctx.field_path, "xpath": xpath},
                    ),
                ),
            )

        candidates: list[Candidate] = []
        evidence: list[EvidenceRef] = []
        for index, element in enumerate(elements):
            # Prefer the element's text. Empty string for self-closing elements
            # (e.g. ``<item id="b"/>``) is a valid match — the caller can
            # decide via the context how to handle it.
            value: str = element.text or ""
            ev = EvidenceRef(
                capability_id="xpath_extraction",
                capability_version="1.0",
                field_path=ctx.field_path,
                context={
                    "xpath": xpath,
                    "element_index": index,
                    "tag": element.tag,
                    "namespaces": dict(namespaces),
                },
            )
            evidence.append(ev)
            candidates.append(Candidate(value=value, evidence_refs=(ev,)))

        return CapabilityResult(
            candidates=tuple(candidates),
            evidence=tuple(evidence),
        )
