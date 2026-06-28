"""``text_extraction`` V1 capability — pull text from raw input.

V1 supports ``text/plain`` and ``text/html`` only (PDF
and image OCR are V2). The capability uses a
**provider SPI** so a real OCR / HTML parser can be plugged in
without modifying the capability; in V1 the provider is a stub.

Provider SPI
------------

The provider is a callable / object with one method:

```python
class TextExtractionProvider(Protocol):
    def extract(self, raw_input: bytes, content_type: str) -> str: ...
```

The capability takes a provider from :attr:`CapabilityContext.config`
(``ctx.config["provider"]``). The default provider is
:class:`StubTextExtractionProvider`, which:

- returns ``raw_input`` decoded as UTF-8 for ``text/plain``;
- uses :mod:`html.parser` to strip HTML tags for ``text/html``;
- raises :class:`~paxman.errors.CapabilityError` for unsupported
  content types.

V1 surface:

- ``input_types`` = ``("STRING",)`` (the input is the raw text).
- ``output_type`` = ``"STRING"`` (the extracted text).
- ``deterministic`` = ``True`` for the default provider.
- ``cost_estimate`` = ``(tokens=0, ms=5, usd=0.0)`` (per
  ``docs/specs/capability-cost-model.md`` §3).
"""

from __future__ import annotations

import html.parser
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
from paxman.errors import CapabilityError

__all__ = [
    "StubTextExtractionProvider",
    "TextExtractionCapability",
    "TextExtractionProvider",
]


class TextExtractionProvider(typing.Protocol):
    """SPI: a text-extraction backend.

    A :class:`TextExtractionProvider` turns raw bytes into a single
    string. V1 ships a :class:`StubTextExtractionProvider`; future
    providers (e.g., ``pytesseract`` for OCR, ``beautifulsoup4`` for
    richer HTML parsing) implement the same Protocol.

    The provider is **stateless and side-effect-free** in V1. It
    does not read the canonical contract or the :class:`InputProfile`
    — it only sees the raw bytes and the content type.
    """

    def extract(self, raw_input: bytes, content_type: str) -> str:
        """Extract text from *raw_input*.

        Args:
            raw_input: The raw bytes (UTF-8 encoded, replacement
                applied at the API layer).
            content_type: The content type (e.g., ``"text/plain"``,
                ``"text/html"``). V1 only supports ``text/*``.

        Returns:
            The extracted text. For ``text/plain``, the decoded text
            itself; for ``text/html``, the HTML with tags stripped.

        Raises:
            paxman.errors.CapabilityError: If the content type is
                unsupported or extraction fails.
        """
        ...


