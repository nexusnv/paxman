"""Specification (grammar) authorities — kind="grammar", single edition each.

Each sub-module declares one grammar authority (RFC/ISO standards compiled
into the capability algorithm). The aggregate here re-exports the module-level
constant names so `from paxman._provenance.specs import RFC_5321` works, and the
legacy `registries` package re-exports them under the same names.

It also exposes :data:`_SPEC_RESOLVERS` — a ``name -> (latest, edition)`` map
used by the Engine to resolve a requested edition for a grammar authority.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import NamedTuple

from paxman._provenance.authority import Authority
from paxman._provenance.specs.ieee_1003_1 import IEEE_1003_1
from paxman._provenance.specs.ieee_1003_1 import edition as ieee_1003_1_edition
from paxman._provenance.specs.ieee_1003_1 import latest as ieee_1003_1_latest
from paxman._provenance.specs.iso_8601 import ISO_8601
from paxman._provenance.specs.iso_8601 import edition as iso_8601_edition
from paxman._provenance.specs.iso_8601 import latest as iso_8601_latest
from paxman._provenance.specs.rfc_1035 import RFC_1035
from paxman._provenance.specs.rfc_1035 import edition as rfc_1035_edition
from paxman._provenance.specs.rfc_1035 import latest as rfc_1035_latest
from paxman._provenance.specs.rfc_2822 import RFC_2822
from paxman._provenance.specs.rfc_2822 import edition as rfc_2822_edition
from paxman._provenance.specs.rfc_2822 import latest as rfc_2822_latest
from paxman._provenance.specs.rfc_3339 import RFC_3339
from paxman._provenance.specs.rfc_3339 import edition as rfc_3339_edition
from paxman._provenance.specs.rfc_3339 import latest as rfc_3339_latest
from paxman._provenance.specs.rfc_3966 import RFC_3966
from paxman._provenance.specs.rfc_3966 import edition as rfc_3966_edition
from paxman._provenance.specs.rfc_3966 import latest as rfc_3966_latest
from paxman._provenance.specs.rfc_3986 import RFC_3986
from paxman._provenance.specs.rfc_3986 import edition as rfc_3986_edition
from paxman._provenance.specs.rfc_3986 import latest as rfc_3986_latest
from paxman._provenance.specs.rfc_4007 import RFC_4007
from paxman._provenance.specs.rfc_4007 import edition as rfc_4007_edition
from paxman._provenance.specs.rfc_4007 import latest as rfc_4007_latest
from paxman._provenance.specs.rfc_4122 import RFC_4122
from paxman._provenance.specs.rfc_4122 import edition as rfc_4122_edition
from paxman._provenance.specs.rfc_4122 import latest as rfc_4122_latest
from paxman._provenance.specs.rfc_4291 import RFC_4291
from paxman._provenance.specs.rfc_4291 import edition as rfc_4291_edition
from paxman._provenance.specs.rfc_4291 import latest as rfc_4291_latest
from paxman._provenance.specs.rfc_5321 import RFC_5321
from paxman._provenance.specs.rfc_5321 import edition as rfc_5321_edition
from paxman._provenance.specs.rfc_5321 import latest as rfc_5321_latest
from paxman._provenance.specs.rfc_5322 import RFC_5322
from paxman._provenance.specs.rfc_5322 import edition as rfc_5322_edition
from paxman._provenance.specs.rfc_5322 import latest as rfc_5322_latest
from paxman._provenance.specs.rfc_5952 import RFC_5952
from paxman._provenance.specs.rfc_5952 import edition as rfc_5952_edition
from paxman._provenance.specs.rfc_5952 import latest as rfc_5952_latest
from paxman._provenance.specs.whatwg_url import WHATWG_URL
from paxman._provenance.specs.whatwg_url import edition as whatwg_url_edition
from paxman._provenance.specs.whatwg_url import latest as whatwg_url_latest


class _SpecResolver(NamedTuple):
    """Resolution helpers for one grammar authority."""

    latest: Callable[[], Authority]
    edition: Callable[[str], Authority]


#: name -> resolver, for the Engine to resolve requested editions.
_SPEC_RESOLVERS: dict[str, _SpecResolver] = {
    "RFC 5321": _SpecResolver(rfc_5321_latest, rfc_5321_edition),
    "RFC 5322": _SpecResolver(rfc_5322_latest, rfc_5322_edition),
    "RFC 3966": _SpecResolver(rfc_3966_latest, rfc_3966_edition),
    "RFC 4122": _SpecResolver(rfc_4122_latest, rfc_4122_edition),
    "RFC 4291": _SpecResolver(rfc_4291_latest, rfc_4291_edition),
    "RFC 5952": _SpecResolver(rfc_5952_latest, rfc_5952_edition),
    "RFC 4007": _SpecResolver(rfc_4007_latest, rfc_4007_edition),
    "RFC 3986": _SpecResolver(rfc_3986_latest, rfc_3986_edition),
    "RFC 3339": _SpecResolver(rfc_3339_latest, rfc_3339_edition),
    "RFC 2822": _SpecResolver(rfc_2822_latest, rfc_2822_edition),
    "RFC 1035": _SpecResolver(rfc_1035_latest, rfc_1035_edition),
    "ISO 8601": _SpecResolver(iso_8601_latest, iso_8601_edition),
    "IEEE 1003.1": _SpecResolver(ieee_1003_1_latest, ieee_1003_1_edition),
    "WHATWG URL": _SpecResolver(whatwg_url_latest, whatwg_url_edition),
}

#: Every grammar authority, in declaration order. Used to build the engine's
#: default authority map.
_ALL_SPEC_AUTHORITIES: tuple = (
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
    IEEE_1003_1,
    WHATWG_URL,
)

__all__ = [
    "IEEE_1003_1",
    "ISO_8601",
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
    "_ALL_SPEC_AUTHORITIES",
    "_SPEC_RESOLVERS",
]
