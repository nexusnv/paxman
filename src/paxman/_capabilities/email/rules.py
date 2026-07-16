"""Email Law 14 rule→provenance manifest + evidence helper.

Moved VERBATIM from `paxman._capabilities.builtins.email`.
"""

from collections.abc import Mapping
from types import MappingProxyType

from paxman._core.provenance import Evidence

# ---------------------------------------------------------------------------
# Law 14 rule→provenance manifest
# ---------------------------------------------------------------------------
# Every code path inside `canonicalize` that returns an `Evidence` entry
# has an entry here. The two dispatch invariants (not_an_email_contract,
# not_a_string_value) are allow-listed with empty `provenance` (Law 14
# §3.6 in the recalibration spec): they describe a routing failure,
# not a canonical-form rule.
#
# Citation categories (MANDATE §7 Law 14):
#   - "RFC ..."        → authoritative specification
#   - "Google Help..." → documented platform behavior
#   - "paxman spec/..."→ explicitly declared Paxman policy
_RULE_PROVENANCE: Mapping[str, str] = MappingProxyType(
    {
        # --- dispatch invariants (no provenance — Law 14 §3.6 allow-list) ---
        "not_an_email_contract": "",
        "not_a_string_value": "",
        # --- strict-mode rejection (Paxman policy) ---
        "strict_rejected_whitespace": "paxman spec/email §1.5 (strict-mode policy)",
        "strict_rejected_non_ascii": "paxman spec/email §1.5 (strict-mode policy)",
        # --- structural rejection (authoritative spec) ---
        "missing_at_sign": 'RFC 5322 §3.6 (mailbox = local-part "@" domain)',
        "empty_local_or_domain": "RFC 5322 §3.6",
        "grammar_rejected": "RFC 5322 §3.2.3 + RFC 5321 §3.4 + RFC 1035 §2.3.1",
        # --- transforming rules (authoritative spec) ---
        "stripped_whitespace": "RFC 5322 §2.1 + §3.6.3 (CFWS)",
        "lowercased_domain": "RFC 5321 §2.4 (domain is case-insensitive)",
        # --- transforming rules (declared Paxman policy) ---
        "lowercased_local_part": (
            "paxman spec/email §1.3 (Paxman policy; diverges from RFC 5321 §2.4)"
        ),
        # --- transforming rules (documented platform behavior) ---
        "domain_synonym_gmail": (
            'Google Help: "Use aliases on your Account" (retrieved 2026-07-14)'
        ),
        "stripped_dots_in_local_part": (
            "Google Help: dots don't matter in Gmail addresses (retrieved 2026-07-14)"
        ),
        "stripped_plus_tag": ("Google Help: Gmail +alias addressing (retrieved 2026-07-14)"),
        # --- recognition-layer transformations (authoritative spec) ---
        "collapsed_internal_whitespace": (
            "RFC 5322 §1.3 (internal whitespace tolerated for obfuscation)"
        ),
        "deobfuscated_verbal_at_dot": (
            "RFC 5322 §3.4.1 (addr-spec is the canonical target) — Paxman "
            "recognition grammar deobfuscates spoken 'at'→@, 'dot'→. forms"
        ),
        # --- recognition-layer ambiguity (declared Paxman policy) ---
        "ambiguous_provider_equivalence": (
            "Gmail documented behavior (dots ignored in local part; "
            "googlemail.com is a gmail.com alias) + Paxman policy: surface "
            "ambiguity rather than guess (spec §2.4)"
        ),
        # --- recognition-layer rejection (authoritative spec) ---
        "unrecognized_format": "input matched no email grammar",
    }
)


def _evidence(rule: str, detail: str = "") -> Evidence:
    """Build an `Evidence` pulling the Law 14 provenance citation
    from the `_RULE_PROVENANCE` manifest.

    The manifest is the single source of truth: a rule with no manifest
    entry raises `KeyError` here, surfacing a missing citation at the
    exact site where the rule is emitted (rather than only in a unit
    test far away). The Law 14 audit test (`test_no_empty_provenance`)
    in `tests/unit/test_email_capability.py` additionally greps the
    capability source for `rule="..."` literals and asserts every
    literal is keyed in `_RULE_PROVENANCE`.
    """
    return Evidence(rule=rule, detail=detail, provenance=_RULE_PROVENANCE[rule])
