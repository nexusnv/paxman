"""RFC 4122 grammar authority (kind="grammar", single edition)."""

from __future__ import annotations

from paxman._errors import UnknownAuthorityEdition
from paxman._provenance.authority import Authority

# RFC/ISO grammar authorities are compiled into the capability algorithm;
# they carry a single edition and do not support runtime edition selection.
RFC_4122 = Authority(
    name="RFC 4122",
    kind="grammar",
    edition="RFC 4122 (UUID)",
    supports_multiple_editions=False,
)


_EDITIONS: dict[str, Authority] = {"RFC 4122 (UUID)": RFC_4122}


def latest() -> Authority:
    """Return the (single) grammar edition."""
    return RFC_4122


def edition(edition_id: str) -> Authority:
    """Return a specific edition; grammar authorities reject selection."""
    if edition_id != "RFC 4122 (UUID)":
        raise UnknownAuthorityEdition(
            f"RFC 4122 is a grammar authority with a single edition "
            f"'RFC 4122 (UUID)'; requested edition {edition_id!r} is not valid."
        )
    return RFC_4122


__all__ = ["RFC_4122", "edition", "latest"]
