"""Central registry of cited authorities — the single source of truth.

Every externally-maintained standard or data-set Paxman cites is declared
**once** here, not re-stringified in each capability's ``rules.py``. A
standard cited by several capabilities (RFC 5321 by email; ISO 3166 by
country + phone-adjacent) is declared a single time and imported wherever
it is needed.

Updating a bundled edition (ISO 3166:2020 → :2024) is one edit in one
place, propagating to every citing capability (mandate Law 14, Principle
4). The registry holds **citation metadata** (which authority exists,
which edition), not domain knowledge (how to parse email) — capabilities
keep their grammars, tables, and rule logic.

The frozen edition strings are constants, never runtime lookups (mandate
Law 1). ``Authority`` is frozen (mandate Law 13).
"""

from __future__ import annotations

from paxman._provenance.authority import Authority

# ---------------------------------------------------------------------------
# Specifications (externally maintained documents/standards)
# ---------------------------------------------------------------------------
RFC_5321: Authority = Authority("RFC 5321", "RFC 5321 (SMTP)", "specification")
RFC_5322: Authority = Authority("RFC 5322", "RFC 5322 (Internet Message Format)", "specification")
RFC_3966: Authority = Authority("RFC 3966", "RFC 3966 (tel URI)", "specification")
RFC_4122: Authority = Authority("RFC 4122", "RFC 4122 (UUID)", "specification")
RFC_4291: Authority = Authority("RFC 4291", "RFC 4291 (IP Version 6 Addressing)", "specification")
RFC_5952: Authority = Authority("RFC 5952", "RFC 5952 (IPv6 Text Representation)", "specification")
RFC_4007: Authority = Authority("RFC 4007", "RFC 4007 (IPv6 Scoped Addresses)", "specification")
RFC_3986: Authority = Authority("RFC 3986", "RFC 3986 (URI Generic Syntax)", "specification")
RFC_3339: Authority = Authority("RFC 3339", "RFC 3339 (Date/Time on Internet)", "specification")
RFC_2822: Authority = Authority("RFC 2822", "RFC 2822 (Internet Message Format)", "specification")
RFC_1035: Authority = Authority("RFC 1035", "RFC 1035 (Domain Names)", "specification")
ISO_8601: Authority = Authority("ISO 8601", "iso8601:2004", "specification")
IEEE_1003_1: Authority = Authority(
    "POSIX/IEEE 1003.1",
    "IEEE Std 1003.1 (epoch seconds)",
    "specification",
)

# ---------------------------------------------------------------------------
# Data-sets (externally maintained data-sets, pinned to the bundled edition)
# ---------------------------------------------------------------------------
ISO_3166: Authority = Authority("ISO 3166-1", "iso3166-1:2020", "data-set")
ISO_4217: Authority = Authority("ISO 4217", "iso4217:2015", "data-set")
CLDR: Authority = Authority("Unicode CLDR", "cldr-45", "data-set")
ITU_E164: Authority = Authority("ITU-T E.164", "ITU-T E.164", "data-set")

# ---------------------------------------------------------------------------
# Platform behavior (documented platform behavior; carries retrieved_at)
# ---------------------------------------------------------------------------
GOOGLE_HELP: Authority = Authority(
    "Google Help",
    "Google Help (Gmail addressing)",
    "platform-behaviour",
    retrieved_at="2026-07-14",
)
# The WHATWG URL Standard is tracked as a pinned snapshot: the `retrieved_at`
# date records when the bundled edition was captured. A single symbol (no
# separate base/“pinned” alias) keeps the registry name-collision-free and
# gives URL artifacts a stable, replay-verifiable authority edition.
WHATWG_URL: Authority = Authority(
    "WHATWG URL",
    "WHATWG URL Standard",
    "platform-behaviour",
    retrieved_at="2026-07-16",
)

# ---------------------------------------------------------------------------
# Paxman policy authorities (internally versioned to the introducing release)
# ---------------------------------------------------------------------------
#: The current paxman capability-version stamp used for policy authorities.
PAXMAN_VERSION = "0.0.0.dev0"

