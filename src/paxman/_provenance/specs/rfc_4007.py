"""RFC 4007 grammar authority (kind="grammar", single edition)."""

from __future__ import annotations

from paxman._errors import UnknownAuthorityEdition
from paxman._provenance.authority import Authority

# RFC/ISO grammar authorities are compiled into the capability algorithm;
# they carry a single edition and do not support runtime edition selection.
RFC_4007 = Authority(
    name="RFC 4007",
    kind="grammar",
    edition="RFC 4007 (IPv6 Scoped Addresses)",
    supports_multiple_editions=False,
)


_EDITIONS: dict[str, Authority] = {"RFC 4007 (IPv6 Scoped Addresses)": RFC_4007}


def latest() -> Authority:
    """Return the (single) grammar edition."""
    return RFC_4007


def edition(edition_id: str) -> Authority:
    """Return a specific edition; grammar authorities reject selection."""
    if edition_id != "RFC 4007 (IPv6 Scoped Addresses)":
        raise UnknownAuthorityEdition(
            f"RFC 4007 is a grammar authority with a single edition "
            f"'RFC 4007 (IPv6 Scoped Addresses)'; requested edition {edition_id!r} is not valid."
        )
    return RFC_4007


__all__ = ["RFC_4007", "edition", "latest"]
