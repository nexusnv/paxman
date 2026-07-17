# src/paxman/_capabilities/_iso3166.py
"""Shared, versioned ISO 3166-1:2020 dataset (Law 8a — bundled, versioned, no I/O).

This module is the SINGLE authoritative source for the ISO 3166-1:2020 named-entity
enumeration used by Paxman. Both the country capability (recognition of country
names/codes) and the phone capability (ISO 3166-1 alpha-2 -> ITU-T E.164 calling-code
expansion) import from here so the cited provenance reference is defined in exactly one
place (MANDATE Law 15 — a cited named-entity source is adopted in full, and its citation
is not duplicated across capabilities).

The frozen edition string is ``COUNTRY_TABLE_VERSION``; every artifact that depends on
this dataset records it as evidence (Law 8a — the dataset version participates in replay).
All 249 officially assigned user-assigned-excluded alpha-2 codes are present; the name,
synonym, and numeric tables are complete against that enumeration.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

COUNTRY_TABLE_VERSION = "iso3166-1:2020"

_ALPHA2_CODES: frozenset[str] = frozenset(
    {
        "AD",
        "AE",
        "AF",
        "AG",
        "AI",
        "AL",
        "AM",
        "AO",
        "AQ",
        "AR",
        "AS",
        "AT",
        "AU",
        "AW",
        "AX",
        "AZ",
        "BA",
        "BB",
        "BD",
        "BE",
        "BF",
        "BG",
        "BH",
        "BI",
        "BJ",
        "BL",
        "BM",
        "BN",
        "BO",
        "BQ",
        "BR",
        "BS",
        "BT",
        "BV",
        "BW",
        "BY",
        "BZ",
        "CA",
        "CC",
        "CD",
        "CF",
        "CG",
        "CH",
        "CI",
        "CK",
        "CL",
        "CM",
        "CN",
        "CO",
        "CR",
        "CU",
        "CV",
        "CW",
        "CX",
        "CY",
        "CZ",
        "DE",
        "DJ",
        "DK",
        "DM",
        "DO",
        "DZ",
        "EC",
        "EE",
        "EG",
        "EH",
        "ER",
        "ES",
        "ET",
        "FI",
        "FJ",
        "FK",
        "FM",
        "FO",
        "FR",
        "GA",
        "GB",
        "GD",
        "GE",
        "GF",
        "GG",
        "GH",
        "GI",
        "GL",
        "GM",
        "GN",
        "GP",
        "GQ",
        "GR",
        "GS",
        "GT",
        "GU",
        "GW",
        "GY",
        "HK",
        "HM",
        "HN",
        "HR",
        "HT",
        "HU",
        "ID",
        "IE",
        "IL",
        "IM",
        "IN",
        "IO",
        "IQ",
        "IR",
        "IS",
        "IT",
        "JE",
        "JM",
        "JO",
        "JP",
        "KE",
        "KG",
        "KH",
        "KI",
        "KM",
        "KN",
        "KP",
        "KR",
        "KW",
        "KY",
        "KZ",
        "LA",
        "LB",
        "LC",
        "LI",
        "LK",
        "LR",
        "LS",
        "LT",
        "LU",
        "LV",
        "LY",
        "MA",
        "MC",
        "MD",
        "ME",
        "MF",
        "MG",
        "MH",
        "MK",
        "ML",
        "MM",
        "MN",
        "MO",
        "MP",
        "MQ",
        "MR",
        "MS",
        "MT",
        "MU",
        "MV",
        "MW",
        "MX",
        "MY",
        "MZ",
        "NA",
        "NC",
        "NE",
        "NF",
        "NG",
        "NI",
        "NL",
        "NO",
        "NP",
        "NR",
        "NU",
        "NZ",
        "OM",
        "PA",
        "PE",
        "PF",
        "PG",
        "PH",
        "PK",
        "PL",
        "PM",
        "PN",
        "PR",
        "PS",
        "PT",
        "PW",
        "PY",
        "QA",
        "RE",
        "RO",
        "RS",
        "RU",
        "RW",
        "SA",
        "SB",
        "SC",
        "SD",
        "SE",
        "SG",
        "SH",
        "SI",
        "SJ",
        "SK",
        "SL",
        "SM",
        "SN",
        "SO",
        "SR",
        "SS",
        "ST",
        "SV",
        "SX",
        "SY",
        "SZ",
        "TC",
        "TD",
        "TF",
        "TG",
        "TH",
        "TJ",
        "TK",
        "TL",
        "TM",
        "TN",
        "TO",
        "TR",
        "TT",
        "TV",
        "TW",
        "TZ",
        "UA",
        "UG",
        "UM",
        "US",
        "UY",
        "UZ",
        "VA",
        "VC",
        "VE",
        "VG",
        "VI",
        "VN",
        "VU",
        "WF",
        "WS",
        "YE",
        "YT",
        "ZA",
        "ZM",
        "ZW",
    }
)

# ISO 3166-1:2020 official English short names (upper-cased) -> alpha-2.
# FULL enumeration of all 249 assigned codes (Law 15 — a cited
# named-entity source is adopted in full). Source edition:
# COUNTRY_TABLE_VERSION = "iso3166-1:2020". The canonical ISO
# capitalization is preserved in the trailing comment per line.
# A small set of prior convenience aliases (e.g. "UNITED STATES",
# "SOUTH KOREA", "RUSSIA") is retained below for backward
# compatibility and is a strict subset of the official names' targets.
# Wrapped in MappingProxyType: the bundled lookup table is immutable for the
# lifetime of the process (MANDATE Law 1 — Identity: canonicalize only;
# Law 2 — Determinism: same input + dataset version -> same artifact).
_NAME_TO_ALPHA2: Mapping[str, str] = MappingProxyType(
    {
        "ANDORRA": "AD",  # Andorra
        "UNITED ARAB EMIRATES": "AE",  # United Arab Emirates
        "AFGHANISTAN": "AF",  # Afghanistan
        "ANTIGUA AND BARBUDA": "AG",  # Antigua and Barbuda
        "ANGUILLA": "AI",  # Anguilla
        "ALBANIA": "AL",  # Albania
        "ARMENIA": "AM",  # Armenia
        "ANGOLA": "AO",  # Angola
        "ANTARCTICA": "AQ",  # Antarctica
        "ARGENTINA": "AR",  # Argentina
        "AMERICAN SAMOA": "AS",  # American Samoa
        "AUSTRIA": "AT",  # Austria
        "AUSTRALIA": "AU",  # Australia
        "ARUBA": "AW",  # Aruba
        "ÅLAND ISLANDS": "AX",  # Åland Islands
        "AZERBAIJAN": "AZ",  # Azerbaijan
        "BOSNIA AND HERZEGOVINA": "BA",  # Bosnia and Herzegovina
        "BARBADOS": "BB",  # Barbados
        "BANGLADESH": "BD",  # Bangladesh
        "BELGIUM": "BE",  # Belgium
        "BURKINA FASO": "BF",  # Burkina Faso
        "BULGARIA": "BG",  # Bulgaria
        "BAHRAIN": "BH",  # Bahrain
        "BURUNDI": "BI",  # Burundi
        "BENIN": "BJ",  # Benin
        "SAINT BARTHÉLEMY": "BL",  # Saint Barthélemy
        "BERMUDA": "BM",  # Bermuda
        "BRUNEI DARUSSALAM": "BN",  # Brunei Darussalam
        "BOLIVIA (PLURINATIONAL STATE OF)": "BO",  # Bolivia (Plurinational State of)
        "BONAIRE, SINT EUSTATIUS AND SABA": "BQ",  # Bonaire, Sint Eustatius and Saba
        "BRAZIL": "BR",  # Brazil
        "BAHAMAS": "BS",  # Bahamas
        "BHUTAN": "BT",  # Bhutan
        "BOUVET ISLAND": "BV",  # Bouvet Island
        "BOTSWANA": "BW",  # Botswana
        "BELARUS": "BY",  # Belarus
        "BELIZE": "BZ",  # Belize
        "CANADA": "CA",  # Canada
        "COCOS (KEELING) ISLANDS": "CC",  # Cocos (Keeling) Islands
        "CONGO (DEMOCRATIC REPUBLIC OF THE)": "CD",  # Congo (Democratic Republic of the)
        "CENTRAL AFRICAN REPUBLIC": "CF",  # Central African Republic
        "CONGO": "CG",  # Congo
        "SWITZERLAND": "CH",  # Switzerland
        "CÔTE D'IVOIRE": "CI",  # Côte d'Ivoire
        "COOK ISLANDS": "CK",  # Cook Islands
        "CHILE": "CL",  # Chile
        "CAMEROON": "CM",  # Cameroon
        "CHINA": "CN",  # China
        "COLOMBIA": "CO",  # Colombia
        "COSTA RICA": "CR",  # Costa Rica
        "CUBA": "CU",  # Cuba
        "CABO VERDE": "CV",  # Cabo Verde
        "CURAÇAO": "CW",  # Curaçao
        "CHRISTMAS ISLAND": "CX",  # Christmas Island
        "CYPRUS": "CY",  # Cyprus
        "CZECHIA": "CZ",  # Czechia
        "GERMANY": "DE",  # Germany
        "DJIBOUTI": "DJ",  # Djibouti
        "DENMARK": "DK",  # Denmark
        "DOMINICA": "DM",  # Dominica
        "DOMINICAN REPUBLIC": "DO",  # Dominican Republic
        "ALGERIA": "DZ",  # Algeria
        "ECUADOR": "EC",  # Ecuador
        "ESTONIA": "EE",  # Estonia
        "EGYPT": "EG",  # Egypt
        "WESTERN SAHARA": "EH",  # Western Sahara
        "ERITREA": "ER",  # Eritrea
        "SPAIN": "ES",  # Spain
        "ETHIOPIA": "ET",  # Ethiopia
        "FINLAND": "FI",  # Finland
        "FIJI": "FJ",  # Fiji
        "FALKLAND ISLANDS (MALVINAS)": "FK",  # Falkland Islands (Malvinas)
        "MICRONESIA (FEDERATED STATES OF)": "FM",  # Micronesia (Federated States of)
        "FAROE ISLANDS": "FO",  # Faroe Islands
        "FRANCE": "FR",  # France
        "GABON": "GA",  # Gabon
        "UNITED KINGDOM OF GREAT BRITAIN AND NORTHERN IRELAND": "GB",
        "GRENADA": "GD",  # Grenada
        "GEORGIA": "GE",  # Georgia
        "FRENCH GUIANA": "GF",  # French Guiana
        "GUERNSEY": "GG",  # Guernsey
        "GHANA": "GH",  # Ghana
        "GIBRALTAR": "GI",  # Gibraltar
        "GREENLAND": "GL",  # Greenland
        "GAMBIA": "GM",  # Gambia
        "GUINEA": "GN",  # Guinea
        "GUADELOUPE": "GP",  # Guadeloupe
        "EQUATORIAL GUINEA": "GQ",  # Equatorial Guinea
        "GREECE": "GR",  # Greece
        "SOUTH GEORGIA AND THE SOUTH SANDWICH ISLANDS": "GS",
        "GUATEMALA": "GT",  # Guatemala
        "GUAM": "GU",  # Guam
        "GUINEA-BISSAU": "GW",  # Guinea-Bissau
        "GUYANA": "GY",  # Guyana
        "HONG KONG": "HK",  # Hong Kong
        "HEARD ISLAND AND MCDONALD ISLANDS": "HM",  # Heard Island and McDonald Islands
        "HONDURAS": "HN",  # Honduras
        "CROATIA": "HR",  # Croatia
        "HAITI": "HT",  # Haiti
        "HUNGARY": "HU",  # Hungary
        "INDONESIA": "ID",  # Indonesia
        "IRELAND": "IE",  # Ireland
        "ISRAEL": "IL",  # Israel
        "ISLE OF MAN": "IM",  # Isle of Man
        "INDIA": "IN",  # India
        "BRITISH INDIAN OCEAN TERRITORY": "IO",  # British Indian Ocean Territory
        "IRAQ": "IQ",  # Iraq
        "IRAN (ISLAMIC REPUBLIC OF)": "IR",  # Iran (Islamic Republic of)
        "ICELAND": "IS",  # Iceland
        "ITALY": "IT",  # Italy
        "JERSEY": "JE",  # Jersey
        "JAMAICA": "JM",  # Jamaica
        "JORDAN": "JO",  # Jordan
        "JAPAN": "JP",  # Japan
        "KENYA": "KE",  # Kenya
        "KYRGYZSTAN": "KG",  # Kyrgyzstan
        "CAMBODIA": "KH",  # Cambodia
        "KIRIBATI": "KI",  # Kiribati
        "COMOROS": "KM",  # Comoros
        "SAINT KITTS AND NEVIS": "KN",  # Saint Kitts and Nevis
        "KOREA (DEMOCRATIC PEOPLE'S REPUBLIC OF)": "KP",  # Korea (Democratic People's Republic of)
        "KOREA (REPUBLIC OF)": "KR",  # Korea (Republic of)
        "KUWAIT": "KW",  # Kuwait
        "CAYMAN ISLANDS": "KY",  # Cayman Islands
        "KAZAKHSTAN": "KZ",  # Kazakhstan
        "LAO PEOPLE'S DEMOCRATIC REPUBLIC": "LA",  # Lao People's Democratic Republic
        "LEBANON": "LB",  # Lebanon
        "SAINT LUCIA": "LC",  # Saint Lucia
        "LIECHTENSTEIN": "LI",  # Liechtenstein
        "SRI LANKA": "LK",  # Sri Lanka
        "LIBERIA": "LR",  # Liberia
        "LESOTHO": "LS",  # Lesotho
        "LITHUANIA": "LT",  # Lithuania
        "LUXEMBOURG": "LU",  # Luxembourg
        "LATVIA": "LV",  # Latvia
        "LIBYA": "LY",  # Libya
        "MOROCCO": "MA",  # Morocco
        "MONACO": "MC",  # Monaco
        "MOLDOVA (REPUBLIC OF)": "MD",  # Moldova (Republic of)
        "MONTENEGRO": "ME",  # Montenegro
        "SAINT MARTIN (FRENCH PART)": "MF",  # Saint Martin (French part)
        "MADAGASCAR": "MG",  # Madagascar
        "MARSHALL ISLANDS": "MH",  # Marshall Islands
        "NORTH MACEDONIA": "MK",  # North Macedonia
        "MALI": "ML",  # Mali
        "MYANMAR": "MM",  # Myanmar
        "MONGOLIA": "MN",  # Mongolia
        "MACAO": "MO",  # Macao
        "NORTHERN MARIANA ISLANDS": "MP",  # Northern Mariana Islands
        "MARTINIQUE": "MQ",  # Martinique
        "MAURITANIA": "MR",  # Mauritania
        "MONTSERRAT": "MS",  # Montserrat
        "MALTA": "MT",  # Malta
        "MAURITIUS": "MU",  # Mauritius
        "MALDIVES": "MV",  # Maldives
        "MALAWI": "MW",  # Malawi
        "MEXICO": "MX",  # Mexico
        "MALAYSIA": "MY",  # Malaysia
        "MOZAMBIQUE": "MZ",  # Mozambique
        "NAMIBIA": "NA",  # Namibia
        "NEW CALEDONIA": "NC",  # New Caledonia
        "NIGER": "NE",  # Niger
        "NORFOLK ISLAND": "NF",  # Norfolk Island
        "NIGERIA": "NG",  # Nigeria
        "NICARAGUA": "NI",  # Nicaragua
        "NETHERLANDS": "NL",  # Netherlands
        "NORWAY": "NO",  # Norway
        "NEPAL": "NP",  # Nepal
        "NAURU": "NR",  # Nauru
        "NIUE": "NU",  # Niue
        "NEW ZEALAND": "NZ",  # New Zealand
        "OMAN": "OM",  # Oman
        "PANAMA": "PA",  # Panama
        "PERU": "PE",  # Peru
        "FRENCH POLYNESIA": "PF",  # French Polynesia
        "PAPUA NEW GUINEA": "PG",  # Papua New Guinea
        "PHILIPPINES": "PH",  # Philippines
        "PAKISTAN": "PK",  # Pakistan
        "POLAND": "PL",  # Poland
        "SAINT PIERRE AND MIQUELON": "PM",  # Saint Pierre and Miquelon
        "PITCAIRN": "PN",  # Pitcairn
        "PUERTO RICO": "PR",  # Puerto Rico
        "PALESTINE, STATE OF": "PS",  # Palestine, State of
        "PORTUGAL": "PT",  # Portugal
        "PALAU": "PW",  # Palau
        "PARAGUAY": "PY",  # Paraguay
        "QATAR": "QA",  # Qatar
        "RÉUNION": "RE",  # Réunion
        "ROMANIA": "RO",  # Romania
        "SERBIA": "RS",  # Serbia
        "RUSSIAN FEDERATION": "RU",  # Russian Federation
        "RWANDA": "RW",  # Rwanda
        "SAUDI ARABIA": "SA",  # Saudi Arabia
        "SOLOMON ISLANDS": "SB",  # Solomon Islands
        "SEYCHELLES": "SC",  # Seychelles
        "SUDAN": "SD",  # Sudan
        "SWEDEN": "SE",  # Sweden
        "SINGAPORE": "SG",  # Singapore
        "SAINT HELENA, ASCENSION AND TRISTAN DA CUNHA": "SH",
        "SLOVENIA": "SI",  # Slovenia
        "SVALBARD AND JAN MAYEN": "SJ",  # Svalbard and Jan Mayen
        "SLOVAKIA": "SK",  # Slovakia
        "SIERRA LEONE": "SL",  # Sierra Leone
        "SAN MARINO": "SM",  # San Marino
        "SENEGAL": "SN",  # Senegal
        "SOMALIA": "SO",  # Somalia
        "SURINAME": "SR",  # Suriname
        "SOUTH SUDAN": "SS",  # South Sudan
        "SAO TOME AND PRINCIPE": "ST",  # Sao Tome and Principe
        "EL SALVADOR": "SV",  # El Salvador
        "SINT MAARTEN (DUTCH PART)": "SX",  # Sint Maarten (Dutch part)
        "SYRIAN ARAB REPUBLIC": "SY",  # Syrian Arab Republic
        "ESWATINI": "SZ",  # Eswatini
        "TURKS AND CAICOS ISLANDS": "TC",  # Turks and Caicos Islands
        "CHAD": "TD",  # Chad
        "FRENCH SOUTHERN TERRITORIES": "TF",  # French Southern Territories
        "TOGO": "TG",  # Togo
        "THAILAND": "TH",  # Thailand
        "TAJIKISTAN": "TJ",  # Tajikistan
        "TOKELAU": "TK",  # Tokelau
        "TIMOR-LESTE": "TL",  # Timor-Leste
        "TURKMENISTAN": "TM",  # Turkmenistan
        "TUNISIA": "TN",  # Tunisia
        "TONGA": "TO",  # Tonga
        "TÜRKIYE": "TR",  # Türkiye
        "TRINIDAD AND TOBAGO": "TT",  # Trinidad and Tobago
        "TUVALU": "TV",  # Tuvalu
        "TAIWAN (PROVINCE OF CHINA)": "TW",  # Taiwan (Province of China)
        "TANZANIA, UNITED REPUBLIC OF": "TZ",  # Tanzania, United Republic of
        "UKRAINE": "UA",  # Ukraine
        "UGANDA": "UG",  # Uganda
        "UNITED STATES MINOR OUTLYING ISLANDS": "UM",  # United States Minor Outlying Islands
        "UNITED STATES OF AMERICA": "US",  # United States of America
        "URUGUAY": "UY",  # Uruguay
        "UZBEKISTAN": "UZ",  # Uzbekistan
        "HOLY SEE": "VA",  # Holy See
        "SAINT VINCENT AND THE GRENADINES": "VC",  # Saint Vincent and the Grenadines
        "VENEZUELA (BOLIVARIAN REPUBLIC OF)": "VE",  # Venezuela (Bolivarian Republic of)
        "VIRGIN ISLANDS (BRITISH)": "VG",  # Virgin Islands (British)
        "VIRGIN ISLANDS (U.S.)": "VI",  # Virgin Islands (U.S.)
        "VIET NAM": "VN",  # Viet Nam
        "VANUATU": "VU",  # Vanuatu
        "WALLIS AND FUTUNA": "WF",  # Wallis and Futuna
        "SAMOA": "WS",  # Samoa
        "YEMEN": "YE",  # Yemen
        "MAYOTTE": "YT",  # Mayotte
        "SOUTH AFRICA": "ZA",  # South Africa
        "ZAMBIA": "ZM",  # Zambia
        "ZIMBABWE": "ZW",  # Zimbabwe
        "CZECH REPUBLIC": "CZ",  # prior convenience alias
        "GREAT BRITAIN": "GB",  # prior convenience alias
        "KOREA REPUBLIC": "KR",  # prior convenience alias
        "RUSSIA": "RU",  # prior convenience alias
        "SOUTH KOREA": "KR",  # prior convenience alias
        "UNITED KINGDOM": "GB",  # prior convenience alias
        "UNITED STATES": "US",  # prior convenience alias
    }
)

# Common aliases / synonyms (uppercased) -> alpha-2. UK->GB per BCP 47 §2.
# Finite, versioned alias dataset (Law 8a; spec/country §3.3). Wrapped in
# MappingProxyType (see _NAME_TO_ALPHA2 note above) for runtime immutability.
_SYNONYM_TO_ALPHA2: Mapping[str, str] = MappingProxyType(
    {
        "USA": "US",
        "U.S.A.": "US",
        "U.S.": "US",
        "AMERICA": "US",
        "UK": "GB",
        "ENGLAND": "GB",
        "SCOTLAND": "GB",
        "BRITAIN": "GB",
        "GREAT BRITAIN": "GB",
        "U.K.": "GB",
        "DEUTSCHLAND": "DE",
        # Expanded T2 aliases (finite, well-established).
        "REPUBLIC OF KOREA": "KR",
        "KOREA REPUBLIC": "KR",
        "RUSSIAN FEDERATION": "RU",
        "VIET NAM": "VN",
        "HOLLAND": "NL",
        "THE NETHERLANDS": "NL",
        "CZECH REPUBLIC": "CZ",
        "MACAO": "MO",
        "HONG KONG": "HK",
        "IRAN": "IR",
        "IRAN, ISLAMIC REPUBLIC OF": "IR",
        "SYRIA": "SY",
        "SYRIAN ARAB REPUBLIC": "SY",
        "TANZANIA": "TZ",
        "UNITED REPUBLIC OF TANZANIA": "TZ",
        "LAOS": "LA",
        "MICRONESIA": "FM",
        "FEDERATED STATES OF MICRONESIA": "FM",
        "BOLIVIA": "BO",
        "PLURINATIONAL STATE OF BOLIVIA": "BO",
        "VENEZUELA": "VE",
        "BOLIVARIAN REPUBLIC OF VENEZUELA": "VE",
        "MOLDOVA": "MD",
        "REPUBLIC OF MOLDOVA": "MD",
        "BRUNEI": "BN",
        "BRUNEI DARUSSALAM": "BN",
        "NORTH KOREA": "KP",
        "DPRK": "KP",
        "SOUTH KOREA": "KR",
        "NORTH MACEDONIA": "MK",
        "REPUBLIC OF NORTH MACEDONIA": "MK",
        "CZECHIA": "CZ",
        "SLOVAKIA": "SK",
        "SLOVAK REPUBLIC": "SK",
        "TURKEY": "TR",
        "TÜRKIYE": "TR",
        "REPUBLIC OF TÜRKIYE": "TR",
        "CAPE VERDE": "CV",
        "CABO VERDE": "CV",
        "ESWATINI": "SZ",
    }
)

# ISO 3166-1 numeric -> alpha-2. Numeric codes are official ISO representations,
# zero-padded to 3 digits (e.g. "004" and "4" both denote Afghanistan). Law 8a:
# bundled, versioned dataset (COUNTRY_TABLE_VERSION). Wrapped in MappingProxyType
# (see _NAME_TO_ALPHA2 note above) for runtime immutability.
_NUMERIC_TO_ALPHA2: Mapping[str, str] = MappingProxyType(
    {
        "004": "AF",
        "008": "AL",
        "010": "AQ",
        "012": "DZ",
        "016": "AS",
        "020": "AD",
        "024": "AO",
        "028": "AG",
        "031": "AZ",
        "032": "AR",
        "036": "AU",
        "040": "AT",
        "044": "BS",
        "048": "BH",
        "050": "BD",
        "051": "AM",
        "052": "BB",
        "056": "BE",
        "060": "BM",
        "064": "BT",
        "068": "BO",
        "070": "BA",
        "072": "BW",
        "074": "BV",
        "076": "BR",
        "084": "BZ",
        "086": "IO",
        "090": "SB",
        "092": "VG",
        "096": "BN",
        "100": "BG",
        "104": "MM",
        "108": "BI",
        "112": "BY",
        "116": "KH",
        "120": "CM",
        "124": "CA",
        "132": "CV",
        "136": "KY",
        "140": "CF",
        "144": "LK",
        "148": "TD",
        "152": "CL",
        "156": "CN",
        "158": "TW",
        "162": "CX",
        "166": "CC",
        "170": "CO",
        "174": "KM",
        "175": "YT",
        "178": "CG",
        "180": "CD",
        "184": "CK",
        "188": "CR",
        "191": "HR",
        "192": "CU",
        "196": "CY",
        "203": "CZ",
        "204": "BJ",
        "208": "DK",
        "212": "DM",
        "214": "DO",
        "218": "EC",
        "222": "SV",
        "226": "GQ",
        "231": "ET",
        "232": "ER",
        "233": "EE",
        "234": "FO",
        "238": "FK",
        "239": "GS",
        "242": "FJ",
        "246": "FI",
        "248": "AX",
        "250": "FR",
        "254": "GF",
        "258": "PF",
        "260": "TF",
        "262": "DJ",
        "266": "GA",
        "268": "GE",
        "270": "GM",
        "275": "PS",
        "276": "DE",
        "288": "GH",
        "292": "GI",
        "296": "KI",
        "300": "GR",
        "304": "GL",
        "308": "GD",
        "312": "GP",
        "316": "GU",
        "320": "GT",
        "324": "GN",
        "328": "GY",
        "332": "HT",
        "334": "HM",
        "336": "VA",
        "340": "HN",
        "344": "HK",
        "348": "HU",
        "352": "IS",
        "356": "IN",
        "360": "ID",
        "364": "IR",
        "368": "IQ",
        "372": "IE",
        "376": "IL",
        "380": "IT",
        "384": "CI",
        "388": "JM",
        "392": "JP",
        "398": "KZ",
        "400": "JO",
        "404": "KE",
        "408": "KP",
        "410": "KR",
        "414": "KW",
        "417": "KG",
        "418": "LA",
        "422": "LB",
        "426": "LS",
        "428": "LV",
        "430": "LR",
        "434": "LY",
        "438": "LI",
        "440": "LT",
        "442": "LU",
        "446": "MO",
        "450": "MG",
        "454": "MW",
        "458": "MY",
        "462": "MV",
        "466": "ML",
        "470": "MT",
        "474": "MQ",
        "478": "MR",
        "480": "MU",
        "484": "MX",
        "492": "MC",
        "496": "MN",
        "498": "MD",
        "499": "ME",
        "500": "MS",
        "504": "MA",
        "508": "MZ",
        "512": "OM",
        "516": "NA",
        "520": "NR",
        "524": "NP",
        "528": "NL",
        "531": "CW",
        "533": "AW",
        "534": "SX",
        "535": "BQ",
        "540": "NC",
        "548": "VU",
        "554": "NZ",
        "558": "NI",
        "562": "NE",
        "566": "NG",
        "570": "NU",
        "574": "NF",
        "578": "NO",
        "580": "MP",
        "581": "UM",
        "583": "FM",
        "584": "MH",
        "585": "PW",
        "586": "PK",
        "591": "PA",
        "598": "PG",
        "600": "PY",
        "604": "PE",
        "608": "PH",
        "612": "PN",
        "616": "PL",
        "620": "PT",
        "624": "GW",
        "626": "TL",
        "630": "PR",
        "634": "QA",
        "638": "RE",
        "642": "RO",
        "643": "RU",
        "646": "RW",
        "652": "BL",
        "654": "SH",
        "659": "KN",
        "660": "AI",
        "662": "LC",
        "663": "MF",
        "666": "PM",
        "670": "VC",
        "674": "SM",
        "678": "ST",
        "682": "SA",
        "686": "SN",
        "688": "RS",
        "690": "SC",
        "694": "SL",
        "702": "SG",
        "703": "SK",
        "704": "VN",
        "705": "SI",
        "706": "SO",
        "710": "ZA",
        "716": "ZW",
        "724": "ES",
        "728": "SS",
        "732": "EH",
        "736": "SD",
        "740": "SR",
        "744": "SJ",
        "748": "SZ",
        "752": "SE",
        "756": "CH",
        "760": "SY",
        "762": "TJ",
        "764": "TH",
        "768": "TG",
        "772": "TK",
        "776": "TO",
        "780": "TT",
        "784": "AE",
        "788": "TN",
        "792": "TR",
        "795": "TM",
        "796": "TC",
        "798": "TV",
        "800": "UG",
        "804": "UA",
        "807": "MK",
        "818": "EG",
        "826": "GB",
        "831": "GG",
        "832": "JE",
        "833": "IM",
        "834": "TZ",
        "840": "US",
        "850": "VI",
        "854": "BF",
        "858": "UY",
        "860": "UZ",
        "862": "VE",
        "876": "WF",
        "882": "WS",
        "887": "YE",
        "894": "ZM",
    }
)
