"""RFC 1035 grammar authority (kind="grammar", single edition)."""

from __future__ import annotations

from paxman._errors import UnknownAuthorityEdition
from paxman._provenance.authority import Authority

# RFC/ISO grammar authorities are compiled into the capability algorithm;
# they carry a single edition and do not support runtime edition selection.
RFC_1035 = Authority(
    name="RFC 1035",
    kind="grammar",
    edition="RFC 1035 (Domain Names)",
    supports_multiple_editions=False,
)


_EDITIONS: dict[str, Authority] = {"RFC 1035 (Domain Names)": RFC_1035}


def latest() -> Authority:
    """Return the (single) grammar edition."""
    return RFC_1035


def edition(edition_id: str) -> Authority:
    """Return a specific edition; grammar authorities reject selection."""
    if edition_id != "RFC 1035 (Domain Names)":
        raise UnknownAuthorityEdition(
            f"RFC 1035 is a grammar authority with a single edition "
            f"'RFC 1035 (Domain Names)'; requested edition {edition_id!r} is not valid."
        )
    return RFC_1035


__all__ = ["RFC_1035", "edition", "latest"]
