from paxman._capabilities.url.canonicalizer import URLCapability
from paxman._capabilities.url.contract import URL, CanonicalURLContract
from paxman._core.status import Status


def _canon(value, **kw):
    cap = URLCapability()
    return cap.canonicalize(value, URL(**kw))


def test_can_handle():
    cap = URLCapability()
    assert cap.can_handle(URL(), "https://x.com") is True
    assert cap.can_handle(CanonicalURLContract(), 123) is False
    assert cap.can_handle("not a contract", "https://x.com") is False


def test_already_normal():
    r = _canon("https://example.com/b")
    assert r.status is Status.CANONICALIZED
    assert r.value == "https://example.com/b"


def test_default_normalizations():
    r = _canon("HTTP://Example.COM:80/./A/../b?x=1")
    assert r.status is Status.CANONICALIZED
    assert r.value == "http://example.com/b?x=1"


def test_fragment_preserved_when_opt_out():
    r = _canon("https://example.com/a#frag", strip_fragment=False)
    assert r.value == "https://example.com/a#frag"


def test_userinfo_retained_by_default():
    r = _canon("https://user:pass@example.com/")
    assert r.value == "https://user:pass@example.com/"


def test_userinfo_stripped_when_opt_in():
    r = _canon("https://user:pass@example.com/", strip_userinfo=True)
    assert r.value == "https://example.com/"


def test_non_default_port_kept():
    r = _canon("http://example.com:8080/")
    assert r.value == "http://example.com:8080/"


def test_decode_unreserved_pct():
    r = _canon("https://example.com/%7Epath")
    assert r.value == "https://example.com/~path"
    r2 = _canon("https://example.com/%2F")
    assert r2.value == "https://example.com/%2F"


def test_scheme_allow_miss_is_unsupported():
    r = _canon("http://example.com/", scheme_allow=("https",))
    assert r.status is Status.UNSUPPORTED


def test_whatwg_off_strict():
    r = _canon("http://example.com./")
    assert r.value == "http://example.com./"


def test_whatwg_on_trailing_dot():
    r = _canon("http://example.com./", whatwg=True)
    assert r.value == "http://example.com/"


def test_unrecognized_format():
    r = _canon("   ")
    assert r.status is Status.INVALID


def test_non_string_value():
    cap = URLCapability()
    r = cap.canonicalize(123, URL())
    assert r.status is Status.INVALID


def test_scheme_relative_bad_authority_is_invalid():
    # A scheme-relative value (//) whose authority has a non-numeric port
    # must be validated and rejected as INVALID, not silently canonicalized.
    r = _canon("//example.com:xyz/path")
    assert r.status is Status.INVALID


def test_scheme_relative_valid_is_canonicalized():
    r = _canon("//example.com/path")
    assert r.status is Status.CANONICALIZED
    assert r.value == "//example.com/path"
