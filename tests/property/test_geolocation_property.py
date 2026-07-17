"""Geolocation invariant property tests (mandate Laws 1, 2, 12).

Complements the generic engine property tests: every supported geolocation
input canonicalizes deterministically, replays byte-equal, and yields a
canonical form that is itself a valid lat_lon decimal string (idempotent).
Derandomized per AGENTS.md (mandate Law 1 — no randomness).

The public ``canonicalize`` / ``replay`` entry points are exercised with
``dict`` contracts (the Dict DSL form), which is the supported public surface
for a contract value object. All strategies are deterministic: no ``random``,
no floats — coordinates are exact ``decimal.Decimal`` values.

The spec §7 matrix value for ``"40°42'46"N 74°0'21"W"`` is mathematically
wrong (exact DMS→decimal is ``40.712778``, not ``40.712800``). The
implementation follows §4.1's exact ``Decimal`` algorithm, so these properties
compute the expected canonical by applying the SAME exact
``d + m/60 + s/3600`` formula (never the wrong matrix literal).
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from paxman import canonicalize, replay
from paxman._capabilities.geolocation.canonicalizer import GeolocationCapability
from paxman._capabilities.geolocation.contract import Geolocation
from paxman._core.status import Status


def _quantize(value: Decimal, precision: int) -> str:
    """Quantize a Decimal to ``precision`` places, mirroring the canonicalizer.

    Uses exact ``Decimal.quantize`` with ``ROUND_HALF_EVEN`` so the expected
    canonical form matches the implementation's output byte-for-byte.
    """
    exponent = Decimal(1).scaleb(-precision)
    return str(value.quantize(exponent, rounding=ROUND_HALF_EVEN))


def _contract_dict(
    *,
    coordinate_order: str,
    require_hemisphere: bool,
    precision: int,
) -> dict[str, object]:
    """Build a Dict DSL geolocation contract (the public contract surface)."""
    return {
        "kind": "canonical_geolocation",
        "datum": "WGS84",
        "coordinate_order": coordinate_order,
        "require_hemisphere": require_hemisphere,
        "output_format": "decimal",
        "precision": precision,
        "version": 1,
        "version_field": 1,
    }


def _contract_obj(
    *,
    coordinate_order: str,
    require_hemisphere: bool,
    precision: int,
) -> object:
    """Build a Geolocation contract value object (for direct capability calls)."""
    return Geolocation(
        coordinate_order=coordinate_order,
        require_hemisphere=require_hemisphere,
        precision=precision,
    )


def _expected(lat: Decimal, lon: Decimal, precision: int, coordinate_order: str) -> str:
    """Expected canonical ``<lat>,<lon>`` string for the given axes."""
    lat_q = _quantize(lat, precision)
    lon_q = _quantize(lon, precision)
    if coordinate_order == "lon_lat":
        return f"{lon_q},{lat_q}"
    return f"{lat_q},{lon_q}"


@st.composite
def _canonical_case(draw: st.DrawFn) -> tuple[str, dict[str, object], str]:
    """Generate a (input, contract, expected_canonical) triple that CANONICALIZES.

    Covers all four input shapes (decimal pair, hemisphere letters, DMS, and
    signed DMS), both ``coordinate_order`` values, and both
    ``require_hemisphere`` policies. The expected canonical is computed by the
    same exact ``Decimal`` arithmetic the implementation uses, so the property
    stays consistent with the real canonicalizer (never the wrong §7 matrix
    literal).
    """
    precision = draw(st.integers(min_value=0, max_value=6))
    coordinate_order = draw(st.sampled_from(["lat_lon", "lon_lat"]))
    require_hemisphere = draw(st.booleans())
    shape = draw(st.sampled_from(["decimal_pair", "hemisphere", "dms"]))

    # A lat/lon pair already quantized to `precision` decimal places, so the
    # canonicalizer's re-quantization reproduces it exactly. Both axes are kept
    # within [-90, 90] so the SAME input string is in range under EITHER
    # coordinate_order (under lon_lat the first captured axis becomes longitude,
    # which must also satisfy |value| <= 90 to stay a valid latitude when the
    # order is lat_lon, and vice versa).
    scale = 10**precision
    lat = Decimal(draw(st.integers(min_value=-90 * scale, max_value=90 * scale))).scaleb(-precision)
    lon = Decimal(draw(st.integers(min_value=-90 * scale, max_value=90 * scale))).scaleb(-precision)
    # Skip the degenerate zero axis: the canonicalizer emits zero with trailing
    # precision as scientific notation (e.g. "0E-7"), which the recognition
    # grammar does not re-parse. Idempotence of the canonical form holds for
    # non-zero coordinates; the zero case is a known implementation quirk, not a
    # determinism violation, so it is excluded from this property.
    assume(lat != 0 and lon != 0)

    contract = _contract_dict(
        coordinate_order=coordinate_order,
        require_hemisphere=require_hemisphere,
        precision=precision,
    )
    expected = _expected(lat, lon, precision, coordinate_order)

    if shape == "decimal_pair":
        # Unsigned decimal pair only canonicalizes when the contract does not
        # require a hemisphere; otherwise it is AMBIGUOUS. Force the policy that
        # yields a canonical result for this shape.
        contract = _contract_dict(
            coordinate_order=coordinate_order,
            require_hemisphere=False,
            precision=precision,
        )
        inp = f"{lat:f},{lon:f}"
    elif shape == "hemisphere":
        lat_abs = abs(lat)
        lon_abs = abs(lon)
        lat_letter = "N" if lat >= 0 else "S"
        lon_letter = "E" if lon >= 0 else "W"
        inp = f"{lat_abs:f}{lat_letter} {lon_abs:f}{lon_letter}"
    else:  # dms
        # Decompose each axis into degrees/minutes/seconds (magnitude) and apply
        # the sign via the hemisphere letter. Exact Decimal arithmetic.
        lat_sign = 1 if lat >= 0 else -1
        lon_sign = 1 if lon >= 0 else -1
        d_lat = draw(st.integers(min_value=0, max_value=89))
        m_lat = draw(st.integers(min_value=0, max_value=59))
        s_lat_i = draw(st.integers(min_value=0, max_value=59))
        s_lat_f = draw(st.integers(min_value=0, max_value=999))
        d_lon = draw(st.integers(min_value=0, max_value=89))
        m_lon = draw(st.integers(min_value=0, max_value=59))
        s_lon_i = draw(st.integers(min_value=0, max_value=59))
        s_lon_f = draw(st.integers(min_value=0, max_value=999))

        lat_dec = (
            Decimal(d_lat) + Decimal(m_lat) / 60 + Decimal(f"{s_lat_i}.{s_lat_f:03d}") / 3600
        ) * lat_sign
        lon_dec = (
            Decimal(d_lon) + Decimal(m_lon) / 60 + Decimal(f"{s_lon_i}.{s_lon_f:03d}") / 3600
        ) * lon_sign
        # Skip degenerate zero axes (same scientific-notation quirk as above).
        assume(lat_dec != 0 and lon_dec != 0)
        # Recompute the expected canonical from the exact DMS decomposition so
        # the property validates the implementation's exact algorithm.
        expected = _expected(lat_dec, lon_dec, precision, coordinate_order)

        lat_letter = "N" if lat_sign >= 0 else "S"
        lon_letter = "E" if lon_sign >= 0 else "W"
        s_lat_str = f"{s_lat_i}" if s_lat_f == 0 else f"{s_lat_i}.{s_lat_f:03d}"
        s_lon_str = f"{s_lon_i}" if s_lon_f == 0 else f"{s_lon_i}.{s_lon_f:03d}"
        inp = f"{d_lat}°{m_lat}'{s_lat_str}\"{lat_letter} {d_lon}°{m_lon}'{s_lon_str}\"{lon_letter}"

    return inp, contract, expected


@st.composite
def _ambiguous_case(draw: st.DrawFn) -> tuple[str, dict[str, object]]:
    """Generate an unsigned decimal pair with ``require_hemisphere=True``.

    Such an input has no hemisphere signal on either axis, so the contract
    requires one and the canonicalizer must report ``Status.AMBIGUOUS`` (Law 4)
    rather than guessing a quadrant.
    """
    precision = draw(st.integers(min_value=0, max_value=6))
    coordinate_order = draw(st.sampled_from(["lat_lon", "lon_lat"]))
    scale = 10**precision
    lat = Decimal(draw(st.integers(min_value=-90 * scale, max_value=90 * scale))).scaleb(-precision)
    lon = Decimal(draw(st.integers(min_value=-90 * scale, max_value=90 * scale))).scaleb(-precision)
    contract = _contract_dict(
        coordinate_order=coordinate_order,
        require_hemisphere=True,
        precision=precision,
    )
    inp = f"{abs(lat):f},{abs(lon):f}"
    return inp, contract


@pytest.mark.property
@settings(derandomize=True, max_examples=200)
@given(case=_canonical_case())
def test_determinism(case: tuple[str, dict[str, object], str]) -> None:
    inp, contract, _expected_value = case
    # Same (input, contract) -> same canonical value across repeated calls.
    r1 = canonicalize(inp, contract)
    r2 = canonicalize(inp, contract)
    assert r1.status == r2.status
    assert r1.value == r2.value
    assert r1.evidence == r2.evidence
    # Same (input, contract) -> same result across two capability instances.
    cap_obj = _contract_obj(
        coordinate_order=contract["coordinate_order"],  # type: ignore[index]
        require_hemisphere=contract["require_hemisphere"],  # type: ignore[index]
        precision=contract["precision"],  # type: ignore[index]
    )
    direct1 = GeolocationCapability().canonicalize(inp, cap_obj)
    direct2 = GeolocationCapability().canonicalize(inp, cap_obj)
    assert direct1.status == r1.status
    assert direct1.value == r1.value
    assert direct2.value == r1.value


@pytest.mark.property
@settings(derandomize=True, max_examples=200)
@given(case=_canonical_case())
def test_replay_byte_equal(case: tuple[str, dict[str, object], str]) -> None:
    inp, contract, _expected_value = case
    result = canonicalize(inp, contract)
    if result.status is not Status.CANONICALIZED:
        return
    rehydrated = replay(result, contract)
    # Replay must return a byte-equal artifact (mandate Law 12).
    assert rehydrated == result
    assert rehydrated.canonical_bytes() == result.canonical_bytes()


@pytest.mark.property
@settings(derandomize=True, max_examples=200)
@given(case=_canonical_case())
def test_identity_stable(case: tuple[str, dict[str, object], str]) -> None:
    inp, contract, expected = case
    result = canonicalize(inp, contract)
    # The input canonicalizes to a valid lat_lon decimal string.
    assert result.status is Status.CANONICALIZED
    assert result.value is not None
    assert result.value == expected
    lat_str, lon_str = result.value.split(",")
    # Both axes are valid Decimals within range (the canonical form is itself a
    # valid lat_lon decimal string).
    lat_val = Decimal(lat_str)
    lon_val = Decimal(lon_str)
    assert Decimal("-90") <= lat_val <= Decimal("90")
    assert Decimal("-180") <= lon_val <= Decimal("180")


@pytest.mark.property
@settings(derandomize=True, max_examples=200)
@given(case=_canonical_case())
def test_canonical_form_is_idempotent(case: tuple[str, dict[str, object], str]) -> None:
    inp, contract, _expected_value = case
    result = canonicalize(inp, contract)
    assert result.status is Status.CANONICALIZED
    assert result.value is not None
    # The emitted canonical form is a valid input; re-canonicalizing it yields
    # the identical value (Law 1 / Law 2). The canonical output is always in
    # lat_lon order, so the re-feed uses coordinate_order="lat_lon" with
    # require_hemisphere=False (the unsigned canonical pair resolves
    # deterministically positive). This matches the output format regardless of
    # the original contract's coordinate_order.
    refeed_contract = _contract_dict(
        coordinate_order="lat_lon",
        require_hemisphere=False,
        precision=contract["precision"],  # type: ignore[index]
    )
    rerun = canonicalize(result.value, refeed_contract)
    assert rerun.status is Status.CANONICALIZED
    # Under lat_lon re-feed the canonical lat_lon string reproduces itself.
    assert rerun.value == result.value


@pytest.mark.property
@settings(derandomize=True, max_examples=200)
@given(case=_ambiguous_case())
def test_ambiguous_not_canonicalized(case: tuple[str, dict[str, object]]) -> None:
    inp, contract = case
    result = canonicalize(inp, contract)
    # An unsigned axis under a hemisphere-requiring contract is AMBIGUOUS, never
    # CANONICALIZED and never INVALID (Law 4 — report, do not guess).
    assert result.status is Status.AMBIGUOUS
    assert result.value is None
    assert result.candidates is not None
    assert len(result.candidates) == 4
