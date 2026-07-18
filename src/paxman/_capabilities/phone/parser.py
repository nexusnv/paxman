# src/paxman/_capabilities/phone/parser.py
"""ISO 3166-1 alpha-2 -> ITU-T E.164 country code lookup.

Mandate Law 5: the contract declares the country; this table is the
deterministic mapping from that declared policy to the E.164 prefix. No
inference, no dataset. Extending the table is a capability-version bump
(Law 8a) — the version rides on the artifact's VersionStamp.

Law 15 (cited named-entity source adopted in full): the cited source is
ISO 3166-1:2024 (the same edition the country capability embodies). The
E.164 calling-code assignment is taken from the ITU-T E.164 country code
list (Annex to ITU Operational Bulletin No. 1114, 15.XII.2016, complement to
ITU-T Recommendation E.164 (11/2010)). Every one of the 249 officially
assigned ISO 3166-1 alpha-2 codes is mapped; the table is asserted complete
against ``_ALPHA2_CODES`` at import time so a partial adoption can never
silently reappear. The provenance reference (``COUNTRY_TABLE_VERSION``) is
imported from the shared ``_iso3166`` module — it is NOT duplicated here.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from paxman._capabilities._iso3166 import _ALPHA2_CODES, COUNTRY_TABLE_VERSION
from paxman._errors import ContractError

# Full ISO 3166-1:2024 alpha-2 -> ITU-T E.164 country calling code.
# 249 entries, matching the cited enumeration exactly. Codes that share a
# parent's calling code (e.g. NANP territories under "1", RU/KZ under "7")
# resolve to the administering state's code — the alpha-2 remains the
# disambiguator, which is what this capability keys on. XK (Kosovo) is a
# user-assigned code, not part of ISO 3166-1:2024, so it is intentionally
# excluded (Law 15 — only the cited source's enumeration is embodied).
# Wrapped in MappingProxyType for runtime immutability (Law 1 + Law 2 —
# the E.164 map is replay-affecting bundled state).
_COUNTRY_TO_CC: Mapping[str, str] = MappingProxyType(
    {
        "AD": "376",
        "AE": "971",
        "AF": "93",
        "AG": "1",
        "AI": "1",
        "AL": "355",
        "AM": "374",
        "AO": "244",
        "AQ": "672",
        "AR": "54",
        "AS": "1",
        "AT": "43",
        "AU": "61",
        "AW": "297",
        "AX": "358",
        "AZ": "994",
        "BA": "387",
        "BB": "1",
        "BD": "880",
        "BE": "32",
        "BF": "226",
        "BG": "359",
        "BH": "973",
        "BI": "257",
        "BJ": "229",
        "BL": "590",
        "BM": "1",
        "BN": "673",
        "BO": "591",
        "BQ": "599",
        "BR": "55",
        "BS": "1",
        "BT": "975",
        "BV": "47",
        "BW": "267",
        "BY": "375",
        "BZ": "501",
        "CA": "1",
        "CC": "61",
        "CD": "243",
        "CF": "236",
        "CG": "242",
        "CH": "41",
        "CI": "225",
        "CK": "682",
        "CL": "56",
        "CM": "237",
        "CN": "86",
        "CO": "57",
        "CR": "506",
        "CU": "53",
        "CV": "238",
        "CW": "599",
        "CX": "61",
        "CY": "357",
        "CZ": "420",
        "DE": "49",
        "DJ": "253",
        "DK": "45",
        "DM": "1",
        "DO": "1",
        "DZ": "213",
        "EC": "593",
        "EE": "372",
        "EG": "20",
        "EH": "212",
        "ER": "291",
        "ES": "34",
        "ET": "251",
        "FI": "358",
        "FJ": "679",
        "FK": "500",
        "FM": "691",
        "FO": "298",
        "FR": "33",
        "GA": "241",
        "GB": "44",
        "GD": "1",
        "GE": "995",
        "GF": "594",
        "GG": "44",
        "GH": "233",
        "GI": "350",
        "GL": "299",
        "GM": "220",
        "GN": "224",
        "GP": "590",
        "GQ": "240",
        "GR": "30",
        "GS": "672",
        "GT": "502",
        "GU": "1",
        "GW": "245",
        "GY": "592",
        "HK": "852",
        "HM": "672",
        "HN": "504",
        "HR": "385",
        "HT": "509",
        "HU": "36",
        "ID": "62",
        "IE": "353",
        "IL": "972",
        "IM": "44",
        "IN": "91",
        "IO": "246",
        "IQ": "964",
        "IR": "98",
        "IS": "354",
        "IT": "39",
        "JE": "44",
        "JM": "1",
        "JO": "962",
        "JP": "81",
        "KE": "254",
        "KG": "996",
        "KH": "855",
        "KI": "686",
        "KM": "269",
        "KN": "1",
        "KP": "850",
        "KR": "82",
        "KW": "965",
        "KY": "1",
        "KZ": "7",
        "LA": "856",
        "LB": "961",
        "LC": "1",
        "LI": "423",
        "LK": "94",
        "LR": "231",
        "LS": "266",
        "LT": "370",
        "LU": "352",
        "LV": "371",
        "LY": "218",
        "MA": "212",
        "MC": "377",
        "MD": "373",
        "ME": "382",
        "MF": "590",
        "MG": "261",
        "MH": "692",
        "MK": "389",
        "ML": "223",
        "MM": "95",
        "MN": "976",
        "MO": "853",
        "MP": "1",
        "MQ": "596",
        "MR": "222",
        "MS": "1",
        "MT": "356",
        "MU": "230",
        "MV": "960",
        "MW": "265",
        "MX": "52",
        "MY": "60",
        "MZ": "258",
        "NA": "264",
        "NC": "687",
        "NE": "227",
        "NF": "672",
        "NG": "234",
        "NI": "505",
        "NL": "31",
        "NO": "47",
        "NP": "977",
        "NR": "674",
        "NU": "683",
        "NZ": "64",
        "OM": "968",
        "PA": "507",
        "PE": "51",
        "PF": "689",
        "PG": "675",
        "PH": "63",
        "PK": "92",
        "PL": "48",
        "PM": "508",
        "PN": "64",
        "PR": "1",
        "PS": "970",
        "PT": "351",
        "PW": "680",
        "PY": "595",
        "QA": "974",
        "RE": "262",
        "RO": "40",
        "RS": "381",
        "RU": "7",
        "RW": "250",
        "SA": "966",
        "SB": "677",
        "SC": "248",
        "SD": "249",
        "SE": "46",
        "SG": "65",
        "SH": "290",
        "SI": "386",
        "SJ": "47",
        "SK": "421",
        "SL": "232",
        "SM": "378",
        "SN": "221",
        "SO": "252",
        "SR": "597",
        "SS": "211",
        "ST": "239",
        "SV": "503",
        "SX": "1",
        "SY": "963",
        "SZ": "268",
        "TC": "1",
        "TD": "235",
        "TF": "262",
        "TG": "228",
        "TH": "66",
        "TJ": "992",
        "TK": "690",
        "TL": "670",
        "TM": "993",
        "TN": "216",
        "TO": "676",
        "TR": "90",
        "TT": "1",
        "TV": "688",
        "TW": "886",
        "TZ": "255",
        "UA": "380",
        "UG": "256",
        "UM": "1",
        "US": "1",
        "UY": "598",
        "UZ": "998",
        "VA": "379",
        "VC": "1",
        "VE": "58",
        "VG": "1",
        "VI": "1",
        "VN": "84",
        "VU": "678",
        "WF": "681",
        "WS": "685",
        "YE": "967",
        "YT": "262",
        "ZA": "27",
        "ZM": "260",
        "ZW": "263",
    }
)

# Law 15 guard: the E.164 map must embody the full cited ISO 3166-1:2024
# enumeration. Fail fast at import if any assigned code is missing or any
# code outside the cited source has crept in. Uses an explicit `raise` (not
# `assert`) so the guard still runs under `python -O` (asserts are stripped
# in optimized mode, which would let a partial adoption silently slip in —
# a Law 15 violation that the runtime check exists to prevent).
_missing = set(_ALPHA2_CODES) - set(_COUNTRY_TO_CC)
_extra = set(_COUNTRY_TO_CC) - set(_ALPHA2_CODES)
if _missing or _extra:
    raise RuntimeError(
        "phone E.164 map must embody ISO 3166-1:2024 in full "
        f"(missing={sorted(_missing)}, extra={sorted(_extra)})"
    )


def _cc_for_country(country: str) -> str:
    """Return the E.164 country code for an ISO 3166-1 alpha-2 code.

    Raises:
        ContractError: if `country` is not a code in the full ISO 3166-1:2024
            enumeration (edition ``COUNTRY_TABLE_VERSION``). Unknown codes are a
            contract error at parse time, never a runtime guess (Law 3 — Never
            Guess). Because the map is complete against the cited source, this
            only fires for inputs outside ISO 3166-1:2024 entirely.
    """
    cc = _COUNTRY_TO_CC.get(country.upper())
    if cc is None:
        raise ContractError(
            f"unknown country code: {country!r}; must be an ISO 3166-1:2024 "
            f"alpha-2 code (edition {COUNTRY_TABLE_VERSION})"
        )
    return cc
