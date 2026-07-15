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
    behavior, or a declared Paxman policy. A small set of routing/
    dispatch failures are allow-listed with empty `provenance` because
    they describe a routing failure, not a canonical-form rule
    (Law 14 §3.6):
      - capability dispatch invariants (declared in each domain's
        `rules.py`): `not_a_date_contract`, `not_a_string_value`,
        `empty_value`, `unrecognized_format`, `not_an_email_contract`,
        `not_a_uuid_contract`;
      - orchestrator routing failures (emitted by `engine.py`):
        `unparseable_contract`, `no_capability_claims`,
        `multiple_claimants`, `validation_unsupported_contract`.
    Every other fired rule MUST carry a non-empty citation.
    """

    rule: str
    detail: str = ""
    provenance: str = ""
