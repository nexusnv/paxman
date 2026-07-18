"""POSIX/IEEE 1003.1 grammar authority (kind="grammar", single edition)."""

from __future__ import annotations

from paxman._errors import UnknownAuthorityEdition
from paxman._provenance.authority import Authority

# RFC/ISO grammar authorities are compiled into the capability algorithm;
# they carry a single edition and do not support runtime edition selection.
IEEE_1003_1 = Authority(
    name="POSIX/IEEE 1003.1",
    kind="grammar",
    edition="IEEE Std 1003.1 (epoch seconds)",
    supports_multiple_editions=False,
)


_EDITIONS: dict[str, Authority] = {"IEEE Std 1003.1 (epoch seconds)": IEEE_1003_1}


def latest() -> Authority:
    """Return the (single) grammar edition."""
    return IEEE_1003_1


def edition(edition_id: str) -> Authority:
    """Return a specific edition; grammar authorities reject selection."""
    if edition_id != "IEEE Std 1003.1 (epoch seconds)":
        raise UnknownAuthorityEdition(
            f"POSIX/IEEE 1003.1 is a grammar authority with a single edition "
            f"'IEEE Std 1003.1 (epoch seconds)'; requested edition {edition_id!r} is not valid."
        )
    return IEEE_1003_1


__all__ = ["IEEE_1003_1", "edition", "latest"]
