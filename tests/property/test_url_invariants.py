import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from paxman import canonicalize, replay
from paxman._capabilities.url.contract import URL

_valid = st.sampled_from(
    [
        "https://example.com/a",
        "http://example.com:80/b",
        "https://Example.COM/./x/../y?z=1",
        "HTTP://x.com",
    ]
)


@settings(max_examples=50, derandomize=True)
@given(_valid)
@pytest.mark.property
def test_replay_byte_equal(uri):
    contract = URL()
    art = canonicalize(uri, contract)
    rehydrated = replay(art, contract)
    assert rehydrated == art
    assert rehydrated.canonical_bytes() == art.canonical_bytes()


@settings(max_examples=50, derandomize=True)
@given(_valid)
@pytest.mark.property
def test_idempotence(uri):
    contract = URL()
    once = canonicalize(uri, contract)
    twice = canonicalize(once.value, contract)
    assert twice.value == once.value


def test_no_silent_ambiguity_among_builtins():
    from paxman._capabilities.url.canonicalizer import URLCapability

    cap = URLCapability()
    assert cap.can_handle(URL(), "https://x.com") is True


def test_whatwg_variant_idempotent():
    contract = URL(whatwg=True)
    art = canonicalize("http://example.com./", contract)
    rehydrated = replay(art, contract)
    assert art.value == "http://example.com/"
    assert rehydrated == art
    assert rehydrated.canonical_bytes() == art.canonical_bytes()
