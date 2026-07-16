"""Regression tests for IPv6 literal handling in the URL capability.

An IPv6 authority is enclosed in brackets (e.g. ``[2001:db8::1]``); the
colons INSIDE the brackets are address separators, not host:port
separators. The resolver must split host/port only on a colon OUTSIDE the
bracketed zone, otherwise ``int(port)`` crashes on ``"1]"``.
"""

from paxman._capabilities.url.canonicalizer import URLCapability
from paxman._capabilities.url.contract import URL
from paxman._core.result import CapabilityResult
from paxman._core.status import Status


def _canon(value: str, **kw: object) -> CapabilityResult:
    return URLCapability().canonicalize(value, URL(**kw))


def test_ipv6_loopback() -> None:
    r = _canon("http://[::1]/")
    assert r.status is Status.CANONICALIZED
    assert r.value == "http://[::1]/"


def test_ipv6_full_address() -> None:
    r = _canon("http://[2001:db8::1]/")
    assert r.status is Status.CANONICALIZED
    assert r.value == "http://[2001:db8::1]/"


def test_ipv6_with_explicit_port() -> None:
    r = _canon("http://[2001:db8::1]:8080/")
    assert r.status is Status.CANONICALIZED
    assert r.value == "http://[2001:db8::1]:8080/"


def test_ipv6_with_default_port_elided() -> None:
    r = _canon("http://[::1]:80/")
    assert r.status is Status.CANONICALIZED
    assert r.value == "http://[::1]/"


def test_ipv6_https_default_port_elided() -> None:
    r = _canon("https://[2001:db8::1]:443/")
    assert r.status is Status.CANONICALIZED
    assert r.value == "https://[2001:db8::1]/"


def test_ipv6_userinfo_kept_by_default() -> None:
    r = _canon("http://user@[2001:db8::1]/")
    assert r.status is Status.CANONICALIZED
    assert r.value == "http://user@[2001:db8::1]/"


def test_ipv6_idempotent() -> None:
    once = _canon("http://[2001:db8::1]:8080/")
    assert once.status is Status.CANONICALIZED
    twice = _canon(once.value)
    assert twice.value == once.value


def test_non_numeric_port_after_ipv6_does_not_crash() -> None:
    # Regression: a non-numeric port after a bracketed IPv6 literal must be
    # rejected (INVALID), not raise ValueError in the resolver.
    r = _canon("http://[::1]:xyz/")
    assert r.status is Status.INVALID


def test_non_numeric_port_after_host_does_not_crash() -> None:
    # Same class of crash for a regular host with a non-numeric port.
    r = _canon("http://example.com:abc/")
    assert r.status is Status.INVALID
