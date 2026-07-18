"""The `Evidence` record and the shared `_evidence` helper (mandate Law 9 + 14)."""

from __future__ import annotations

from collections.abc import Mapping

import attrs

from paxman._provenance.authority import Authority

_authority_validator = attrs.validators.optional(attrs.validators.instance_of(Authority))


@attrs.frozen
class Evidence:
    """One entry on an ExecutionArtifact's evidence list (mandate Law 9).

    Each entry records **what matched and why** (mandate Law 9) plus
    **where the canonical form came from** (mandate Law 14). The
    `authority` field carries a structured :class:`Authority` citation to
    one of the four Law 14 sources: an authoritative spec, a bundled
    data-set, a documented platform behavior, or a declared Paxman policy.
    A small set of routing/dispatch failures are allow-listed with
    ``authority=None`` because they describe a routing failure, not a
    canonical-form rule (Law 14 §3.6):
      - capability dispatch invariants (declared in each domain's
        `rules.py`): `not_a_<kind>_contract`, `not_a_string_value`,
        `empty_value`, `unrecognized_format`, `not_an_email_contract`,
        `not_a_uuid_contract`;
      - orchestrator routing failures (emitted by `engine.py`):
        `unparseable_contract`, `no_capability_claims`,
        `multiple_claimants`, `validation_unsupported_contract`.
    Every other fired rule MUST carry a non-``None`` authority.
    """

    rule: str
    detail: str = ""
    authority: Authority | None = attrs.field(default=None, validator=_authority_validator)

    @property
    def provenance(self) -> str:
        """Deprecated alias for the structured ``authority`` citation.

        ``Evidence`` no longer carries a free-form ``provenance`` string
        (mandate Law 14 — it carries a structured ``authority`` instead).
        Accessing this property raises an informative error rather than
        returning a silently-wrong value.
        """
        raise AttributeError(
            "Evidence no longer carries a 'provenance' string; it carries a "
            "structured 'authority: Authority | None' (mandate Law 14)."
        )


#: A capability's rule→authority manifest maps every emitted rule name to
#: the :class:`Authority` it cites (or ``None`` for the allow-listed
#: dispatch invariants that describe a routing failure, not a
#: canonical-form rule).
RuleAuthorities = Mapping[str, Authority | None]


def _evidence(
    rule: str,
    manifest: RuleAuthorities,
    detail: str = "",
) -> Evidence:
    """Build an ``Evidence`` resolving the authority from ``manifest``.

    The manifest is the single source of truth: a rule with no manifest
    entry raises ``KeyError`` here, surfacing a missing citation at the
    exact site where the rule is emitted (rather than only in a unit test
    far away). Capabilities wrap this shared helper to close over their
    own ``_RULE_AUTHORITIES`` manifest::

        def _evidence(rule: str, detail: str = "") -> Evidence:
            return _provenance_evidence(rule, _RULE_AUTHORITIES, detail)

    Args:
        rule: The rule name; must be a key in ``manifest``.
        manifest: The capability's ``_RULE_AUTHORITIES`` mapping.
        detail: Optional human-readable detail string.

    Returns:
        An ``Evidence`` instance with authority resolved from the map.
    """
    return Evidence(rule=rule, detail=detail, authority=manifest[rule])


def _evidence_from_args(
    rule: str,
    authority: Authority | None,
    detail: str = "",
) -> Evidence:
    """Build an ``Evidence`` from an explicit authority (no manifest lookup).

    Used where the citation is assembled directly (e.g. the orchestrator's
    routing-failure entries, or capabilities that construct evidence
    outside the manifest path).
    """
    return Evidence(rule=rule, detail=detail, authority=authority)
