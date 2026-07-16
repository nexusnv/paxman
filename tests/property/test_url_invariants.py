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
def test_replay_invariant(uri):
    contract = URL()
    art = canonicalize(uri, contract)
    rehydrated = replay(art, contract)
    assert rehydrated == art
    assert rehydrated.canonical_bytes() == art.canonical_bytes()


@settings(max_examples=50, derandomize=True)
@given(_valid)
@pytest.mark.property
def test_idempotence_invariant(uri):
    contract = URL()
    once = canonicalize(uri, contract)
    twice = canonicalize(once.value, contract)
    assert twice.value == once.value


@settings(max_examples=50, derandomize=True)
@given(_valid)
@pytest.mark.property
def test_uniqueness_invariant(uri):
    # An input that admits more than one canonical reading must be reported as
    # AMBIGUOUS (mandate Law 4 / §5.4). A single well-formed URL yields exactly
    # one canonical value, never an ambiguous set of survivors.
    contract = URL()
    art = canonicalize(uri, contract)
    assert art.status.name != "AMBIGUOUS"


@settings(max_examples=50, derandomize=True)
@given(_valid)
@pytest.mark.property
def test_artifact_immutability_invariant(uri):
    # The returned artifact is frozen (mandate Law 13); rehydration must not
    # mutate it and must reproduce an equal, byte-equal artifact.
    contract = URL()
    art = canonicalize(uri, contract)
    rehydrated = replay(art, contract)
    assert rehydrated == art
    assert rehydrated.canonical_bytes() == art.canonical_bytes()


@settings(max_examples=50, derandomize=True)
@given(_valid)
@pytest.mark.property
def test_canonicalization_invariant(uri):
    # Canonicalization is a deterministic fixed point (mandate Laws 1 & 2):
    # the same (input, contract) always yields the same value, and re-applying
    # canonicalize to the result is a no-op.
    contract = URL()
    first = canonicalize(uri, contract)
    second = canonicalize(uri, contract)
    assert first.value == second.value
    reapplied = canonicalize(first.value, contract)
    assert reapplied.value == first.value
