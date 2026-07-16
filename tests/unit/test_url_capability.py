from paxman import canonicalize, replay
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


def test_default_canonicalizations():
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


def test_no_silent_ambiguity_among_builtins():
    cap = URLCapability()
    assert cap.can_handle(URL(), "https://x.com") is True


def test_whatwg_variant_idempotent():
    contract = URL(whatwg=True)
    art = canonicalize("http://example.com./", contract)
    assert art.value == "http://example.com/"
    rehydrated = replay(art, contract)
    assert rehydrated == art
    assert rehydrated.canonical_bytes() == art.canonical_bytes()


def test_dot_segment_preserves_empty_and_trailing():
    # RFC 3986 §5.2.4 regression cases called out in review.
    assert _canon("http://h//a").value == "http://h//a"
    assert _canon("http://h/a/").value == "http://h/a/"
    assert _canon("http://h/a/.").value == "http://h/a/"
    assert _canon("http://h/a/../").value == "http://h/"


def test_empty_port_is_rejected():
    # http://host:/ carries an explicitly empty port; it must not be elided
    # into a valid authority but rejected as INVALID.
    r = _canon("http://host:/")
    assert r.status is Status.INVALID


def test_digit_leading_registered_name_accepted():
    # 3com.com is a valid registered name (RFC 3986 §3.2.2) and must not be
    # rejected merely for a digit-leading label.
    r = _canon("http://3com.com/")
    assert r.status is Status.CANONICALIZED
    assert r.value == "http://3com.com/"


def test_out_of_range_port_rejected():
    r = _canon("http://example.com:99999/")
    assert r.status is Status.INVALID


def test_malformed_ipv6_rejected():
    r = _canon("http://[::]/")
    assert r.status is Status.CANONICALIZED
    r2 = _canon("http://[gggg::1]/")
    assert r2.status is Status.INVALID
