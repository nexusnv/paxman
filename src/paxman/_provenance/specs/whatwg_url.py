"""WHATWG URL grammar authority (kind="grammar", single edition)."""

from __future__ import annotations

from paxman._errors import UnknownAuthorityEdition
from paxman._provenance.authority import Authority

# RFC/ISO grammar authorities are compiled into the capability algorithm;
# they carry a single edition and do not support runtime edition selection.
WHATWG_URL = Authority(
    name="WHATWG URL",
    kind="grammar",
    edition="WHATWG URL Standard (snapshotted 2026-07-16)",
    supports_multiple_editions=False,
)


_EDITIONS: dict[str, Authority] = {"WHATWG URL Standard (snapshotted 2026-07-16)": WHATWG_URL}


def latest() -> Authority:
    """Return the (single) grammar edition."""
    return WHATWG_URL


def edition(edition_id: str) -> Authority:
    """Return a specific edition; grammar authorities reject selection."""
    if edition_id != "WHATWG URL Standard (snapshotted 2026-07-16)":
        raise UnknownAuthorityEdition(
            f"Whatwg URL is a grammar authority with a single edition "
            f"'Whatwg URL Standard (snapshotted 2026-07-16)'; "
            f"requested edition {edition_id!r} is not valid."
        )
    return WHATWG_URL


__all__ = ["WHATWG_URL", "edition", "latest"]
