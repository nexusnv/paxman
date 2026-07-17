# src/paxman/_capabilities/geolocation/canonicalizer.py
"""GeolocationCapability: a built-in capability of Paxman v2.

Mandate Laws 3, 4, 5, 7, 8a, 11, 14. The datum, axis order, hemisphere policy,
output format, and precision live in the contract (Law 5 — the contract is the
truth). The capability applies them; it never guesses the datum, the axis order,
or the hemisphere (Law 3 / Law 7). All coordinate arithmetic uses exact
``decimal.Decimal`` — never ``float`` (spec §4.3).

Architecture (recognition → resolver → validation → classify), mirroring the
ip/money capabilities. Recognition is delegated to ``grammar.recognize``; the
resolver applies the contract policy and validates ranges.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal

import attrs

from paxman._capabilities.geolocation.contract import CanonicalGeolocationContract
from paxman._capabilities.geolocation.grammar import (
    RecognizedRep,
    _parse_number,
    _split_sign,
    recognize,
)
from paxman._capabilities.geolocation.rules import _evidence
from paxman._core.contracts import Contract
from paxman._core.provenance import Evidence
from paxman._core.result import CapabilityResult
from paxman._core.status import Status

# Latitude range (degrees) and longitude range (degrees), inclusive.
_LAT_MIN = Decimal("-90")
_LAT_MAX = Decimal("90")
_LON_MIN = Decimal("-180")
_LON_MAX = Decimal("180")


@attrs.frozen
class _Candidate:
    """A single enumerated reading of a geolocation-shaped input."""

    value: str
    rule: str
    source: str
    evidence: tuple[Evidence, ...]


def _quantize(value: Decimal, precision: int) -> str:
    """Quantize a Decimal to ``precision`` places, preserving trailing zeros.

    Uses exact ``Decimal.quantize`` with ``ROUND_HALF_EVEN`` so the canonical
    form keeps exactly ``precision`` decimal places (F1-equivalent — literal
    decimal places preserved, replay-stable). Never drops trailing zeros.

    Args:
        value: The exact Decimal coordinate value.
        precision: Number of decimal places in the canonical output.

    Returns:
        The quantized decimal string with exactly ``precision`` places.
    """
    exponent = Decimal(1).scaleb(-precision)
    quantized = value.quantize(exponent, rounding=ROUND_HALF_EVEN)
    # Decimal renders zero as scientific notation (e.g. "0E-7") above 6 places.
    # The canonical form must stay fixed-point so it re-parses as a valid input
    # (Law 2 idempotence / replay byte-equality). Force trailing-zero notation.
    if quantized == 0:
        return f"0.{'0' * precision}"
    return str(quantized)


def _axis_sign(letter: str | None, sign: str) -> int:
    """Resolve the sign of an axis from an explicit signal.

    A hemisphere letter (N/E positive, S/W negative) or a leading sign sets the
    sign explicitly. Returns ``1`` for positive, ``-1`` for negative.

    Args:
        letter: A hemisphere letter (N/S/E/W) or ``None``.
        sign: A sign string (``"+"`` or ``"-"``).

    Returns:
        ``1`` for positive, ``-1`` for negative.
    """
    if letter is not None:
        return -1 if letter in ("S", "W") else 1
    return -1 if sign == "-" else 1


def generate_interpretations(
    rep: RecognizedRep, contract: CanonicalGeolocationContract
) -> list[_Candidate]:
    """Resolve a recognized rep into candidate canonical forms (resolver).

    Applies the contract's ``coordinate_order`` to assign the captured axes to
    (latitude, longitude), resolves hemisphere signals, converts DMS to decimal,
    validates ranges, and quantizes to the contract precision. A malformed or
    out-of-range input returns no candidates (surfaced as INVALID by the caller,
    never guessed).

    Args:
        rep: The RecognizedRep from the recognition layer.
        contract: The CanonicalGeolocationContract (policy authority).

    Returns:
        A list with one ``_Candidate`` when the input resolves deterministically,
        or an empty list when the input is malformed or out of range.
    """
    shape = rep.shape
    caps = rep.captures
    evidence: list[Evidence] = []
    # When True, v1/v2 already carry their signed value (geo_dms_signed) and
    # must not be re-multiplied by _axis_sign in Stage 5.
    _signs_in_magnitude = False

    # Stage 1: extract the two raw axes and any hemisphere signals.
    if shape == "geo_decimal_pair":
        evidence.append(_evidence("recognized_decimal_pair"))
        a1_sign, a1_body = _split_sign(caps["a1"])
        a2_sign, a2_body = _split_sign(caps["a2"])
        h1 = h2 = None
        v1 = _parse_number(a1_body)
        v2 = _parse_number(a2_body)
        s1 = a1_sign
        s2 = a2_sign
    elif shape == "geo_decimal_hemi":
        evidence.append(_evidence("recognized_decimal_hemisphere"))
        h1 = caps.get("h1")
        h2 = caps.get("h2")
        # The numeric body carries the magnitude; the hemisphere letter carries
        # the sign. An explicit numeric sign AND a hemisphere letter both assert
        # a sign, which is a conflicting input and must be rejected (Law 4),
        # never silently resolved. The magnitude is taken as absolute; the
        # letter sets the sign exactly once in Stage 5.
        a1_sign, a1_body = _split_sign(caps["a1"])
        a2_sign, a2_body = _split_sign(caps["a2"])
        v1 = _parse_number(a1_body)
        v2 = _parse_number(a2_body)
        if h1 is not None and a1_sign != "+":
            return []
        if h2 is not None and a2_sign != "+":
            return []
        # The explicit numeric sign is redundant with a consistent letter; the
        # letter alone drives the sign. Record it as "+" so Stage 5 does not
        # double-apply the numeric sign.
        s1 = s2 = "+"
    elif shape == "geo_dms":
        evidence.append(_evidence("recognized_dms"))
        h1 = caps.get("h1")
        h2 = caps.get("h2")
        d1 = _parse_number(caps["d1"])
        m1 = _parse_number(caps["m1"])
        sec1 = _parse_number(caps["s1"])
        d2 = _parse_number(caps["d2"])
        m2 = _parse_number(caps["m2"])
        sec2 = _parse_number(caps["s2"])
        v1 = d1 + m1 / Decimal(60) + sec1 / Decimal(3600)
        v2 = d2 + m2 / Decimal(60) + sec2 / Decimal(3600)
        s1 = s2 = "+"
        evidence.append(_evidence("dms_to_decimal"))
    elif shape == "geo_dms_signed":
        evidence.append(_evidence("recognized_dms"))
        h1 = h2 = None
        # Each DMS component (degrees, minutes, seconds) carries its own sign and
        # is summed literally per spec §4.1 (decimal = d + m/60 + s/3600). The
        # resulting magnitude is ALREADY signed, so the hemisphere signal is taken
        # from the degree sign but the magnitude must NOT be re-multiplied by
        # _axis_sign (that would double-apply the sign). See `_signs_in_magnitude`.
        d1 = _parse_number(caps["d1"])
        m1 = _parse_number(caps["m1"])
        sec1 = _parse_number(caps["s1"])
        d2 = _parse_number(caps["d2"])
        m2 = _parse_number(caps["m2"])
        sec2 = _parse_number(caps["s2"])
        v1 = d1 + m1 / Decimal(60) + sec1 / Decimal(3600)
        v2 = d2 + m2 / Decimal(60) + sec2 / Decimal(3600)
        # Signal (for Stage 3 ambiguity) from the degree sign; magnitude already
        # carries the full signed value.
        s1 = "-" if d1 < 0 else "+"
        s2 = "-" if d2 < 0 else "+"
        _signs_in_magnitude = True
        evidence.append(_evidence("dms_to_decimal"))
    else:
        return []

    # Stage 2: assign captured axes to (lat, lon) via contract coordinate_order.
    # When the input carries an explicit hemisphere signal (letter or sign), that
    # signal wins; otherwise the contract order decides. No auto-detection.
    lat_raw: Decimal
    lon_raw: Decimal
    lat_sign: str
    lon_sign: str
    lat_letter: str | None
    lon_letter: str | None
    if contract.coordinate_order == "lon_lat":
        lon_raw, lat_raw = v1, v2
        lon_sign, lat_sign = s1, s2
        lon_letter, lat_letter = h1, h2
    else:
        lat_raw, lon_raw = v1, v2
        lat_sign, lon_sign = s1, s2
        lat_letter, lon_letter = h1, h2
    evidence.append(
        _evidence("axis_order_applied", f"coordinate_order={contract.coordinate_order}")
    )

    # Stage 3: resolve hemisphere per axis. A letter or sign sets the sign
    # explicitly; an unsigned, letter-less axis is ambiguous when the contract
    # requires a hemisphere, otherwise defaulted to positive.
    lat_signal = lat_letter is not None or lat_sign != "+"
    lon_signal = lon_letter is not None or lon_sign != "+"
    if not lat_signal and contract.require_hemisphere:
        return []
    if not lon_signal and contract.require_hemisphere:
        return []
    if lat_signal or lon_signal:
        evidence.append(_evidence("hemisphere_resolved"))
    else:
        evidence.append(_evidence("hemisphere_defaulted"))

    _lat_factor = Decimal(1) if _signs_in_magnitude else Decimal(_axis_sign(lat_letter, lat_sign))
    _lon_factor = Decimal(1) if _signs_in_magnitude else Decimal(_axis_sign(lon_letter, lon_sign))
    lat_value = lat_raw * _lat_factor
    lon_value = lon_raw * _lon_factor

    # Stage 4: range check (latitude in [-90, 90], longitude in [-180, 180]).
    if not (_LAT_MIN <= lat_value <= _LAT_MAX):
        return []
    if not (_LON_MIN <= lon_value <= _LON_MAX):
        return []

    # Stage 5: quantize each axis to contract precision (trailing zeros kept).
    lat_str = _quantize(lat_value, contract.precision)
    lon_str = _quantize(lon_value, contract.precision)
    evidence.append(_evidence("precision_applied", f"precision={contract.precision}"))

    canonical = f"{lat_str},{lon_str}"
    evidence.append(_evidence("canonicalized_geolocation", f"{rep.raw!r} -> {canonical!r}"))
    return [
        _Candidate(
            value=canonical,
            rule="canonicalized_geolocation",
            source="ISO 6709 (geographic point coord) + WGS84 datum",
            evidence=tuple(evidence),
        )
    ]


def classify(
    rep: RecognizedRep | None,
    candidates: list[_Candidate],
    contract: CanonicalGeolocationContract,
) -> tuple[Status, str | None, tuple[Evidence, ...], tuple[str, ...] | None]:
    """Classify resolver output into a canonicalization outcome.

    Returns a 4-tuple (status, value, evidence, candidates). When the input is
    unsigned on an axis and the contract requires a hemisphere, the two competing
    readings (positive / negative) are enumerated as AMBIGUOUS candidates (Law 4),
    never guessed.

    Args:
        rep: The RecognizedRep (or ``None`` when no shape matched).
        candidates: The resolver's candidate list.
        contract: The CanonicalGeolocationContract (policy authority).

    Returns:
        A 4-tuple of (status, value, evidence, candidates).
    """
    if rep is None:
        return Status.INVALID, None, (_evidence("unrecognized_format"),), None
    if not candidates:
        # Resolver rejected a malformed or out-of-range input. When the input was
        # a decimal pair with no hemisphere signal and the contract requires one,
        # surface the ambiguity instead of guessing (Law 4).
        if rep.shape == "geo_decimal_pair" and contract.require_hemisphere:
            caps = rep.captures
            a1_sign, a1_body = _split_sign(caps["a1"])
            a2_sign, a2_body = _split_sign(caps["a2"])
            a1 = _parse_number(a1_body)
            a2 = _parse_number(a2_body)
            # Map the two raw axes to (lat, lon) per the contract's input order.
            if contract.coordinate_order == "lon_lat":
                lon, lon_sign, lat, lat_sign = a1, a1_sign, a2, a2_sign
            else:
                lat, lat_sign, lon, lon_sign = a1, a1_sign, a2, a2_sign
            if _LAT_MIN <= lat <= _LAT_MAX and _LON_MIN <= lon <= _LON_MAX:
                # An axis with an explicit sign is fixed; only an unsigned axis
                # is ambiguous (Law 4 — never guess the missing sign). Each
                # reading is emitted in canonical latitude,longitude order.
                lat_vals = (lat,) if lat_sign != "+" else (lat, -lat)
                lon_vals = (lon,) if lon_sign != "+" else (lon, -lon)
                readings = tuple(
                    f"{_quantize(lv, contract.precision)},{_quantize(lonv, contract.precision)}"
                    for lv in lat_vals
                    for lonv in lon_vals
                )
                return (
                    Status.AMBIGUOUS,
                    None,
                    (_evidence("ambiguous_hemisphere"),),
                    readings,
                )
        return Status.INVALID, None, (_evidence("out_of_range"),), None
    c = candidates[0]
    return Status.CANONICALIZED, c.value, c.evidence, None


class GeolocationCapability:
    """A pure deterministic transformation that canonicalizes geolocations."""

    name: str = "geolocation_canonicalization"

    def can_handle(self, contract: Contract, value: object) -> bool:
        """Return True if this capability canonicalizes the given contract.

        Accepts a CanonicalGeolocationContract with a string (or None) value.
        """
        return isinstance(contract, CanonicalGeolocationContract) and (
            value is None or isinstance(value, str)
        )

    def canonicalize(self, value: object, contract: Contract) -> CapabilityResult:
        """Canonicalize a geolocation string into "<lat>,<lon>".

        Args:
            value: The raw geolocation string (or None).
            contract: The CanonicalGeolocationContract (policy authority).

        Returns:
            A CapabilityResult with status CANONICALIZED and the canonical form,
            or INVALID / MISSING / AMBIGUOUS when the input cannot be
            deterministically resolved (empty, malformed, out of range, or an
            unsigned axis under a hemisphere-requiring contract).
        """
        if not isinstance(contract, CanonicalGeolocationContract):
            return CapabilityResult(
                status=Status.INVALID, evidence=(_evidence("not_a_geolocation_contract"),)
            )
        if not (value is None or isinstance(value, str)):
            return CapabilityResult(
                status=Status.INVALID, evidence=(_evidence("not_a_string_value"),)
            )

        # Missing/whitespace-only value -> MISSING (spec §5, Law 8).
        if value is None or value.strip(" \t\r\n\f\v") == "":
            return CapabilityResult(status=Status.MISSING, evidence=(_evidence("missing_value"),))

        # Track whether surrounding whitespace was stripped (record if changed).
        stripped_evidence: tuple[Evidence, ...] = ()
        stripped = value.strip(" \t\r\n\f\v")
        if stripped != value:
            stripped_evidence = (_evidence("trimmed_whitespace"),)
            value = stripped

        # Recognition layer (Layer 1) — shape classification only.
        rep = recognize(value)
        if rep is None:
            return CapabilityResult(
                status=Status.INVALID, evidence=(_evidence("unrecognized_format"),)
            )

        # Resolver (applies contract policy) + classify.
        cands = generate_interpretations(rep, contract)
        status, rendered, evidence, cands_out = classify(rep, cands, contract)
        if stripped_evidence:
            evidence = stripped_evidence + evidence
        return CapabilityResult(
            status=status, value=rendered, evidence=evidence, candidates=cands_out
        )
