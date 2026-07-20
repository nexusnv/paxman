# src/paxman/_capabilities/money/contract.py
"""Money contract value objects + builder/registration.

Mandate Law 5: the contract is the truth. It declares *what* the canonical
form is, never *how* it is produced. The currency is REQUIRED (no default):
Paxman must never guess the currency (Law 3 — Never Guess; Law 7 — Explicit
Over Clever).
"""

from __future__ import annotations

from typing import Any

import attrs

from paxman._capabilities._shared.contract import (
    _authority_override_from_spec,
    authority_override_field,
    strip_authority_override,
)
from paxman._errors import ContractError
from paxman._registry.contract_registry import register_contract

#: Frozen edition string for the bundled ISO 4217 dataset. Recorded on every
#: artifact's evidence (Law 8a — the dataset version participates in replay).
#: The cited source is embodied in full: the complete ISO 4217:2015 active
#: code list (maintained by the SIX Group Maintenance Agency; amendments
#: through #179, effective 2026-01-01, which added XAD; the 2026-01-01
#: Bulgaria->EUR change withdrew BGN, and the 2023-01-01 Croatia->EUR change
#: withdrew HRK — both withdrawn codes are excluded). Law 15: a cited
#: named-entity source (currencies) is adopted in full; there is no curated
#: subset.
MONEY_TABLE_VERSION: str = (
    "iso4217:2015 (SIX Maintenance Agency register, amendments through #179, effective 2026-01-01)"
)

# Full ISO 4217:2015 active alphabetic code list (177 codes: 159 national/
# supranational + 18 X-codes). Fixed, deterministic, versioned (no network I/O
# — Law 8a). Every code the contract accepts is present; the validator below
# checks membership against this complete set.
_ISO4217_CODES: frozenset[str] = frozenset(
    {
        "AED",
        "AFN",
        "ALL",
        "AMD",
        "ANG",
        "AOA",
        "ARS",
        "AUD",
        "AWG",
        "AZN",
        "BAM",
        "BBD",
        "BDT",
        "BHD",
        "BIF",
        "BMD",
        "BND",
        "BOB",
        "BOV",
        "BRL",
        "BSD",
        "BTN",
        "BWP",
        "BYN",
        "BZD",
        "CAD",
        "CDF",
        "CHE",
        "CHF",
        "CHW",
        "CLF",
        "CLP",
        "CNY",
        "COP",
        "COU",
        "CRC",
        "CUP",
        "CVE",
        "CZK",
        "DJF",
        "DKK",
        "DOP",
        "DZD",
        "EGP",
        "ERN",
        "ETB",
        "EUR",
        "FJD",
        "FKP",
        "GBP",
        "GEL",
        "GHS",
        "GIP",
        "GMD",
        "GNF",
        "GTQ",
        "GYD",
        "HKD",
        "HNL",
        "HTG",
        "HUF",
        "IDR",
        "ILS",
        "INR",
        "IQD",
        "IRR",
        "ISK",
        "JMD",
        "JOD",
        "JPY",
        "KES",
        "KGS",
        "KHR",
        "KMF",
        "KPW",
        "KRW",
        "KWD",
        "KYD",
        "KZT",
        "LAK",
        "LBP",
        "LKR",
        "LRD",
        "LYD",
        "MAD",
        "MDL",
        "MGA",
        "MKD",
        "MMK",
        "MNT",
        "MOP",
        "MRU",
        "MUR",
        "MVR",
        "MWK",
        "MXN",
        "MXV",
        "MYR",
        "MZN",
        "NAD",
        "NGN",
        "NIO",
        "NOK",
        "NPR",
        "NZD",
        "OMR",
        "PAB",
        "PEN",
        "PGK",
        "PHP",
        "PKR",
        "PLN",
        "PYG",
        "QAR",
        "RON",
        "RSD",
        "RUB",
        "RWF",
        "SAR",
        "SBD",
        "SCR",
        "SDG",
        "SEK",
        "SGD",
        "SHP",
        "SLE",
        "SOS",
        "SRD",
        "SSP",
        "STN",
        "SVC",
        "SYP",
        "SZL",
        "THB",
        "TJS",
        "TMT",
        "TND",
        "TOP",
        "TRY",
        "TTD",
        "TWD",
        "TZS",
        "UAH",
        "UGX",
        "USD",
        "USN",
        "UYI",
        "UYU",
        "UYW",
        "UZS",
        "VED",
        "VES",
        "VND",
        "VUV",
        "WST",
        "XAD",
        "XAF",
        "XAG",
        "XAU",
        "XBA",
        "XBB",
        "XBC",
        "XBD",
        "XCD",
        "XDR",
        "XOF",
        "XPD",
        "XPF",
        "XPT",
        "XSU",
        "XTS",
        "XUA",
        "XXX",
        "YER",
        "ZAR",
        "ZMW",
        "ZWL",
    }
)