PAXMAN_SPEC_EMAIL = Authority("paxman spec/email", PAXMAN_VERSION, "policy")
PAXMAN_SPEC_DATE = Authority("paxman spec/date", PAXMAN_VERSION, "policy")
PAXMAN_SPEC_MONEY = Authority("paxman spec/money", PAXMAN_VERSION, "policy")
PAXMAN_SPEC_PHONE = Authority("paxman spec/phone", PAXMAN_VERSION, "policy")
PAXMAN_SPEC_URL = Authority("paxman spec/url", PAXMAN_VERSION, "policy")
PAXMAN_SPEC_IP = Authority("paxman spec/ip", PAXMAN_VERSION, "policy")
PAXMAN_SPEC_GEOLOCATION = Authority("paxman spec/geolocation", PAXMAN_VERSION, "policy")
PAXMAN_SPEC_BOOLEAN = Authority("paxman spec/boolean", PAXMAN_VERSION, "policy")
PAXMAN_SPEC_COUNTRY = Authority("paxman spec/country", PAXMAN_VERSION, "policy")
MANDATE = Authority("MANDATE.md", PAXMAN_VERSION, "policy")


def current_spec_versions() -> dict[str, str]:
    """The editions of every specification authority Paxman currently bundles.

    Used at replay time to detect a stale authority. Only the authorities an
    artifact's own evidence cited are compared (mandate Law 12 — the
    artifact's production context, not the global registry).
    """
    return {a.name: a.edition for a in _ALL_AUTHORITIES if a.kind == "specification"}


def current_registry_versions() -> dict[str, str]:
    """The editions of every data-set authority Paxman currently bundles.

    See :func:`current_spec_versions` for the Law 12 rationale.
    """
    return {a.name: a.edition for a in _ALL_AUTHORITIES if a.kind == "data-set"}


#: Every authority declared in this module, in declaration order. Used to
#: derive the current-edition maps above without re-listing each name.
_ALL_AUTHORITIES: tuple[Authority, ...] = (
    RFC_5321,
    RFC_5322,
    RFC_3966,
    RFC_4122,
    RFC_4291,
    RFC_5952,
    RFC_4007,
    RFC_3986,
    RFC_3339,
    RFC_2822,
    RFC_1035,
    ISO_8601,
    WHATWG_URL,
    IEEE_1003_1,
    ISO_3166,
    ISO_4217,
    CLDR,
    ITU_E164,
    GOOGLE_HELP,
    PAXMAN_SPEC_EMAIL,
    PAXMAN_SPEC_DATE,
    PAXMAN_SPEC_MONEY,
    PAXMAN_SPEC_PHONE,
    PAXMAN_SPEC_URL,
    PAXMAN_SPEC_IP,
    PAXMAN_SPEC_GEOLOCATION,
    PAXMAN_SPEC_BOOLEAN,
    PAXMAN_SPEC_COUNTRY,
    MANDATE,
)

__all__ = [
    "CLDR",
    "GOOGLE_HELP",
    "IEEE_1003_1",
    "ISO_3166",
    "ISO_4217",
    "ISO_8601",
    "ITU_E164",
    "MANDATE",
    "PAXMAN_SPEC_BOOLEAN",
    "PAXMAN_SPEC_COUNTRY",
    "PAXMAN_SPEC_DATE",
    "PAXMAN_SPEC_EMAIL",
    "PAXMAN_SPEC_GEOLOCATION",
    "PAXMAN_SPEC_IP",
    "PAXMAN_SPEC_MONEY",
    "PAXMAN_SPEC_PHONE",
    "PAXMAN_SPEC_URL",
    "PAXMAN_VERSION",
    "RFC_1035",
    "RFC_2822",
    "RFC_3339",
    "RFC_3966",
    "RFC_3986",
    "RFC_4007",
    "RFC_4122",
    "RFC_4291",
    "RFC_5321",
    "RFC_5322",
    "RFC_5952",
    "WHATWG_URL",
]
