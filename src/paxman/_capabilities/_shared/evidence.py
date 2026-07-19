"""Shared Law-14 evidence helpers (mandate Law 9 + 14).

Capabilities each wrapped the central ``_provenance._evidence(rule, manifest,
detail)`` helper over their own ``_RULE_AUTHORITIES`` manifest — a 3-line
closure repeated 10x. ``make_evidence`` returns that closure from a manifest in
one call. ``make_evidence_for`` extends it for the engine-aware capabilities
(country, money): when an ``engine`` binds a non-default edition of a named
authority, the registry-citing rules re-resolve their authority from the engine
so the recorded edition matches the binding (Concern 3). The authority is named
by a plain string param — not hardcoded — so a future 3rd registry-backed
domain (CLDR, E.164) wires in with no change here.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from paxman._core.engine_env import Engine
from paxman._provenance.authority import Authority
from paxman._provenance.evidence import Evidence, _evidence_from_args

#: Engine-aware ``_evidence`` closure shape: ``(rule, detail="", engine=None)``.
EngineEvidence = Callable[[str, str, "Engine | None"], Evidence]

#: A capability's rule→authority manifest maps every emitted rule name to the
#: :class:`Authority` it cites (or ``None`` for allow-listed dispatch invariants).
RuleAuthorities = Mapping[str, Authority | None]


def make_evidence(manifest: RuleAuthorities) -> Callable[..., Evidence]:
    """Return an ``_evidence(rule, detail="")`` closure bound to ``manifest``."""

    def _evidence(rule: str, detail: str = "") -> Evidence:
        return Evidence(rule=rule, detail=detail, authority=manifest[rule])

    return _evidence


def make_evidence_for(
    manifest: RuleAuthorities,
    authority_name: str,
    registry_rules: frozenset[str] | None = None,
) -> Callable[..., Evidence]:
    """Return an engine-aware ``_evidence(rule, detail="", engine=None)`` closure.

    When ``engine`` is not ``None`` and ``rule`` is in ``registry_rules`` and the
    manifest authority is not ``None``, the authority is re-resolved from
    ``engine.authority(authority_name)`` so the recorded edition reflects the
    pinned edition. ``authority_name`` is a plain string (e.g. ``"ISO 3166-1"``)
    — not hardcoded — to stay flexible as engine-awareness spreads to more
    domains.

    Args:
        manifest: The capability's ``_RULE_AUTHORITIES`` mapping.
        authority_name: The registry authority this capability cites per edition.
        registry_rules: Rule names whose authority must re-resolve via the engine.
    """

    rules = registry_rules or frozenset()

    def _evidence(rule: str, detail: str = "", engine: Engine | None = None) -> Evidence:
        authority = manifest[rule]
        if engine is not None and rule in rules and authority is not None:
            bound = engine.authority(authority_name)
            if rule == "unrecognized_format":
                authority = bound.section(_unrecognized_section(manifest, rule))
            else:
                authority = bound.section(authority.version)
        return _evidence_from_args(rule, authority, detail)

    return _evidence


def _unrecognized_section(manifest: RuleAuthorities, rule: str) -> str:
    """Preserve the manifest's unrecognized_format narrative if present."""
    base = manifest.get(rule)
    if base is not None and base.version:
        return base.version
    return "input is not a recognized token"
