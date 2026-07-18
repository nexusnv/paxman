"""Google Help platform-behaviour authority (kind="platform-behaviour").

Documented Gmail addressing behavior. Carries a `retrieved_at` snapshot.
"""

from __future__ import annotations

from paxman._provenance.authority import Authority

GOOGLE_HELP: Authority = Authority(
    name="Google Help",
    edition="Google Help (Gmail addressing)",
    kind="platform-behaviour",
    publisher="Google",
    released_on="2026-07-14",
    lifecycle="active",
    retrieved_at="2026-07-14",
    supports_multiple_editions=False,
    dataset=None,
    checksum="google-help-gmail",
)

__all__ = ["GOOGLE_HELP"]
