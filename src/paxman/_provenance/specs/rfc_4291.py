"""RFC 4291 grammar authority (kind="grammar", single edition)."""

from __future__ import annotations

from paxman._errors import UnknownAuthorityEdition
from paxman._provenance.authority import Authority

# RFC/ISO grammar authorities are compiled into the capability algorithm;
# they carry a single edition and do not support runtime edition selection.
RFC_4291 = Authority(
    name="RFC 4291",
    kind="grammar",
    edition="RFC 4291 (IP Version 6 Addressing)",
    supports_multiple_editions=False,
)


_EDITIONS: dict[str, Authority] = {"RFC 4291 (IP Version 6 Addressing)": RFC_4291}


def latest() -> Authority:
    """Return the (single) grammar edition."""
    return RFC_4291


def edition(edition_id: str) -> Authority:
    """Return a specific edition; grammar authorities reject selection."""
    if edition_id != "RFC 4291 (IP Version 6 Addressing)":
        raise UnknownAuthorityEdition(
            f"RFC 4291 is a grammar authority with a single edition "
            f"'RFC 4291 (IP Version 6 Addressing)'; requested edition {edition_id!r} is not valid."
        )
    return RFC_4291


__all__ = ["RFC_4291", "edition", "latest"]
