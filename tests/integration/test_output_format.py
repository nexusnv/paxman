"""End-to-end integration tests for the output_format feature.

Exercises ``paxman.canonicalize()`` with different ``output_format`` values
for every capability that declares one, verifying:

1. Default ``output_format`` produces expected output (backward compat).
2. Non-default ``output_format`` produces different output (where multiple
   formats exist).
3. Invalid ``output_format`` raises ``ContractError`` at construction time
   (fail fast).
4. Multiple calls with different ``output_format`` on the same input produce
   different artifacts (where multiple formats exist).
"""

from __future__ import annotations

import pytest

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
from paxman._errors import ContractError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok(artifact: object) -> None:
    """Assert the artifact was canonicalized successfully."""
    assert artifact.status is Status.CANONICALIZED  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# 1. Default output_format produces expected output (backward compat)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestDefaultOutputFormat:
    """Every capability's default output_format must produce the expected
    canonical form — backward compatibility guarantee."""

    def test_email_default(self) -> None:
        r = canonicalize("USER@EXAMPLE.COM", Email())
        _ok(r)
        assert r.value == "user@example.com"

    def test_uuid_default(self) -> None:
        r = canonicalize("a1b2c3d4-e5f6-4789-a1b2-c3d4e5f67890", UUID())
        _ok(r)
        assert r.value == "a1b2c3d4-e5f6-4789-a1b2-c3d4e5f67890"

    def test_boolean_default(self) -> None:
        r = canonicalize("Yes", Boolean())
        _ok(r)
        assert r.value == "true"

    def test_ip_default(self) -> None:
        r = canonicalize("192.168.001.001", IP())
        _ok(r)
        assert r.value == "192.168.1.1"

    def test_money_default(self) -> None:
        r = canonicalize("RM 12.50", Money(currency="MYR"))
        _ok(r)
        assert r.value == "MYR:12.50"

    def test_geolocation_default(self) -> None:
        r = canonicalize("40.7128N 74.0060W", Geolocation())
        _ok(r)
        assert r.value == "40.712800,-74.006000"

    def test_url_default(self) -> None:
        r = canonicalize("https://Example.COM/path", URL())
        _ok(r)
        assert r.value == "https://example.com/path"

    def test_phone_default(self) -> None:
        r = canonicalize("+12025550123", Phone())
        _ok(r)
        assert r.value == "+12025550123"

    def test_country_default_alpha2(self) -> None:
        r = canonicalize("United States", Country())
        _ok(r)
        assert r.value == "US"

    def test_country_default_explicit_alpha2(self) -> None:
        r = canonicalize("United States", Country(output_format="alpha2"))
        _ok(r)
        assert r.value == "US"

    def test_date_default(self) -> None:
        r = canonicalize("2025-01-15", Date())
        _ok(r)
        assert r.value == "2025-01-15"


# ---------------------------------------------------------------------------
# 2. Non-default output_format produces different output
#    (only country and date have multiple supported formats)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestNonDefaultOutputFormat:
    """Capabilities with multiple output formats must produce different
    canonical forms when a non-default format is selected."""

    def test_country_alpha3(self) -> None:
        r = canonicalize("United States", Country(output_format="alpha3"))
        _ok(r)
        assert r.value == "USA"

    def test_country_numeric(self) -> None:
        r = canonicalize("United States", Country(output_format="numeric"))
        _ok(r)
        assert r.value == "840"

    def test_date_compact(self) -> None:
        r = canonicalize("2025-01-15", Date(output_format="compact"))
        _ok(r)
        assert r.value == "20250115"

    def test_country_alpha3_from_alpha2_input(self) -> None:
        r = canonicalize("US", Country(output_format="alpha3"))
        _ok(r)
        assert r.value == "USA"

    def test_country_numeric_from_alpha3_input(self) -> None:
        r = canonicalize("USA", Country(output_format="numeric"))
        _ok(r)
        assert r.value == "840"

    def test_date_compact_from_iso_input(self) -> None:
        r = canonicalize("March 5, 2025", Date(locale="US", output_format="compact"))
        _ok(r)
        assert r.value == "20250305"


