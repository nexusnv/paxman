# src/paxman/_capabilities/country/contract.py
"""Country contract value objects + builder/registration.

Mandate Law 5: the contract is the truth. It declares *what* the canonical
form is, never *how* it is produced. The canonical form is the ISO 3166-1
alpha-2 code; the bundled alias/code table lives here as a frozen, versioned
dataset (Law 8a — no network I/O).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import attrs

from paxman._errors import ContractError
from paxman._registry.contract_registry import register_contract

# Version of the bundled ISO 3166-1 dataset. Recorded on every artifact's
# evidence (Law 8a — the dataset version participates in replay).
COUNTRY_TABLE_VERSION = "iso3166-1:2020"

# Frozen set of every officially assigned ISO 3166-1 alpha-2 code (v1 scope:
# the 249 assigned user-assigned-reserved-excluded codes).
# NOTE: the spec (§3.3) describes this as an identity dict `_ALPHA2_TO_CODE`
# ({"US": "US", ...}); this plan implements it as a `frozenset[str]`
# (`_ALPHA2_CODES`) instead. The resolver checks membership
# (`token in _ALPHA2_CODES`) and the canonical form is the token itself, so the
# two are functionally identical. The frozenset form is also what
# `_validate_extra_synonyms` checks target codes against, keeping a single
# source of truth. Keep the plan/spec terminology in sync if the spec is
# revised.
_ALPHA2_CODES: frozenset[str] = frozenset(
    {
        "AD", "AE", "AF", "AG", "AI", "AL", "AM", "AO", "AQ", "AR", "AS", "AT",
        "AU", "AW", "AX", "AZ", "BA", "BB", "BD", "BE", "BF", "BG", "BH", "BI",
        "BJ", "BL", "BM", "BN", "BO", "BQ", "BR", "BS", "BT", "BV", "BW", "BY",
        "BZ", "CA", "CC", "CD", "CF", "CG", "CH", "CI", "CK", "CL", "CM", "CN",
        "CO", "CR", "CU", "CV", "CW", "CX", "CY", "CZ", "DE", "DJ", "DK", "DM",
        "DO", "DZ", "EC", "EE", "EG", "EH", "ER", "ES", "ET", "FI", "FJ", "FK",
        "FM", "FO", "FR", "GA", "GB", "GD", "GE", "GF", "GG", "GH", "GI", "GL",
        "GM", "GN", "GP", "GQ", "GR", "GS", "GT", "GU", "GW", "GY", "HK", "HM",
        "HN", "HR", "HT", "HU", "ID", "IE", "IL", "IM", "IN", "IO", "IQ", "IR",
        "IS", "IT", "JE", "JM", "JO", "JP", "KE", "KG", "KH", "KI", "KM", "KN",
        "KP", "KR", "KW", "KY", "KZ", "LA", "LB", "LC", "LI", "LK", "LR", "LS",
        "LT", "LU", "LV", "LY", "MA", "MC", "MD", "ME", "MF", "MG", "MH", "MK",
        "ML", "MM", "MN", "MO", "MP", "MQ", "MR", "MS", "MT", "MU", "MV", "MW",
        "MX", "MY", "MZ", "NA", "NC", "NE", "NF", "NG", "NI", "NL", "NO", "NP",
        "NR", "NU", "NZ", "OM", "PA", "PE", "PF", "PG", "PH", "PK", "PL", "PM",
        "PN", "PR", "PS", "PT", "PW", "PY", "QA", "RE", "RO", "RS", "RU", "RW",
        "SA", "SB", "SC", "SD", "SE", "SG", "SH", "SI", "SJ", "SK", "SL", "SM",
        "SN", "SO", "SR", "SS", "ST", "SV", "SX", "SY", "SZ", "TC", "TD", "TF",
        "TG", "TH", "TJ", "TK", "TL", "TM", "TN", "TO", "TR", "TT", "TV", "TW",
        "TZ", "UA", "UG", "UM", "US", "UY", "UZ", "VA", "VC", "VE", "VG", "VI",
        "VN", "VU", "WF", "WS", "YE", "YT", "ZA", "ZM", "ZW",
    }
)

# ISO 3166-1 alpha-3 -> alpha-2. A representative curated subset (extend to
# full 249 as needed; the structure is fixed).
_ALPHA3_TO_ALPHA2: dict[str, str] = {
    "USA": "US", "GBR": "GB", "DEU": "DE", "FRA": "FR", "CAN": "CA",
    "AUS": "AU", "JPN": "JP", "CHN": "CN", "IND": "IN", "BRA": "BR",
    "RUS": "RU", "ITA": "IT", "ESP": "ES", "MEX": "MX", "KOR": "KR",
    "NLD": "NL", "CHE": "CH", "SWE": "SE", "NOR": "NO", "DNK": "DK",
    "FIN": "FI", "POL": "PL", "AUT": "AT", "BEL": "BE", "IRL": "IE",
    "NZL": "NZ", "SGP": "SG", "MYS": "MY", "ZAF": "ZA", "ARG": "AR",
    "PRT": "PT", "GRC": "GR", "CZE": "CZ", "HUN": "HU", "THA": "TH",
}

# Canonical English short name (uppercased) -> alpha-2.
_NAME_TO_ALPHA2: dict[str, str] = {
    "UNITED STATES": "US", "UNITED STATES OF AMERICA": "US",
    "UNITED KINGDOM": "GB", "GREAT BRITAIN": "GB",
    "GERMANY": "DE", "FRANCE": "FR", "CANADA": "CA", "AUSTRALIA": "AU",
    "JAPAN": "JP", "CHINA": "CN", "INDIA": "IN", "BRAZIL": "BR",
    "RUSSIA": "RU", "ITALY": "IT", "SPAIN": "ES", "MEXICO": "MX",
    "SOUTH KOREA": "KR", "KOREA REPUBLIC": "KR", "NETHERLANDS": "NL",
    "SWITZERLAND": "CH", "SWEDEN": "SE", "NORWAY": "NO", "DENMARK": "DK",
    "FINLAND": "FI", "POLAND": "PL", "AUSTRIA": "AT", "BELGIUM": "BE",
    "IRELAND": "IE", "NEW ZEALAND": "NZ", "SINGAPORE": "SG",
    "MALAYSIA": "MY", "SOUTH AFRICA": "ZA", "ARGENTINA": "AR",
    "PORTUGAL": "PT", "GREECE": "GR", "CZECHIA": "CZ", "CZECH REPUBLIC": "CZ",
    "HUNGARY": "HU", "THAILAND": "TH",
}

# Common aliases / synonyms (uppercased) -> alpha-2. UK->GB per BCP 47 §2.
_SYNONYM_TO_ALPHA2: dict[str, str] = {
    "USA": "US", "U.S.A.": "US", "U.S.": "US", "AMERICA": "US",
    "UK": "GB", "ENGLAND": "GB", "SCOTLAND": "GB", "BRITAIN": "GB",
    "GREAT BRITAIN": "GB", "U.K.": "GB", "DEUTSCHLAND": "DE",
}


def _validate_bool(inst: object, attr: object, value: object) -> None:
    """Attrs validator: policy fields must be real bools (Law 7 — explicit)."""
    if not isinstance(value, bool):
        name = getattr(attr, "name", attr)
        raise ContractError(f"contract field {name!r} must be a bool, got {type(value).__name__}")


def _validate_v1(inst: object, attr: object, value: object) -> None:
    """Attrs validator: version fields must be int 1 (only v1 supported)."""
    if not isinstance(value, int) or isinstance(value, bool) or value != 1:
        name = getattr(attr, "name", attr)
        raise ContractError(f"contract field {name!r} must be int 1, got {value!r}")


def _validate_extra_synonyms(inst: object, attr: object, value: Mapping[str, str]) -> None:
    """Attrs validator: each target must be a 2-letter uppercase alpha-2 code."""
    for alias, code in value.items():
        if not isinstance(code, str) or len(code) != 2 or not code.isupper() or code not in _ALPHA2_CODES:
            raise ContractError(
                f"extra_synonyms target must be a valid ISO 3166-1 alpha-2 code, got {code!r}"
            )


@attrs.frozen
class CanonicalCountryContract:
    """The country contract.

    Fields are policy declarations (mandate Law 7 — Explicit Over Clever).
    `extra_synonyms` is a caller-supplied, replayable alias map (Law 8a).
    """

    allow_alpha3: bool = attrs.field(default=True, validator=_validate_bool)
    allow_name: bool = attrs.field(default=True, validator=_validate_bool)
    allow_synonym: bool = attrs.field(default=True, validator=_validate_bool)
    extra_synonyms: Mapping[str, str] = attrs.field(factory=dict, validator=_validate_extra_synonyms)
    kind: str = attrs.field(
        default="canonical_country",
        validator=attrs.validators.matches_re(r"^canonical_country$"),
    )
    version: int = attrs.field(default=1, validator=_validate_v1)
    version_field: int = attrs.field(default=1, validator=_validate_v1)

    def as_dict(self) -> dict[str, Any]:
        """Return the Dict DSL form of this contract."""
        return {
            "kind": self.kind,
            "allow_alpha3": self.allow_alpha3,
            "allow_name": self.allow_name,
            "allow_synonym": self.allow_synonym,
            "extra_synonyms": dict(self.extra_synonyms),
            "version": self.version,
            "version_field": self.version_field,
        }


def Country(
    *,
    allow_alpha3: bool = True,
    allow_name: bool = True,
    allow_synonym: bool = True,
    extra_synonyms: Mapping[str, str] | None = None,
) -> CanonicalCountryContract:
    """Domain-type sugar: declare a country contract in user vocabulary.

    Args:
        allow_alpha3: accept ISO 3166-1 alpha-3 codes. Default True.
        allow_name: accept canonical country names. Default True.
        allow_synonym: accept bundled aliases (USA, UK, …). Default True.
        extra_synonyms: caller-supplied {alias: alpha2} map (replayable,
            Law 8a). Default None (empty).

    Returns:
        A frozen CanonicalCountryContract instance.

    Raises:
        ContractError: if a flag argument is not a bool, or if an
            `extra_synonyms` target is not a valid alpha-2 code.
    """
    return CanonicalCountryContract(
        allow_alpha3=_require_bool("allow_alpha3", allow_alpha3),
        allow_name=_require_bool("allow_name", allow_name),
        allow_synonym=_require_bool("allow_synonym", allow_synonym),
        extra_synonyms=dict(extra_synonyms) if extra_synonyms is not None else {},
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
        raise ContractError(f"contract field {field!r} must be 1 (only v1 is supported), got {value}")
    return value


def _build_country(spec: dict[str, Any]) -> CanonicalCountryContract:
    _require_v1("version", spec.get("version", 1))
    _require_v1("version_field", spec.get("version_field", 1))
    extra = spec.get("extra_synonyms", {})
    if not isinstance(extra, dict):
        raise ContractError("extra_synonyms must be a dict")
    return CanonicalCountryContract(
        allow_alpha3=_require_bool("allow_alpha3", spec.get("allow_alpha3", True)),
        allow_name=_require_bool("allow_name", spec.get("allow_name", True)),
        allow_synonym=_require_bool("allow_synonym", spec.get("allow_synonym", True)),
        extra_synonyms=dict(extra),
    )


register_contract("canonical_country", _build_country)
