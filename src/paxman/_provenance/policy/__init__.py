"""Paxman policy authorities (kind="policy", internally versioned).

Each capability's *resolution policy* (the deterministic decision rules
Paxman applies, distinct from the external grammar it cites) is recorded as a
`policy` authority versioned to the Paxman release that introduced it. These
participate in provenance + replay but are NOT specification/data-set
authorities, so they do not enter the VersionStamp spec/registry maps.
"""

from __future__ import annotations

from paxman._provenance.authority import Authority

#: The current paxman capability-version stamp used for policy authorities.
PAXMAN_VERSION = "0.0.0.dev0"

MANDATE: Authority = Authority(name="MANDATE.md", edition=PAXMAN_VERSION, kind="policy")

PAXMAN_SPEC_EMAIL: Authority = Authority(
    name="paxman spec/email", edition=PAXMAN_VERSION, kind="policy"
)
PAXMAN_SPEC_DATE: Authority = Authority(
    name="paxman spec/date", edition=PAXMAN_VERSION, kind="policy"
)
PAXMAN_SPEC_MONEY: Authority = Authority(
    name="paxman spec/money", edition=PAXMAN_VERSION, kind="policy"
)
PAXMAN_SPEC_PHONE: Authority = Authority(
    name="paxman spec/phone", edition=PAXMAN_VERSION, kind="policy"
)
PAXMAN_SPEC_URL: Authority = Authority(
    name="paxman spec/url", edition=PAXMAN_VERSION, kind="policy"
)
PAXMAN_SPEC_IP: Authority = Authority(name="paxman spec/ip", edition=PAXMAN_VERSION, kind="policy")
PAXMAN_SPEC_GEOLOCATION: Authority = Authority(
    name="paxman spec/geolocation", edition=PAXMAN_VERSION, kind="policy"
)
PAXMAN_SPEC_BOOLEAN: Authority = Authority(
    name="paxman spec/boolean", edition=PAXMAN_VERSION, kind="policy"
)
PAXMAN_SPEC_COUNTRY: Authority = Authority(
    name="paxman spec/country", edition=PAXMAN_VERSION, kind="policy"
)

__all__ = [
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
]