class _HtmlStripper(html.parser.HTMLParser):
    """Strip HTML tags and decode entities. Internal helper."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        """Capture text between tags."""
        self._chunks.append(data)

    @property
    def text(self) -> str:
        """Return concatenated text content."""
        return "".join(self._chunks)


class StubTextExtractionProvider:
    """V1 default :class:`TextExtractionProvider`.

    Behavior:

    - ``text/plain`` → ``raw_input`` decoded as UTF-8 (``errors="replace"``).
    - ``text/html`` → HTML parsed with :mod:`html.parser`; tags
      stripped, character references decoded, text concatenated.
    - Anything else → raises :class:`~paxman.errors.CapabilityError`.

    The stub is intentionally minimal: it does not preserve
    formatting, line numbers, or anchor positions. Real providers
    (V2) may emit richer output.
    """

    def extract(self, raw_input: bytes, content_type: str) -> str:
        """Extract text from *raw_input*.

        Args:
            raw_input: The raw bytes.
            content_type: The content type (``"text/plain"`` or
                ``"text/html"`` for V1).

        Returns:
            The extracted text.

        Raises:
            paxman.errors.CapabilityError: If the content type is
                unsupported.
        """
        ct = content_type.lower().strip()
        if ct in ("text/plain", "text"):
            return raw_input.decode("utf-8", errors="replace")
        if ct in ("text/html", "html"):
            text = raw_input.decode("utf-8", errors="replace")
            stripper = _HtmlStripper()
            stripper.feed(text)
            stripper.close()
            return stripper.text
        raise CapabilityError(
            f"text_extraction: unsupported content type {content_type!r} "
            f"(V1 supports text/plain and text/html)",
            error_code="UNSUPPORTED_CONTENT_TYPE",
            context={"content_type": content_type},
        )


#: The default :class:`TextExtractionProvider` used when no provider
#: is supplied via :attr:`CapabilityContext.config`.
_DEFAULT_PROVIDER: typing.Final[TextExtractionProvider] = StubTextExtractionProvider()


class TextExtractionCapability:
    """V1 ``text_extraction`` capability.

    Extracts text from raw input using a :class:`TextExtractionProvider`.
    The provider is supplied via :attr:`CapabilityContext.config`
    (``ctx.config["provider"]``). The content type is supplied via
    ``ctx.config["content_type"]`` (defaults to
    ``ctx.input_profile_type``).

    The capability produces **one candidate** containing the
    extracted text. If the provider raises
    :class:`~paxman.errors.CapabilityError`, the capability returns
    an empty :class:`CapabilityResult` with a diagnostic carrying
    the error message.

    Examples:
        >>> cap = TextExtractionCapability()
        >>> ctx = CapabilityContext(
        ...     raw_input=b"<p>ACME Corp</p>",
        ...     field_path="supplier_name",
        ...     field_type_name="STRING",
        ...     config={"content_type": "text/html"},
        ... )
        >>> result = cap.invoke(ctx)
        >>> result.candidates[0].value
        'ACME Corp'
    """

    @property
    def spec(self) -> CapabilitySpec:
        """The :class:`CapabilitySpec` for ``text_extraction@1.0``."""
        return _TEXT_EXTRACTION_SPEC

    def invoke(self, ctx: CapabilityContext) -> CapabilityResult:
        """Run text extraction.

        Args:
            ctx: The :class:`CapabilityContext`. ``ctx.config`` may
                contain:

                - ``"provider"``: a :class:`TextExtractionProvider`.
                  Defaults to :data:`_DEFAULT_PROVIDER`.
                - ``"content_type"``: a ``str``. Defaults to
                  ``ctx.input_profile_type``.

        Returns:
            A :class:`CapabilityResult` with one :class:`Candidate`
            containing the extracted text, plus an :class:`EvidenceRef`
            with the full input span.
        """
        provider = ctx.config.get("provider", _DEFAULT_PROVIDER)
        # Check both that the attribute exists AND that it is
        # callable. ``hasattr`` alone accepts a property or any
        # other descriptor; if we passed that to ``provider.extract(...)``
        # Python would raise ``TypeError: 'X' object is not
        # callable`` at the call site. Checking ``callable`` up
        # front lets us return a structured diagnostic instead.
        extract = getattr(provider, "extract", None)
        if extract is None or not callable(extract):
            return CapabilityResult(
                candidates=(),
                diagnostics=(
                    Diagnostic(
                        code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                        severity=DiagnosticSeverity.ERROR,
                        message=(
                            "text_extraction: config['provider'] does not implement extract()"
                        ),
                        context={"field_path": ctx.field_path},
                    ),
                ),
            )
        content_type = ctx.config.get("content_type", ctx.input_profile_type)
        if not isinstance(content_type, str) or not content_type:
            content_type = "text"

        try:
            text = extract(ctx.raw_input, content_type)
        except CapabilityError as e:
            return CapabilityResult(
                candidates=(),
                diagnostics=(
                    Diagnostic(
                        code=DiagnosticCode.INPUT_NOT_SUPPORTED
                        if "unsupported" in str(e).lower()
                        else DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                        severity=DiagnosticSeverity.ERROR,
                        message=str(e),
                        context=e.context,
                    ),
                ),
            )

        evidence = (
            EvidenceRef(
                capability_id="text_extraction",
                capability_version="1.0",
                field_path=ctx.field_path,
                span=(0, len(ctx.raw_input)),
                context={"content_type": content_type},
            ),
        )
        return CapabilityResult(
            candidates=(Candidate(value=text, evidence_refs=evidence),),
            evidence=evidence,
        )


#: Singleton spec for ``text_extraction@1.0``. Reused across instances.
_TEXT_EXTRACTION_SPEC: typing.Final[CapabilitySpec] = CapabilitySpec(
    id="text_extraction",
    version="1.0",
    input_types=("STRING",),
    output_type="STRING",
    cost_estimate=CostHint(tokens=0, ms=5, usd=0.0),
    tier=CapabilityTier.LOCAL_DETERMINISTIC,
    deterministic=True,
    required_providers=(),
)