def _validate_currency(inst: object, attr: object, value: str) -> None:
    """Attrs validator: currency must be a recognized 3-letter ISO 4217 code."""
    if not isinstance(value, str) or len(value) != 3 or not value.isalpha():
        raise ContractError(f"currency must be a 3-letter ISO 4217 code, got {value!r}")
    if value.upper() not in _ISO4217_CODES:
        raise ContractError(f"unknown ISO 4217 currency code: {value!r}")


def _validate_bool(inst: object, attr: object, value: object) -> None:
    """Attrs validator: policy fields must be real bools (Law 7 — explicit)."""
    if not isinstance(value, bool):
        name = getattr(attr, "name", attr)
        raise ContractError(f"contract field {name!r} must be a bool, got {type(value).__name__}")


def _validate_v1(inst: object, attr: object, value: object) -> None:
    """Attrs validator: version fields must be int 1 (only v1 is supported)."""
    if not isinstance(value, int) or isinstance(value, bool) or value != 1:
        name = getattr(attr, "name", attr)
        raise ContractError(f"contract field {name!r} must be int 1, got {value!r}")


@attrs.frozen
class CanonicalMoneyContract:
    """The money contract.

    Fields are policy declarations (mandate Law 7 — Explicit Over Clever).
    `currency` is REQUIRED with no default: the capability must never guess the
    currency (Law 3). Validators enforce the invariants on every construction
    path (factory, Dict DSL, and direct instantiation) so a broken contract
    fails before canonicalization.
    """

    currency: str = attrs.field(validator=_validate_currency)
    allow_symbol: bool = attrs.field(default=True, validator=_validate_bool)
    allow_code: bool = attrs.field(default=True, validator=_validate_bool)
    strip_spaces: bool = attrs.field(default=True, validator=_validate_bool)
    kind: str = attrs.field(
        default="canonical_money",
        validator=attrs.validators.matches_re(r"^canonical_money$"),
    )
    version: int = attrs.field(default=1, validator=_validate_v1)
    version_field: int = attrs.field(default=1, validator=_validate_v1)

    authority_override: Any = authority_override_field()

    def as_dict(self) -> dict[str, Any]:
        """Return the Dict DSL form of this contract."""
        return strip_authority_override(
            {
                "kind": self.kind,
                "currency": self.currency,
                "allow_symbol": self.allow_symbol,
                "allow_code": self.allow_code,
                "strip_spaces": self.strip_spaces,
                "version": self.version,
                "version_field": self.version_field,
            }
        )


def Money(
    *,
    currency: str,
    allow_symbol: bool = True,
    allow_code: bool = True,
    strip_spaces: bool = True,
    authority_override: Any | None = None,
) -> CanonicalMoneyContract:
    """Domain-type sugar: declare a money contract in user vocabulary.

    Args:
        currency: ISO 4217 alpha code. REQUIRED — no default (Law 7).
        allow_symbol: accept currency symbols ($/€/£/¥) in input, validating
            them against `currency`. Default True.
        allow_code: accept ISO codes ("MYR") in input, validating against
            `currency`. Default True.
        strip_spaces: trim ASCII whitespace around the amount. Default True.

    Returns:
        A frozen CanonicalMoneyContract instance.

    Raises:
        ContractError: if `currency` is missing, not a 3-letter string, not a
            recognized ISO 4217 code, or if a flag argument is not a bool.
    """
    if not isinstance(currency, str):
        raise ContractError(
            f"currency must be a 3-letter ISO 4217 code, got {type(currency).__name__}"
        )
    cur = currency.upper()
    if len(cur) != 3 or not cur.isalpha() or cur not in _ISO4217_CODES:
        raise ContractError(f"unknown ISO 4217 currency code: {currency!r}")
    return CanonicalMoneyContract(
        currency=cur,
        allow_symbol=_require_bool("allow_symbol", allow_symbol),
        allow_code=_require_bool("allow_code", allow_code),
        strip_spaces=_require_bool("strip_spaces", strip_spaces),
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


def _build_money(spec: dict[str, Any]) -> CanonicalMoneyContract:
    currency = spec.get("currency")
    if not isinstance(currency, str) or len(currency) != 3 or not currency.isalpha():
        raise ContractError(
            f"contract field 'currency' must be a 3-letter ISO 4217 code, got {currency!r}"
        )
    cur = currency.upper()
    if cur not in _ISO4217_CODES:
        raise ContractError(f"unknown ISO 4217 currency code: {currency!r}")
    _require_v1("version", spec.get("version", 1))
    _require_v1("version_field", spec.get("version_field", 1))
    return CanonicalMoneyContract(
        currency=cur,
        allow_symbol=_require_bool("allow_symbol", spec.get("allow_symbol", True)),
        allow_code=_require_bool("allow_code", spec.get("allow_code", True)),
        strip_spaces=_require_bool("strip_spaces", spec.get("strip_spaces", True)),
        authority_override=_authority_override_from_spec(spec),
    )


register_contract("canonical_money", _build_money)
