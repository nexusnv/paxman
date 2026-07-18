"""RFC 3339 grammar authority (kind="grammar", single edition)."""

from __future__ import annotations

from paxman._errors import UnknownAuthorityEdition
from paxman._provenance.authority import Authority

# RFC/ISO grammar authorities are compiled into the capability algorithm;
# they carry a single edition and do not support runtime edition selection.
RFC_3339 = Authority(
    name="RFC 3339",
    kind="grammar",
    edition="RFC 3339 (Date/Time on Internet)",
    supports_multiple_editions=False,
)


_EDITIONS: dict[str, Authority] = {"RFC 3339 (Date/Time on Internet)": RFC_3339}


def latest() -> Authority:
    """Return the (single) grammar edition."""
    return RFC_3339


def edition(edition_id: str) -> Authority:
    """Return a specific edition; grammar authorities reject selection."""
    if edition_id != "RFC 3339 (Date/Time on Internet)":
        raise UnknownAuthorityEdition(
            f"RFC 3339 is a grammar authority with a single edition "
            f"'RFC 3339 (Date/Time on Internet)'; requested edition {edition_id!r} is not valid."
        )
    return RFC_3339


__all__ = ["RFC_3339", "edition", "latest"]
