"""Unit tests for :mod:`paxman.capabilities.v1.xpath_extraction`.

V1 deterministic capability that resolves a documented subset of
XPath against the raw input parsed as XML.
"""

from __future__ import annotations

import pytest

from paxman.capabilities.base import CapabilityContext
from paxman.capabilities.result import DiagnosticCode, DiagnosticSeverity
from paxman.capabilities.spec import CapabilitySpec, CapabilityTier, CostHint
from paxman.capabilities.v1.xpath_extraction import XPathExtractionCapability

pytestmark = pytest.mark.unit


def _ctx(raw: bytes = b"", xpath: str | None = None, **extra: object) -> CapabilityContext:
    cfg: dict = {}
    if xpath is not None:
        cfg["xpath"] = xpath
    cfg.update(extra)
    return CapabilityContext(
        raw_input=raw,
        field_path="supplier_name",
        field_type_name="STRING",
        config=cfg,
    )


# --- spec -----------------------------------------------------------------


def test_spec() -> None:
    """The spec is xpath_extraction@1.0, LOCAL_DETERMINISTIC, free."""
    cap = XPathExtractionCapability()
    spec = cap.spec
    assert isinstance(spec, CapabilitySpec)
    assert spec.id == "xpath_extraction"
    assert spec.version == "1.0"
    assert spec.tier is CapabilityTier.LOCAL_DETERMINISTIC
    assert spec.deterministic is True
    assert spec.cost_estimate == CostHint(tokens=0, ms=1, usd=0.0)


# --- happy path -----------------------------------------------------------


def test_resolves_absolute_path() -> None:
    """An absolute path returns the matching element's text."""
    cap = XPathExtractionCapability()
    raw = b"<root><supplier>ACME</supplier></root>"
    result = cap.invoke(_ctx(raw, xpath="/root/supplier"))
    assert [c.value for c in result.candidates] == ["ACME"]
    ev = result.candidates[0].evidence_refs[0]
    assert ev.capability_id == "xpath_extraction"
    assert ev.context["xpath"] == "/root/supplier"
    assert ev.context["element_index"] == 0


def test_resolves_attribute_predicate() -> None:
    """An [@attr="value"] predicate filters by attribute."""
    cap = XPathExtractionCapability()
    raw = b'<root><item id="a"/><item id="b"/></root>'
    result = cap.invoke(_ctx(raw, xpath='/root/item[@id="b"]'))
    assert len(result.candidates) == 1
    # The match is at position 0 in the result list (it's the only match).
    # To verify it picked the correct *element* (id="b"), check the context.
    ev = result.candidates[0].evidence_refs[0]
    assert ev.context["xpath"] == '/root/item[@id="b"]'
    # And verify the other match (id="a") is NOT in the candidates.
    assert "a" not in [c.value for c in result.candidates]


def test_predicate_excludes_non_matching() -> None:
    """A predicate that doesn't match any element returns PATTERN_NO_MATCH."""
    cap = XPathExtractionCapability()
    raw = b'<root><item id="a"/><item id="b"/></root>'
    result = cap.invoke(_ctx(raw, xpath='/root/item[@id="c"]'))
    assert result.candidates == ()
    assert result.diagnostics[0].code is DiagnosticCode.PATTERN_NO_MATCH


def test_resolves_with_namespace() -> None:
    """Namespace prefixes are honored when declared in config['namespaces']."""
    cap = XPathExtractionCapability()
    raw = b'<root xmlns:inv="http://example.com/invoice"><inv:supplier>ACME</inv:supplier></root>'
    result = cap.invoke(
        _ctx(
            raw,
            xpath="/root/inv:supplier",
            namespaces={"inv": "http://example.com/invoice"},
        )
    )
    assert [c.value for c in result.candidates] == ["ACME"]


def test_unicode_input() -> None:
    """UTF-8 encoded XML input is supported."""
    cap = XPathExtractionCapability()
    raw = "<root><name>日本語 🎉</name></root>".encode()
    result = cap.invoke(_ctx(raw, xpath="/root/name"))
    assert [c.value for c in result.candidates] == ["日本語 🎉"]


def test_multiple_matches() -> None:
    """Multiple matches produce multiple candidates in document order."""
    cap = XPathExtractionCapability()
    raw = b"<root><item>a</item><item>b</item><item>c</item></root>"
    result = cap.invoke(_ctx(raw, xpath="/root/item"))
    assert [c.value for c in result.candidates] == ["a", "b", "c"]


# --- failure modes --------------------------------------------------------


