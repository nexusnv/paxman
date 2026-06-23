"""Unit tests for :mod:`paxman.capabilities.v1.text_extraction`."""

from __future__ import annotations

import pytest

from paxman.capabilities.base import CapabilityContext
from paxman.capabilities.result import DiagnosticCode
from paxman.capabilities.spec import CapabilitySpec, CapabilityTier, CostHint
from paxman.capabilities.v1.text_extraction import (
    StubTextExtractionProvider,
    TextExtractionCapability,
    TextExtractionProvider,
)

pytestmark = pytest.mark.unit


def _ctx(
    raw: bytes = b"",
    field_path: str = "text",
    config: dict | None = None,
) -> CapabilityContext:
    return CapabilityContext(
        raw_input=raw,
        field_path=field_path,
        field_type_name="STRING",
        config=config or {},
    )


# --- spec -----------------------------------------------------------------


def test_spec() -> None:
    cap = TextExtractionCapability()
    spec = cap.spec
    assert isinstance(spec, CapabilitySpec)
    assert spec.id == "text_extraction"
    assert spec.version == "1.0"
    assert spec.tier is CapabilityTier.LOCAL_DETERMINISTIC
    assert spec.deterministic is True
    assert spec.cost_estimate == CostHint(tokens=0, ms=5, usd=0.0)


# --- provider: text/plain ------------------------------------------------


def test_text_plain_returns_raw_text() -> None:
    provider = StubTextExtractionProvider()
    assert provider.extract(b"Hello, World!", "text/plain") == "Hello, World!"


def test_text_plain_with_replacement() -> None:
    """Invalid UTF-8 is replaced (U+FFFD)."""
    provider = StubTextExtractionProvider()
    out = provider.extract(b"\xff\xfe\x00", "text/plain")
    assert "\ufffd" in out


# --- provider: text/html -------------------------------------------------


def test_text_html_strips_tags() -> None:
    provider = StubTextExtractionProvider()
    html = b"<html><body><h1>ACME Corp</h1><p>Invoice</p></body></html>"
    out = provider.extract(html, "text/html")
    assert "ACME Corp" in out
    assert "Invoice" in out
    assert "<h1>" not in out


def test_text_html_decodes_entities() -> None:
    provider = StubTextExtractionProvider()
    html = b"<p>AT&amp;T</p>"
    out = provider.extract(html, "text/html")
    assert "AT&T" in out


# --- provider: unsupported content type ---------------------------------


def test_unsupported_content_type_raises() -> None:
    """A non-text content type raises CapabilityError."""
    from paxman.errors import CapabilityError

    provider = StubTextExtractionProvider()
    with pytest.raises(CapabilityError) as exc_info:
        provider.extract(b"data", "image/png")
    assert exc_info.value.error_code == "UNSUPPORTED_CONTENT_TYPE"


# --- capability ---------------------------------------------------------


def test_capability_uses_default_provider_for_text_plain() -> None:
    """Without a provider config, the default stub is used."""
    cap = TextExtractionCapability()
    result = cap.invoke(_ctx(b"Hello", config={"content_type": "text/plain"}))
    assert result.candidates[0].value == "Hello"
    assert result.diagnostics == ()


def test_capability_uses_default_provider_for_text_html() -> None:
    cap = TextExtractionCapability()
    result = cap.invoke(_ctx(b"<p>ACME</p>", config={"content_type": "text/html"}))
    assert result.candidates[0].value == "ACME"


def test_capability_uses_custom_provider() -> None:
    """A custom provider is used when supplied via config."""

    class _CountProvider:
        def extract(self, raw_input: bytes, content_type: str) -> str:
            return f"len={len(raw_input)}"

    cap = TextExtractionCapability()
    result = cap.invoke(
        _ctx(b"abc", config={"provider": _CountProvider(), "content_type": "text/plain"})
    )
    assert result.candidates[0].value == "len=3"


def test_capability_rejects_provider_without_extract() -> None:
    """A non-provider config returns an error diagnostic."""

    class _NotAProvider:
        pass

    cap = TextExtractionCapability()
    result = cap.invoke(
        _ctx(b"x", config={"provider": _NotAProvider(), "content_type": "text/plain"})
    )
    assert result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED


def test_capability_evidence_has_full_span() -> None:
    cap = TextExtractionCapability()
    result = cap.invoke(_ctx(b"hello world", config={"content_type": "text/plain"}))
    ev = result.candidates[0].evidence_refs[0]
    assert ev.capability_id == "text_extraction"
    assert ev.capability_version == "1.0"
    assert ev.span == (0, 11)
    assert ev.context == {"content_type": "text/plain"}


# --- provider SPI: TextExtractionProvider is a Protocol ---------------


def test_text_extraction_provider_is_protocol() -> None:
    """TextExtractionProvider is a typing.Protocol; custom providers
    that implement ``extract(raw_input, content_type) -> str`` are accepted
    structurally (PEP 544)."""
    assert hasattr(TextExtractionProvider, "extract")
