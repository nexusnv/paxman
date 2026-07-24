"""Property tests for output_format determinism across all capabilities.

Verifies Mandate Law 2 (Determinism) and Law 12 (Replay) as they relate to
the ``output_format`` policy field on every capability contract.

Three properties:
1. **Determinism** — ``canonicalize(x, contract)`` is deterministic: two calls
   with the same input and contract produce identical artifacts.
2. **Format idempotency** — ``replay(artifact, contract) == artifact`` for
   every artifact, regardless of output_format (Mandate Law 12).
3. **Format stability** — for multi-format capabilities (country, date),
   applying different output formats to the same input produces distinct but
   individually valid canonical forms.

Capability output_format types (from contract.py):
- email:     Literal["email"]         (single format)
- uuid:      Literal["hex"]           (single format)
- boolean:   Literal["truefalse"]     (single format)
- ip:        Literal["normalized"]    (single format)
- money:     Literal["iso4217"]       (single format)
- geolocation: Literal["decimal"]     (single format)
- url:       Literal["normalized"]    (single format)
- phone:     Literal["e164"]          (single format)
- country:   Literal["alpha2", "alpha3", "numeric"]  (3 formats)
- date:      Literal["iso", "compact"]                (2 formats)
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from paxman import (
    IP,
    URL,
    UUID,
    Boolean,
    Country,
    Date,
    Email,
    Geolocation,
    Money,
    Phone,
    canonicalize,
    replay,
)
from paxman._core.status import Status

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Email: well-formed lowercase addresses
_emails = st.from_regex(r"[a-z]{3,}@[a-z]{3,}\.[a-z]{2,}", fullmatch=True)

# UUID: RFC 4122 canonical lowercase hyphenated strings
_uuids = st.uuids().map(str)

# Boolean: representative tokens spanning all accepted forms
_boolean_tokens = st.sampled_from(
    [
        "true",
        "True",
        "TRUE",
        "false",
        "False",
        "FALSE",
        "yes",
        "Y",
        "no",
        "N",
        "1",
        "0",
        "on",
        "off",
        "enabled",
        "disabled",
    ]
)

# IP: valid IPv4 and IPv6 addresses
_ips = st.sampled_from(
    [
        "192.168.1.1",
        "10.0.0.1",
        "8.8.8.8",
        "127.0.0.1",
        "::1",
        "2001:db8::1",
        "fe80::1%eth0",
    ]
)

# Money: (input, currency) pairs — currency is REQUIRED (Law 3)
_money_pairs = st.sampled_from(
    [
        ("$12.50", "USD"),
        ("€100.00", "EUR"),
        ("£50.00", "GBP"),
        ("RM 50.00", "MYR"),
        ("¥1000", "JPY"),
        ("12.50 USD", "USD"),
        ("100 EUR", "EUR"),
    ]
)

# Geolocation: coordinate strings with explicit hemisphere letters (the
# default contract requires hemispheres, so only hemisphere-marked inputs
# canonicalize; unsigned pairs are AMBIGUOUS and that's fine for the
# determinism + replay properties).
_geolocations = st.sampled_from(
    [
        "40.7128N 74.006W",
        "35.6762N 139.6503E",
        "51.5074N 0.1278W",
        "33.8688S 151.2093E",
        "0.0N 0.0E",
    ]
)

# URL: valid URLs across scheme/case/path variations
_urls = st.sampled_from(
    [
        "https://example.com",
        "http://foo.bar/baz",
        "HTTPS://EXAMPLE.COM/path?q=1#frag",
        "http://example.com:8080/path",
    ]
)

# Phone: E.164 and national numbers (default country=US)
_phones = st.sampled_from(
    [
        "+12025551234",
        "+442071234567",
        "+81312345678",
        "+12125551234",
    ]
)

# Country: names, alpha-2, alpha-3, synonyms — covers multiple resolution
# paths through the country capability
_countries = st.sampled_from(
    [
        "US",
        "USA",
        "United States",
        "UK",
        "GBR",
        "Germany",
        "DE",
        "France",
        "FR",
        "Japan",
        "JP",
        "China",
        "CN",
        "Malaysia",
        "MY",
    ]
)

# Date: ISO date strings (YYYY-MM-DD, guaranteed to parse)
_dates = st.builds(
    lambda y, m, d: f"{y:04d}-{m:02d}-{d:02d}",
    st.integers(1970, 2999),
    st.integers(1, 12),
    st.integers(1, 28),
)


# ---------------------------------------------------------------------------
# 1. DETERMINISM — same (input, contract) → same artifact
#
# Mandate Law 2: canonicalize is a pure function of (input, contract,
# registered_capabilities, config, version). Calling it twice with the
# same inputs must produce byte-identical artifacts.
# ---------------------------------------------------------------------------


@pytest.mark.property
@settings(derandomize=True, max_examples=50, deadline=None)
@given(value=_emails)
def test_email_determinism(value: str) -> None:
    c = Email()
    first = canonicalize(value, c)
    second = canonicalize(value, c)
    assert first == second
    assert first.canonical_bytes() == second.canonical_bytes()


@pytest.mark.property
@settings(derandomize=True, max_examples=50, deadline=None)
@given(value=_uuids)
def test_uuid_determinism(value: str) -> None:
    c = UUID()
    first = canonicalize(value, c)
    second = canonicalize(value, c)
    assert first == second
    assert first.canonical_bytes() == second.canonical_bytes()


@pytest.mark.property
@settings(derandomize=True, max_examples=50, deadline=None)
@given(value=_boolean_tokens)
def test_boolean_determinism(value: str) -> None:
    c = Boolean()
    first = canonicalize(value, c)
    second = canonicalize(value, c)
    assert first == second
    assert first.canonical_bytes() == second.canonical_bytes()


@pytest.mark.property
@settings(derandomize=True, max_examples=50, deadline=None)
@given(value=_ips)
def test_ip_determinism(value: str) -> None:
    c = IP()
    first = canonicalize(value, c)
    second = canonicalize(value, c)
    assert first == second
    assert first.canonical_bytes() == second.canonical_bytes()


@pytest.mark.property
@settings(derandomize=True, max_examples=50, deadline=None)
@given(pair=_money_pairs)
def test_money_determinism(pair: tuple[str, str]) -> None:
    value, currency = pair
    c = Money(currency=currency)
    first = canonicalize(value, c)
    second = canonicalize(value, c)
    assert first == second
    assert first.canonical_bytes() == second.canonical_bytes()


@pytest.mark.property
@settings(derandomize=True, max_examples=50, deadline=None)
@given(value=_geolocations)
def test_geolocation_determinism(value: str) -> None:
    c = Geolocation()
    first = canonicalize(value, c)
    second = canonicalize(value, c)
    assert first == second
    assert first.canonical_bytes() == second.canonical_bytes()


@pytest.mark.property
@settings(derandomize=True, max_examples=50, deadline=None)
@given(value=_urls)
def test_url_determinism(value: str) -> None:
    c = URL()
    first = canonicalize(value, c)
    second = canonicalize(value, c)
    assert first == second
    assert first.canonical_bytes() == second.canonical_bytes()


@pytest.mark.property
@settings(derandomize=True, max_examples=50, deadline=None)
@given(value=_phones)
def test_phone_determinism(value: str) -> None:
    c = Phone()
    first = canonicalize(value, c)
    second = canonicalize(value, c)
    assert first == second
    assert first.canonical_bytes() == second.canonical_bytes()


@pytest.mark.property
@settings(derandomize=True, max_examples=50, deadline=None)
@given(value=_countries)
def test_country_determinism(value: str) -> None:
    c = Country()
    first = canonicalize(value, c)
    second = canonicalize(value, c)
    assert first == second
    assert first.canonical_bytes() == second.canonical_bytes()


@pytest.mark.property
@settings(derandomize=True, max_examples=50, deadline=None)
@given(value=_dates)
def test_date_determinism(value: str) -> None:
    c = Date()
    first = canonicalize(value, c)
    second = canonicalize(value, c)
    assert first == second
    assert first.canonical_bytes() == second.canonical_bytes()


# ---------------------------------------------------------------------------
# 2. FORMAT IDEMPOTENCY — replay(artifact, contract) == artifact
#
# Mandate Law 12: replay rehydrates the artifact from the stored
# canonical_bytes without re-executing the capability. The rehydrated
# artifact must be byte-for-byte equal to the original, for every
# output_format on every capability.
# ---------------------------------------------------------------------------


@pytest.mark.property
@settings(derandomize=True, max_examples=50, deadline=None)
@given(value=_emails)
def test_email_replay_invariant(value: str) -> None:
    c = Email()
    art = canonicalize(value, c)
    rehydrated = replay(art, c)
    assert rehydrated == art
    assert rehydrated.canonical_bytes() == art.canonical_bytes()


@pytest.mark.property
@settings(derandomize=True, max_examples=50, deadline=None)
@given(value=_uuids)
def test_uuid_replay_invariant(value: str) -> None:
    c = UUID()
    art = canonicalize(value, c)
    rehydrated = replay(art, c)
    assert rehydrated == art
    assert rehydrated.canonical_bytes() == art.canonical_bytes()


@pytest.mark.property
@settings(derandomize=True, max_examples=50, deadline=None)
@given(value=_boolean_tokens)
def test_boolean_replay_invariant(value: str) -> None:
    c = Boolean()
    art = canonicalize(value, c)
    rehydrated = replay(art, c)
    assert rehydrated == art
    assert rehydrated.canonical_bytes() == art.canonical_bytes()


@pytest.mark.property
@settings(derandomize=True, max_examples=50, deadline=None)
@given(value=_ips)
def test_ip_replay_invariant(value: str) -> None:
    c = IP()
    art = canonicalize(value, c)
    rehydrated = replay(art, c)
    assert rehydrated == art
    assert rehydrated.canonical_bytes() == art.canonical_bytes()


@pytest.mark.property
@settings(derandomize=True, max_examples=50, deadline=None)
@given(pair=_money_pairs)
def test_money_replay_invariant(pair: tuple[str, str]) -> None:
    value, currency = pair
    c = Money(currency=currency)
    art = canonicalize(value, c)
    rehydrated = replay(art, c)
    assert rehydrated == art
    assert rehydrated.canonical_bytes() == art.canonical_bytes()


@pytest.mark.property
@settings(derandomize=True, max_examples=50, deadline=None)
@given(value=_geolocations)
def test_geolocation_replay_invariant(value: str) -> None:
    c = Geolocation()
    art = canonicalize(value, c)
    rehydrated = replay(art, c)
    assert rehydrated == art
    assert rehydrated.canonical_bytes() == art.canonical_bytes()


@pytest.mark.property
@settings(derandomize=True, max_examples=50, deadline=None)
@given(value=_urls)
def test_url_replay_invariant(value: str) -> None:
    c = URL()
    art = canonicalize(value, c)
    rehydrated = replay(art, c)
    assert rehydrated == art
    assert rehydrated.canonical_bytes() == art.canonical_bytes()


@pytest.mark.property
@settings(derandomize=True, max_examples=50, deadline=None)
@given(value=_phones)
def test_phone_replay_invariant(value: str) -> None:
    c = Phone()
    art = canonicalize(value, c)
    rehydrated = replay(art, c)
    assert rehydrated == art
    assert rehydrated.canonical_bytes() == art.canonical_bytes()


@pytest.mark.property
@settings(derandomize=True, max_examples=50, deadline=None)
@given(value=_countries)
def test_country_replay_invariant(value: str) -> None:
    c = Country()
    art = canonicalize(value, c)
    rehydrated = replay(art, c)
    assert rehydrated == art
    assert rehydrated.canonical_bytes() == art.canonical_bytes()


@pytest.mark.property
@settings(derandomize=True, max_examples=50, deadline=None)
@given(value=_dates)
def test_date_replay_invariant(value: str) -> None:
    c = Date()
    art = canonicalize(value, c)
    rehydrated = replay(art, c)
    assert rehydrated == art
    assert rehydrated.canonical_bytes() == art.canonical_bytes()


# ---------------------------------------------------------------------------
# 3. FORMAT STABILITY — multi-format capabilities produce distinct valid forms
#
# For capabilities with multiple output_format values (country: alpha2/alpha3/
# numeric, date: iso/compact), switching the output_format on the same input
# must produce a different string representation while still yielding a valid
# CANONICALIZED artifact. Each distinct form must be idempotent under its own
# format (re-canonicalizing with the same format reproduces the same value).
# ---------------------------------------------------------------------------


@pytest.mark.property
@settings(derandomize=True, max_examples=50, deadline=None)
@given(value=_countries)
def test_country_format_alpha2_vs_alpha3(value: str) -> None:
    a2 = canonicalize(value, Country(output_format="alpha2"))
    if a2.status is not Status.CANONICALIZED:
        return
    a3 = canonicalize(value, Country(output_format="alpha3"))
    assert a3.status is Status.CANONICALIZED
    # Different format declarations must yield different string values.
    assert a2.value != a3.value
    # Each form is idempotent under its own format.
    assert canonicalize(a2.value, Country(output_format="alpha2")).value == a2.value
    assert canonicalize(a3.value, Country(output_format="alpha3")).value == a3.value


@pytest.mark.property
@settings(derandomize=True, max_examples=50, deadline=None)
@given(value=_countries)
def test_country_format_alpha2_vs_numeric(value: str) -> None:
    a2 = canonicalize(value, Country(output_format="alpha2"))
    if a2.status is not Status.CANONICALIZED:
        return
    num = canonicalize(value, Country(output_format="numeric"))
    assert num.status is Status.CANONICALIZED
    assert a2.value != num.value
    assert canonicalize(a2.value, Country(output_format="alpha2")).value == a2.value
    assert canonicalize(num.value, Country(output_format="numeric")).value == num.value


@pytest.mark.property
@settings(derandomize=True, max_examples=50, deadline=None)
@given(value=_countries)
def test_country_format_alpha3_vs_numeric(value: str) -> None:
    a3 = canonicalize(value, Country(output_format="alpha3"))
    if a3.status is not Status.CANONICALIZED:
        return
    num = canonicalize(value, Country(output_format="numeric"))
    assert num.status is Status.CANONICALIZED
    assert a3.value != num.value
    assert canonicalize(a3.value, Country(output_format="alpha3")).value == a3.value
    assert canonicalize(num.value, Country(output_format="numeric")).value == num.value


@pytest.mark.property
@settings(derandomize=True, max_examples=50, deadline=None)
@given(value=_dates)
def test_date_format_iso_vs_compact(value: str) -> None:
    iso = canonicalize(value, Date(output_format="iso"))
    if iso.status is not Status.CANONICALIZED:
        return
    compact = canonicalize(value, Date(output_format="compact"))
    assert compact.status is Status.CANONICALIZED
    assert iso.value != compact.value
    assert canonicalize(iso.value, Date(output_format="iso")).value == iso.value
    assert canonicalize(compact.value, Date(output_format="compact")).value == compact.value
