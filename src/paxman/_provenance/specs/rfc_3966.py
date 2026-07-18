"""RFC 3966 grammar authority (kind="grammar", single edition)."""

from __future__ import annotations

from paxman._errors import UnknownAuthorityEdition
from paxman._provenance.authority import Authority

# RFC/ISO grammar authorities are compiled into the capability algorithm;
# they carry a single edition and do not support runtime edition selection.
RFC_3966 = Authority(
    name="RFC 3966",
    kind="grammar",
    edition="RFC 3966 (tel URI)",
    supports_multiple_editions=False,
)


_EDITIONS: dict[str, Authority] = {"RFC 3966 (tel URI)": RFC_3966}


def latest() -> Authority:
    """Return the (single) grammar edition."""
    return RFC_3966


def edition(edition_id: str) -> Authority:
    """Return a specific edition; grammar authorities reject selection."""
    if edition_id != "RFC 3966 (tel URI)":
        raise UnknownAuthorityEdition(
            f"RFC 3966 is a grammar authority with a single edition "
            f"'RFC 3966 (tel URI)'; requested edition {edition_id!r} is not valid."
        )
    return RFC_3966


__all__ = ["RFC_3966", "edition", "latest"]