def test_missing_xpath_in_config() -> None:
    """Missing config['xpath'] returns an error diagnostic."""
    cap = XPathExtractionCapability()
    result = cap.invoke(_ctx(b"<root/>"))
    assert result.candidates == ()
    d = result.diagnostics[0]
    assert d.code is DiagnosticCode.CAPABILITY_INVOKE_FAILED
    assert "xpath" in d.message


def test_empty_xpath() -> None:
    """Empty config['xpath'] returns an error diagnostic."""
    cap = XPathExtractionCapability()
    result = cap.invoke(_ctx(b"<root/>", xpath=""))
    assert result.candidates == ()
    assert result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED


def test_invalid_xml() -> None:
    """Malformed input returns an error diagnostic (not an exception)."""
    cap = XPathExtractionCapability()
    result = cap.invoke(_ctx(b"<root><unclosed>", xpath="/root"))
    assert result.candidates == ()
    d = result.diagnostics[0]
    assert d.code is DiagnosticCode.CAPABILITY_INVOKE_FAILED
    assert "xml" in d.message.lower()


def test_path_not_found() -> None:
    """A valid XML but no matching elements returns a PATTERN_NO_MATCH."""
    cap = XPathExtractionCapability()
    result = cap.invoke(_ctx(b"<root/>", xpath="/root/missing"))
    assert result.candidates == ()
    d = result.diagnostics[0]
    assert d.code is DiagnosticCode.PATTERN_NO_MATCH
    assert d.severity is DiagnosticSeverity.INFO


def test_unsupported_xpath_function() -> None:
    """XPath function calls are outside the documented V1 subset."""
    cap = XPathExtractionCapability()
    raw = b"<root><item>a</item></root>"
    result = cap.invoke(_ctx(raw, xpath="/root/item[contains(text(),'a')]"))
    assert result.candidates == ()
    d = result.diagnostics[0]
    assert d.code is DiagnosticCode.CAPABILITY_INVOKE_FAILED
    assert "unsupported" in d.message.lower()


def test_unsupported_text_node() -> None:
    """The text() node test is outside the documented V1 subset."""
    cap = XPathExtractionCapability()
    raw = b"<root><item>a</item></root>"
    result = cap.invoke(_ctx(raw, xpath="/root/item/text()"))
    assert result.candidates == ()
    assert result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED


def test_undeclared_namespace_prefix() -> None:
    """A namespace prefix not in config['namespaces'] is an error."""
    cap = XPathExtractionCapability()
    raw = b'<root xmlns:inv="http://example.com/invoice"><inv:supplier>ACME</inv:supplier></root>'
    result = cap.invoke(_ctx(raw, xpath="/root/inv:supplier"))
    assert result.candidates == ()
    d = result.diagnostics[0]
    assert d.code is DiagnosticCode.CAPABILITY_INVOKE_FAILED
    assert "namespace" in d.message.lower() or "prefix" in d.message.lower()


def test_path_root_mismatch() -> None:
    """An xpath that does not start with the actual document root returns PATTERN_NO_MATCH."""
    cap = XPathExtractionCapability()
    raw = b"<other><item>a</item></other>"
    result = cap.invoke(_ctx(raw, xpath="/root/item"))
    assert result.candidates == ()
    assert result.diagnostics[0].code is DiagnosticCode.PATTERN_NO_MATCH


def test_namespaces_wrong_type() -> None:
    """config['namespaces'] must be a dict, not a list or other type."""
    cap = XPathExtractionCapability()
    raw = b"<root><item>a</item></root>"
    result = cap.invoke(_ctx(raw, xpath="/root/item", namespaces=["inv"]))  # type: ignore[arg-type]
    assert result.candidates == ()
    d = result.diagnostics[0]
    assert d.code is DiagnosticCode.CAPABILITY_INVOKE_FAILED
    assert "namespaces" in d.message


def test_empty_input() -> None:
    """Empty raw_input returns an error diagnostic."""
    cap = XPathExtractionCapability()
    result = cap.invoke(_ctx(b"", xpath="/root"))
    assert result.candidates == ()
    assert result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED


# --- determinism ----------------------------------------------------------


@pytest.mark.deterministic
def test_determinism() -> None:
    """Same input + same xpath = same candidates, byte-equal."""
    cap = XPathExtractionCapability()
    ctx = _ctx(b"<root><item>a</item><item>b</item></root>", xpath="/root/item")
    r1 = cap.invoke(ctx)
    r2 = cap.invoke(ctx)
    assert [c.value for c in r1.candidates] == [c.value for c in r2.candidates]
    assert [c.evidence_refs[0].context for c in r1.candidates] == [
        c.evidence_refs[0].context for c in r2.candidates
    ]
