from __future__ import annotations

from collections.abc import Mapping

# Paxman policy (not RFC 3986 §3.2.3, which only defines the syntax, not the
# values): the well-known default port for each scheme, drawn from the IANA
# Service Name and Transport Protocol Port Number Registry. Used only to *elide*
# a port equal to the default (Law 3 — never guess: an unknown scheme yields
# None, so an explicit port is treated as non-default rather than invented).
# Mandate laws touched: Law 1 (deterministic lookup), Law 3 (no guessing on
# unknown schemes), Law 14 (provenance: IANA registry, cited here).
_SCHEME_TO_DEFAULT_PORT: Mapping[str, int] = {
    "http": 80,
    "https": 443,
    "ftp": 21,
    "ftps": 990,
    "ws": 80,
    "wss": 443,
    "ntp": 123,
    "ldap": 389,
    "ldaps": 636,
    "telnet": 23,
    "smtp": 25,
    "pop": 110,
    "imap": 143,
    "rtsp": 554,
    "sftp": 22,
}


def default_port_for_scheme(scheme: str) -> int | None:
    """Return the Paxman-policy default port for a scheme, else None.

    The values come from the IANA Service Name and Transport Protocol Port
    Number Registry (Paxman policy, not an RFC 3986 mandate). Lookup is
    case-insensitive. Unknown schemes return None so the resolver treats an
    explicit port as non-default (never guessed — Law 3).
    """
    return _SCHEME_TO_DEFAULT_PORT.get(scheme.lower())
