# src/paxman/_capabilities/country/contract.py
"""Country contract value objects + builder/registration.

Mandate Law 5: the contract is the truth. It declares *what* the canonical
form is, never *how* it is produced. The canonical form is the ISO 3166-1
alpha-2 code; the bundled alias/code table lives here as a frozen, versioned
dataset (Law 8a — no network I/O).
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any, Literal, cast

import attrs

# ISO 3166-1:2024 dataset is the single shared source (see _iso3166.py).
# Re-exported here so existing importers (canonicalizer, rules) are unchanged.
from paxman._capabilities._iso3166 import (
    _ALPHA2_CODES,
    _NAME_TO_ALPHA2,
    _NUMERIC_TO_ALPHA2,
    _SYNONYM_TO_ALPHA2,
    COUNTRY_TABLE_VERSION,
)
from paxman._capabilities._shared.contract import (
    _authority_override_from_spec,
    authority_override_field,
    strip_authority_override,
)
from paxman._errors import ContractError
from paxman._registry.contract_registry import register_contract

__all__ = [
    "CLDR_VERSION",
    "COUNTRY_TABLE_VERSION",
    "_ALPHA2_CODES",
    "_ALPHA3_TO_ALPHA2",
    "_HISTORICAL_TO_ALPHA2",
    "_LOCALIZED_TO_ALPHA2",
    "_NAME_TO_ALPHA2",
    "_NUMERIC_TO_ALPHA2",
    "_SYNONYM_TO_ALPHA2",
]

# (ISO 3166-1:2024 dataset imported and re-exported from _iso3166 below)

# (ISO 3166-1:2024 dataset imported and re-exported from _iso3166 below)
# codes (v1 scope, matching _ALPHA2_CODES). Mirrors the alpha-2 frozenset
# order. Law 8a: bundled, versioned dataset (COUNTRY_TABLE_VERSION).
# Wrapped in MappingProxyType for runtime immutability (Law 1 + Law 2 — see
# the note in _iso3166.py).
_ALPHA3_TO_ALPHA2: Mapping[str, str] = MappingProxyType(
    {
        "AND": "AD",
        "ARE": "AE",
        "AFG": "AF",
        "ATG": "AG",
        "AIA": "AI",
        "ALB": "AL",
        "ARM": "AM",
        "AGO": "AO",
        "ATA": "AQ",
        "ARG": "AR",
        "ASM": "AS",
        "AUT": "AT",
        "AUS": "AU",
        "ABW": "AW",
        "ALA": "AX",
        "AZE": "AZ",
        "BHS": "BS",
        "BHR": "BH",
        "BGD": "BD",
        "BRB": "BB",
        "BEL": "BE",
        "BEN": "BJ",
        "BLM": "BL",
        "BMU": "BM",
        "BTN": "BT",
        "BOL": "BO",
        "BES": "BQ",
        "BRA": "BR",
        "BVT": "BV",
        "BWA": "BW",
        "BLR": "BY",
        "BLZ": "BZ",
        "BIH": "BA",
        "BFA": "BF",
        "BGR": "BG",
        "BDI": "BI",
        "BRN": "BN",
        "CAN": "CA",
        "CCK": "CC",
        "COD": "CD",
        "CAF": "CF",
        "COG": "CG",
        "CHE": "CH",
        "CIV": "CI",
        "COK": "CK",
        "CHL": "CL",
        "CMR": "CM",
        "CHN": "CN",
        "COL": "CO",
        "CRI": "CR",
        "CUB": "CU",
        "CPV": "CV",
        "CUW": "CW",
        "CXR": "CX",
        "CYP": "CY",
        "CZE": "CZ",
        "DEU": "DE",
        "DJI": "DJ",
        "DNK": "DK",
        "DMA": "DM",
        "DOM": "DO",
        "DZA": "DZ",
        "ECU": "EC",
        "EST": "EE",
        "EGY": "EG",
        "ESH": "EH",
        "ERI": "ER",
        "ESP": "ES",
        "ETH": "ET",
        "FIN": "FI",
        "FJI": "FJ",
        "FLK": "FK",
        "FSM": "FM",
        "FRO": "FO",
        "FRA": "FR",
        "GAB": "GA",
        "GBR": "GB",
        "GRD": "GD",
        "GEO": "GE",
        "GUF": "GF",
        "GGY": "GG",
        "GHA": "GH",
        "GIB": "GI",
        "GRL": "GL",
        "GMB": "GM",
        "GIN": "GN",
        "GLP": "GP",
        "GNQ": "GQ",
        "GRC": "GR",
        "SGS": "GS",
        "GTM": "GT",
        "GUM": "GU",
        "GNB": "GW",
        "GUY": "GY",
        "HKG": "HK",
        "HMD": "HM",
        "HND": "HN",
        "HRV": "HR",
        "HTI": "HT",
        "HUN": "HU",
        "IDN": "ID",
        "IRL": "IE",
        "ISR": "IL",
        "IMN": "IM",
        "IND": "IN",
        "IOT": "IO",
        "IRQ": "IQ",
        "IRN": "IR",
        "ISL": "IS",
        "ITA": "IT",
        "JEY": "JE",
        "JAM": "JM",
        "JOR": "JO",
        "JPN": "JP",
        "KEN": "KE",
        "KGZ": "KG",
        "KHM": "KH",
        "KIR": "KI",
        "COM": "KM",
        "KNA": "KN",
        "PRK": "KP",
        "KOR": "KR",
        "KWT": "KW",
        "CYM": "KY",
        "KAZ": "KZ",
        "LAO": "LA",
        "LBN": "LB",
        "LCA": "LC",
        "LIE": "LI",
        "LKA": "LK",
        "LBR": "LR",
        "LSO": "LS",
        "LTU": "LT",
        "LUX": "LU",
        "LVA": "LV",
        "LBY": "LY",
        "MAR": "MA",
        "MCO": "MC",
        "MDA": "MD",
        "MNE": "ME",
        "MAF": "MF",
        "MDG": "MG",
        "MHL": "MH",
        "MKD": "MK",
        "MLI": "ML",
        "MMR": "MM",
        "MNG": "MN",
        "MAC": "MO",
        "MNP": "MP",
        "MTQ": "MQ",
        "MRT": "MR",
        "MSR": "MS",
        "MLT": "MT",
        "MUS": "MU",
        "MDV": "MV",
        "MWI": "MW",
        "MEX": "MX",
        "MYS": "MY",
        "MOZ": "MZ",
        "NAM": "NA",
        "NCL": "NC",
        "NER": "NE",
        "NFK": "NF",
        "NGA": "NG",
        "NIC": "NI",
        "NLD": "NL",
        "NOR": "NO",
        "NPL": "NP",
        "NRU": "NR",
        "NIU": "NU",
        "NZL": "NZ",
        "OMN": "OM",
        "PAN": "PA",
        "PER": "PE",
        "PYF": "PF",
        "PNG": "PG",
        "PHL": "PH",
        "PAK": "PK",
        "POL": "PL",
        "SPM": "PM",
        "PCN": "PN",
        "PRI": "PR",
        "PSE": "PS",
        "PRT": "PT",
        "PLW": "PW",
        "PRY": "PY",
        "QAT": "QA",
        "REU": "RE",
        "ROU": "RO",
        "SRB": "RS",
        "RUS": "RU",
        "RWA": "RW",
        "SAU": "SA",
        "SLB": "SB",
        "SYC": "SC",
        "SDN": "SD",
        "SWE": "SE",
        "SGP": "SG",
        "SHN": "SH",
        "SVN": "SI",
        "SJM": "SJ",
        "SVK": "SK",
        "SLE": "SL",
        "SMR": "SM",
        "SEN": "SN",
        "SOM": "SO",
        "SUR": "SR",
        "SSD": "SS",
        "STP": "ST",
        "SLV": "SV",
        "SXM": "SX",
        "SYR": "SY",
        "SWZ": "SZ",
        "TCA": "TC",
        "TCD": "TD",
        "ATF": "TF",
        "TGO": "TG",
        "THA": "TH",
        "TJK": "TJ",
        "TKL": "TK",
        "TLS": "TL",
        "TKM": "TM",
        "TUN": "TN",
        "TON": "TO",
        "TUR": "TR",
        "TTO": "TT",
        "TUV": "TV",
        "TWN": "TW",
        "TZA": "TZ",
        "UKR": "UA",
        "UGA": "UG",
        "UMI": "UM",
        "USA": "US",
        "URY": "UY",
        "UZB": "UZ",
        "VAT": "VA",
        "VCT": "VC",
        "VEN": "VE",
        "VGB": "VG",
        "VIR": "VI",
        "VNM": "VN",
        "VUT": "VU",
        "WLF": "WF",
        "WSM": "WS",
        "YEM": "YE",
        "MYT": "YT",
        "ZAF": "ZA",
        "ZMB": "ZM",
        "ZWE": "ZW",
    }
)

# (ISO 3166-1:2024 dataset imported and re-exported from _iso3166 below)

# (ISO 3166-1:2024 dataset imported and re-exported from _iso3166 below)

# ISO 3166-1 numeric -> alpha-2. Numeric codes are official ISO
# representations, zero-padded to 3 digits (e.g. "004" and "4" both denote
# Afghanistan). Law 8a: bundled, versioned dataset (COUNTRY_TABLE_VERSION).
# Source: ISO 3166-1 numeric assignment (generated from Locale::Country /
# UN M.49, matching the ISO 3166/MA official list). User-assigned and
# exceptional/reserved numeric codes (249 fx, 530 an, 891 cs) are excluded
# because they are not in the assigned _ALPHA2_CODES set. Verified bijective
# with _ALPHA2_CODES (249 entries) by the assertion at the foot of this module.
# (ISO 3166-1:2024 dataset imported and re-exported from _iso3166 below)

# Unicode CLDR (Common Locale Data Repository) localized country names ->
# alpha-2. Curated sample spanning several scripts; the full dataset is large,
# so this is opt-in via `localized_names` (data footprint, Law 7). CLDR is a
# versioned authoritative specification (Law 14 source #1).
#: Frozen edition string for the bundled Unicode CLDR localized country-name
#: sample. Recorded as evidence when ``localized_names`` resolves a token
#: (Law 8a — the dataset version participates in replay).
CLDR_VERSION: str = "cldr-45"
_LOCALIZED_TO_ALPHA2: Mapping[str, str] = MappingProxyType(
    {
        # Malaysia
        "ماليزيا": "MY",
        "马来西亚": "MY",
        "マレーシア": "MY",
        "말레이시아": "MY",
        "Малайзия": "MY",
        # United States
        "الولايات المتحدة": "US",
        "美国": "US",
        "アメリカ合衆国": "US",
        "États-Unis": "US",
        # Japan
        "日本": "JP",
        "ژاپن": "JP",
        "Япония": "JP",
        # Germany
        "ألمانيا": "DE",
        "德国": "DE",
        "Deutschland": "DE",
        "Германия": "DE",
        # France
        "فرنسا": "FR",
        "法国": "FR",
        "Франция": "FR",
        # United Kingdom
        "المملكة المتحدة": "GB",
        "英国": "GB",
        "Royaume-Uni": "GB",
        # South Korea
        "한국": "KR",
        "대한민국": "KR",
        # Russia
        "Россия": "RU",
        # China
        "中华人民共和国": "CN",
        # India
        "भारत": "IN",
        # Indonesia
        "إندونيسيا": "ID",
        # Brazil
        "برازيل": "BR",
        "Brasil": "BR",
        # Thailand
        "ประเทศไทย": "TH",
        "Таиланд": "TH",
    }
)

# Historical / deprecated country names -> current alpha-2. Finite, explicit
# mappings (Law 4 — known equivalence). Opt-in via `historical_names` to keep
# the default surface stable. Provenance cites a recorded Paxman policy (Law 14
# §826 bullet 3). Wrapped in MappingProxyType for runtime immutability.
_HISTORICAL_TO_ALPHA2: Mapping[str, str] = MappingProxyType(
    {
        "BURMA": "MM",
        "SWAZILAND": "SZ",
        "CZECH REPUBLIC": "CZ",
        "MACAO": "MO",
        "HONG KONG": "HK",
        "CEYLON": "LK",
        "PERSIA": "IR",
        "SIAM": "TH",
        "EAST GERMANY": "DE",
        "WEST GERMANY": "DE",
        "SERBIA AND MONTENEGRO": "RS",
        "YUGOSLAVIA": "RS",
        "CZECHOSLOVAKIA": "CZ",
        "RHODESIA": "ZW",
        "UPPER VOLTA": "BF",
        "ZAIRE": "CD",
    }
)


def _validate_bool(inst: object, attr: object, value: object) -> None:
    """Attrs validator: policy fields must be real bools (Law 7 — explicit)."""
    if not isinstance(value, bool):
        name = getattr(attr, "name", attr)
        raise ContractError(f"contract field {name!r} must be a bool, got {type(value).__name__}")


def _validate_output_format(inst: object, attr: object, value: object) -> None:
    """Attrs validator: output_format must be one of the supported formats."""
    _SUPPORTED = frozenset({"alpha2", "alpha3", "numeric"})
    if not isinstance(value, str) or value not in _SUPPORTED:
        name = getattr(attr, "name", attr)
        raise ContractError(
            f"contract field {name!r} must be one of {sorted(_SUPPORTED)}, got {value!r}"
        )


def _validate_v1(inst: object, attr: object, value: object) -> None:
    """Attrs validator: version fields must be int 1 (only v1 supported)."""
    if not isinstance(value, int) or isinstance(value, bool) or value != 1:
        name = getattr(attr, "name", attr)
        raise ContractError(f"contract field {name!r} must be int 1, got {value!r}")


def _validate_extra_synonyms(inst: object, attr: object, value: Mapping[str, str]) -> None:
    """Attrs validator: each target must be a 2-letter uppercase alpha-2 code."""
    for _alias, code in value.items():
        if (
            not isinstance(code, str)
            or len(code) != 2
            or not code.isupper()
            or code not in _ALPHA2_CODES
        ):
            raise ContractError(
                f"extra_synonyms target must be a valid ISO 3166-1 alpha-2 code, got {code!r}"
            )


def _freeze_extra_synonyms(value: Mapping[str, str]) -> Mapping[str, str]:
    """Converter: freeze the caller-supplied mapping into a MappingProxyType.

    The contract is `attrs.frozen` so field reassignment already fails, but
    without this converter the stored value could still be a mutable dict the
    caller retains a reference to and mutates post-construction — which would
    change canonicalization behavior under the same contract + dataset
    version (Law 1 Identity + Law 2 Determinism).
    """
    return MappingProxyType(dict(value))


@attrs.frozen
class CanonicalCountryContract:
    """The country contract.

    Fields are policy declarations (mandate Law 7 — Explicit Over Clever).
    `extra_synonyms` is a caller-supplied, replayable alias map (Law 8a).
    `output_format` declares the canonical output form (alpha2, alpha3, or numeric).
    """

    allow_alpha3: bool = attrs.field(default=True, validator=_validate_bool)
    allow_name: bool = attrs.field(default=True, validator=_validate_bool)
    allow_synonym: bool = attrs.field(default=True, validator=_validate_bool)
    # Expansion axes (opt-in where noted). Numeric (ISO 3166-1 M49) is on by
    # default because it is an official ISO shape (Tier 1). Localized (CLDR)
    # and historical names are OFF by default to keep the default data
    # footprint small and the default behaviour stable (Law 7 — explicit).
    allow_numeric: bool = attrs.field(default=True, validator=_validate_bool)
    localized_names: bool = attrs.field(default=False, validator=_validate_bool)
    historical_names: bool = attrs.field(default=False, validator=_validate_bool)
    extra_synonyms: Mapping[str, str] = attrs.field(
        factory=dict,
        validator=_validate_extra_synonyms,
        converter=_freeze_extra_synonyms,
        # Excluded from __hash__: the frozen MappingProxyType it converts to
        # is not hashable, but it stays in __eq__ so two contracts with
        # different synonym maps remain distinct (mandate Law 5 equality).
        hash=False,
    )
    output_format: Literal["alpha2", "alpha3", "numeric"] = attrs.field(
        default="alpha2", validator=_validate_output_format
    )
    kind: str = attrs.field(
        default="canonical_country",
        validator=attrs.validators.matches_re(r"^canonical_country$"),
    )
    version: int = attrs.field(default=1, validator=_validate_v1)
    version_field: int = attrs.field(default=1, validator=_validate_v1)

    authority_override: Any = authority_override_field()

    def as_dict(self) -> dict[str, Any]:
        """Return the Dict DSL form of this contract."""
        return strip_authority_override(
            {
                "kind": self.kind,
                "allow_alpha3": self.allow_alpha3,
                "allow_name": self.allow_name,
                "allow_synonym": self.allow_synonym,
                "allow_numeric": self.allow_numeric,
                "localized_names": self.localized_names,
                "historical_names": self.historical_names,
                "extra_synonyms": dict(self.extra_synonyms),
                "output_format": self.output_format,
                "version": self.version,
                "version_field": self.version_field,
            }
        )


def Country(
    *,
    allow_alpha3: bool = True,
    allow_name: bool = True,
    allow_synonym: bool = True,
    allow_numeric: bool = True,
    localized_names: bool = False,
    historical_names: bool = False,
    extra_synonyms: Mapping[str, str] | None = None,
    output_format: Literal["alpha2", "alpha3", "numeric"] = "alpha2",
    authority_override: Any | None = None,
) -> CanonicalCountryContract:
    """Domain-type sugar: declare a country contract in user vocabulary.

    Args:
        allow_alpha3: accept ISO 3166-1 alpha-3 codes. Default True.
        allow_name: accept canonical country names. Default True.
        allow_synonym: accept bundled aliases (USA, UK, …). Default True.
        allow_numeric: accept ISO 3166-1 numeric (M49) codes. Default True.
        localized_names: accept Unicode CLDR localized names (multilingual).
            Default False (data footprint; opt-in).
        historical_names: accept deprecated/historical names (Burma→Myanmar).
            Default False (keeps default surface stable).
        extra_synonyms: caller-supplied {alias: alpha2} map (replayable,
            Law 8a). Default None (empty).
        output_format: the canonical output form. Default "alpha2".
            Supported: "alpha2", "alpha3", "numeric".

    Returns:
        A frozen CanonicalCountryContract instance.

    Raises:
        ContractError: if a flag argument is not a bool, if an
            `extra_synonyms` target is not a valid alpha-2 code, or if
            `output_format` is not one of the supported formats.
    """
    return CanonicalCountryContract(
        allow_alpha3=_require_bool("allow_alpha3", allow_alpha3),
        allow_name=_require_bool("allow_name", allow_name),
        allow_synonym=_require_bool("allow_synonym", allow_synonym),
        allow_numeric=_require_bool("allow_numeric", allow_numeric),
        localized_names=_require_bool("localized_names", localized_names),
        historical_names=_require_bool("historical_names", historical_names),
        extra_synonyms=dict(extra_synonyms) if extra_synonyms is not None else {},
        output_format=output_format,
        authority_override=authority_override,
    )


def _require_bool(field: str, value: object) -> bool:
    """Validate that a contract field is a real bool (Law 7 — explicit)."""
    if not isinstance(value, bool):
        raise ContractError(f"contract field {field!r} must be a bool, got {type(value).__name__}")
    return value


def _require_v1(field: str, value: object) -> int:
    """Validate that a contract version field is the supported v1 (Law 7)."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ContractError(f"contract field {field!r} must be int 1, got {type(value).__name__}")
    if value != 1:
        raise ContractError(
            f"contract field {field!r} must be 1 (only v1 is supported), got {value}"
        )
    return value