# ---------------------------------------------------------------------------
# 3. Invalid output_format raises ContractError at construction time
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestInvalidOutputFormat:
    """An unsupported ``output_format`` value must raise ``ContractError``
    at contract construction — fail fast, never at canonicalization time."""

    def test_email_invalid_format(self) -> None:
        with pytest.raises(ContractError):
            Email(output_format="base64")  # type: ignore[arg-type]

    def test_uuid_invalid_format(self) -> None:
        with pytest.raises(ContractError):
            UUID(output_format="braced")  # type: ignore[arg-type]

    def test_boolean_invalid_format(self) -> None:
        with pytest.raises(ContractError):
            Boolean(output_format="TRUE_FALSE")  # type: ignore[arg-type]

    def test_ip_invalid_format(self) -> None:
        with pytest.raises(ContractError):
            IP(output_format="dotted")  # type: ignore[arg-type]

    def test_money_invalid_format(self) -> None:
        with pytest.raises(ContractError):
            Money(currency="USD", output_format="symbol")  # type: ignore[arg-type]

    def test_geolocation_invalid_format(self) -> None:
        with pytest.raises(ContractError):
            Geolocation(output_format="dms")  # type: ignore[arg-type]

    def test_url_invalid_format(self) -> None:
        with pytest.raises(ContractError):
            URL(output_format="short")  # type: ignore[arg-type]

    def test_phone_invalid_format(self) -> None:
        with pytest.raises(ContractError):
            Phone(output_format="national")  # type: ignore[arg-type]

    def test_country_invalid_format(self) -> None:
        with pytest.raises(ContractError):
            Country(output_format="name")  # type: ignore[arg-type]

    def test_date_invalid_format(self) -> None:
        with pytest.raises(ContractError):
            Date(output_format="rfc2822")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 4. Multiple calls with different output_format on same input produce
#    different artifacts (only country and date have multiple formats)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestDifferentFormatsProduceDifferentArtifacts:
    """When a capability supports multiple output formats, calling
    ``canonicalize`` with different formats on the same input must produce
    distinct artifact values."""

    def test_country_all_three_formats(self) -> None:
        input_value = "Japan"
        alpha2 = canonicalize(input_value, Country(output_format="alpha2"))
        alpha3 = canonicalize(input_value, Country(output_format="alpha3"))
        numeric = canonicalize(input_value, Country(output_format="numeric"))
        _ok(alpha2)
        _ok(alpha3)
        _ok(numeric)
        assert alpha2.value == "JP"
        assert alpha3.value == "JPN"
        assert numeric.value == "392"
        # All three must be distinct.
        assert len({alpha2.value, alpha3.value, numeric.value}) == 3

    def test_country_alpha2_vs_alpha3(self) -> None:
        input_value = "Malaysia"
        a2 = canonicalize(input_value, Country(output_format="alpha2"))
        a3 = canonicalize(input_value, Country(output_format="alpha3"))
        _ok(a2)
        _ok(a3)
        assert a2.value == "MY"
        assert a3.value == "MYS"
        assert a2.value != a3.value

    def test_date_iso_vs_compact(self) -> None:
        input_value = "December 25, 2025"
        iso = canonicalize(input_value, Date(locale="US", output_format="iso"))
        compact = canonicalize(input_value, Date(locale="US", output_format="compact"))
        _ok(iso)
        _ok(compact)
        assert iso.value == "2025-12-25"
        assert compact.value == "20251225"
        assert iso.value != compact.value

    def test_country_artifacts_are_replayable(self) -> None:
        """Each format-specific artifact must be independently replayable."""
        input_value = "Germany"
        for fmt in ("alpha2", "alpha3", "numeric"):
            contract = Country(output_format=fmt)
            artifact = canonicalize(input_value, contract)
            _ok(artifact)
            rehydrated = replay(artifact, contract)
            assert rehydrated == artifact
            assert rehydrated.canonical_bytes() == artifact.canonical_bytes()

    def test_date_artifacts_are_replayable(self) -> None:
        """Each format-specific date artifact must be independently replayable."""
        input_value = "2025-06-15"
        for fmt in ("iso", "compact"):
            contract = Date(output_format=fmt)
            artifact = canonicalize(input_value, contract)
            _ok(artifact)
            rehydrated = replay(artifact, contract)
            assert rehydrated == artifact
            assert rehydrated.canonical_bytes() == artifact.canonical_bytes()
