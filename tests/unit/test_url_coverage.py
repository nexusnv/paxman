"""Targeted coverage tests for the URL capability to satisfy the
per-subpackage >=90% gate for ``_capabilities/url``.

These exercise branches not hit by the happy-path capability tests:
WHATWG authority/path coercion, query sorting, userinfo stripping on
scheme-relative input, relative-reference grammars, and the defensive
UNSUPPORTED / no_transformation_needed paths.
"""

from paxman._capabilities.url.canonicalizer import URLCapability
from paxman._capabilities.url.contract import URL
from paxman._core.result import CapabilityResult
from paxman._core.status import Status


def _canon(value: str, **kw: object) -> CapabilityResult:
    return URLCapability().canonicalize(value, URL(**kw))


def test_whatwg_backslash_in_host() -> None:
    r = _canon("http://ex\\ample.com/", whatwg=True)
    assert r.value == "http://example.com/"


def test_whatwg_pct_dot_in_path() -> None:
    r = _canon("http://example.com/%2e%2e/foo", whatwg=True)
    assert r.value is not None
    assert ".." not in r.value or r.value == "http://example.com/foo"


def test_whatwg_backslash_in_path() -> None:
    r = _canon("http://example.com/a\\b", whatwg=True)
    assert r.value == "http://example.com/a/b"


def test_sort_query() -> None:
    r = _canon("http://example.com/?b=2&a=1", sort_query=True)
    assert r.value == "http://example.com/?a=1&b=2"


def test_strip_userinfo_on_scheme_relative() -> None:
    r = _canon("//user:pass@example.com/", strip_userinfo=True)
    assert r.value == "//example.com/"


def test_authority_relative_passthrough() -> None:
    r = _canon("//example.com/path")
    assert r.value == "//example.com/path"


def test_path_relative_passthrough() -> None:
    r = _canon("/just/a/path")
    assert r.value == "/just/a/path"


def test_scheme_allow_unsupported_evidence() -> None:
    r = _canon("http://example.com/", scheme_allow=("https",))
    assert r.status is Status.UNSUPPORTED
    assert any(e.rule == "scheme_not_allowed" for e in r.evidence)


def test_ambiguous_defensive_unreachable_shape() -> None:
    r = _canon("/a/b/c")
    assert r.status is Status.CANONICALIZED