def _build_country(spec: dict[str, Any]) -> CanonicalCountryContract:
    _require_v1("version", spec.get("version", 1))
    _require_v1("version_field", spec.get("version_field", 1))
    extra = spec.get("extra_synonyms", {})
    if not isinstance(extra, dict):
        raise ContractError("extra_synonyms must be a dict")
    output_format = spec.get("output_format", "alpha2")
    _SUPPORTED_OUTPUT_FORMATS = frozenset({"alpha2", "alpha3", "numeric"})
    if not isinstance(output_format, str) or output_format not in _SUPPORTED_OUTPUT_FORMATS:
        supported = sorted(_SUPPORTED_OUTPUT_FORMATS)
        raise ContractError(f"output_format must be one of {supported}, got {output_format!r}")
    output_format = cast(Literal["alpha2", "alpha3", "numeric"], output_format)
    return CanonicalCountryContract(
        allow_alpha3=_require_bool("allow_alpha3", spec.get("allow_alpha3", True)),
        allow_name=_require_bool("allow_name", spec.get("allow_name", True)),
        allow_synonym=_require_bool("allow_synonym", spec.get("allow_synonym", True)),
        allow_numeric=_require_bool("allow_numeric", spec.get("allow_numeric", True)),
        localized_names=_require_bool("localized_names", spec.get("localized_names", False)),
        historical_names=_require_bool("historical_names", spec.get("historical_names", False)),
        extra_synonyms=dict(extra),
        output_format=output_format,
        authority_override=_authority_override_from_spec(spec),
    )


register_contract("canonical_country", _build_country)
