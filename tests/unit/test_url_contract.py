import pytest

# Mandate laws covered by this file:
#   Law 5  (Contract declares *what*, not *how*): the URL contract exposes only
#           policy fields (scheme_allow, strip_userinfo, whatwg, ...), never an
#           algorithm.
#   Law 12 (Replay): the contract carries a version_field consumed by replay; a
#           contract without it cannot round-trip through parse_contract.
from paxman._capabilities.url.contract import URL, _build_url
from paxman._errors import ContractError


def test_factory_defaults():
    c = URL()
    assert c.scheme_allow is None
    assert c.strip_userinfo is False
    assert c.strip_fragment is True
    assert c.sort_query is False
    assert c.whatwg is False
    assert c.kind == "canonical_url"
    assert c.version == 1
    assert c.version_field == 1


def test_factory_explicit():
    c = URL(scheme_allow=("http", "https"), strip_fragment=False, whatwg=True)
    assert c.scheme_allow == ("http", "https")
    assert c.strip_fragment is False
    assert c.whatwg is True


def test_as_dict_roundtrip():
    c = URL(scheme_allow=("https",))
    d = c.as_dict()
    assert d["kind"] == "canonical_url"
    assert d["scheme_allow"] == ["https"]
    assert d["strip_fragment"] is True


def test_build_url_allowlist_validation():
    with pytest.raises(ContractError):
        _build_url({"kind": "canonical_url", "scheme_allow": ["http", 123]})
    with pytest.raises(ContractError):
        _build_url({"kind": "canonical_url", "scheme_allow": "http"})


def test_build_url_bool_validation():
    with pytest.raises(ContractError):
        _build_url({"kind": "canonical_url", "strip_fragment": "yes"})


def test_build_url_default_missing_allow():
    c = _build_url({"kind": "canonical_url"})
    assert c.scheme_allow is None
    assert c.strip_fragment is True
