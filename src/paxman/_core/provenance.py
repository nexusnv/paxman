"""Provenance / evidence record for Paxman v2."""

from __future__ import annotations

import attrs


@attrs.frozen
class Evidence:
    """One entry on an ExecutionArtifact's evidence list (mandate Law 9).

    Each entry records **what matched and why** (mandate Law 9) plus
    **where the canonical form came from** (mandate Law 14). The
    `provenance` field carries a human-readable citation to one of the
    three Law 14 sources: an authoritative spec, a documented platform
    behavior, or a declared Paxman policy. Two dispatch-invariant rules
    (`not_an_email_contract`, `not_a_string_value`) are allow-listed
    with empty `provenance` because they describe a routing failure,
    not a canonical-form rule (see `docs/superpowers/specs/
    2026-07-13-email-canonicalization-design.md` §7.2).
    """

    rule: str
    detail: str = ""
    provenance: str = ""
