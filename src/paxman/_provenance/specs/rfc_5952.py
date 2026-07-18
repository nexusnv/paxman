"""RFC 5952 grammar authority (kind="grammar", single edition)."""

from __future__ import annotations

from paxman._errors import UnknownAuthorityEdition
from paxman._provenance.authority import Authority

# RFC/ISO grammar authorities are compiled into the capability algorithm;
# they carry a single edition and do not support runtime edition selection.
RFC_5952 = Authority(
    name="RFC 5952",
    kind="grammar",
    edition="RFC 5952 (IPv6 Text Representation)",
    supports_multiple_editions=False,
)


_EDITIONS: dict[str, Authority] = {"RFC 5952 (IPv6 Text Representation)": RFC_5952}


def latest() -> Authority:
    """Return the (single) grammar edition."""
    return RFC_5952


def edition(edition_id: str) -> Authority:
    """Return a specific edition; grammar authorities reject selection."""
    if edition_id != "RFC 5952 (IPv6 Text Representation)":
        raise UnknownAuthorityEdition(
            f"RFC 5952 is a grammar authority with a single edition "
            f"'RFC 5952 (IPv6 Text Representation)'; requested edition {edition_id!r} is not valid."
        )
    return RFC_5952


__all__ = ["RFC_5952", "edition", "latest"]
