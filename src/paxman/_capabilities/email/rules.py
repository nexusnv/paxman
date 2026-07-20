"""Email Law 14 rule→authority manifest + evidence helper.

Moved VERBATIM from `paxman._capabilities.builtins.email`, then migrated
from a free-form `_RULE_PROVENANCE` string map to a structured
`_RULE_AUTHORITIES` authority map (mandate Law 14 — issue #158).
"""

from collections.abc import Mapping

from paxman._capabilities._shared.evidence import rule_authorities
from paxman._provenance import Authority
from paxman._provenance import registries as R

# Composite authority used by a single rule that cites more than one spec.
_EMAIL_GRAMMAR = Authority(
    "RFC 5322 + RFC 5321 + RFC 1035",
    "RFC 5322 §3.2.3 + RFC 5321 §3.4 + RFC 1035 §2.3.1",
    "grammar",
)
_DEOBFUSCATION = Authority(
    "RFC 5322 + paxman spec/email",
    "RFC 5322 §3.4.1 (addr-spec) + paxman spec/email §2.4 (recognition grammar)",
    "grammar",
)
_PROVIDER_EQUIV = Authority(
    "Gmail + paxman spec/email",
    "Gmail documented behavior (dots ignored; googlemail.com alias) + paxman spec/email §2.4",
    "platform-behaviour",
    retrieved_at="2026-07-14",
)

# ---------------------------------------------------------------------------
# Law 14 rule→authority manifest
# ---------------------------------------------------------------------------
# Every code path inside `canonicalize` that returns an `Evidence` entry
# has an entry here. The two dispatch invariants (not_an_email_contract,
# not_a_string_value) are allow-listed with ``None`` authority (Law 14
# §3.6): they describe a routing failure, not a canonical-form rule.
#
# Citation categories (MANDATE §7 Law 14):
#   - "RFC ..."        → authoritative specification
#   - "Google Help..." → documented platform behavior
#   - "paxman spec/..."→ explicitly declared Paxman policy
_RULE_AUTHORITIES: Mapping[str, Authority | None] = {
    # --- dispatch invariants (no authority — Law 14 §3.6 allow-list) ---
    "not_an_email_contract": None,
    "not_a_string_value": None,
    # --- strict-mode rejection (Paxman policy) ---
    "strict_rejected_whitespace": R.PAXMAN_SPEC_EMAIL,
    "strict_rejected_non_ascii": R.PAXMAN_SPEC_EMAIL,
    # --- structural rejection (authoritative spec) ---
    "missing_at_sign": R.RFC_5322.section('§3.6 (mailbox = local-part "@" domain)'),
    "empty_local_or_domain": R.RFC_5322.section("§3.6"),
    "grammar_rejected": _EMAIL_GRAMMAR,
    # --- transforming rules (authoritative spec) ---
    "stripped_whitespace": R.RFC_5322.section("§2.1 + §3.6.3 (CFWS)"),
    "lowercased_domain": R.RFC_5321.section("§2.4 (domain is case-insensitive)"),
    # --- transforming rules (declared Paxman policy) ---
    "lowercased_local_part": R.PAXMAN_SPEC_EMAIL.section(
        "§1.3 (Paxman policy; diverges from RFC 5321 §2.4)"
    ),
    # --- transforming rules (documented platform behavior) ---
    "domain_synonym_gmail": R.GOOGLE_HELP.section('"Use aliases on your Account"'),
    "stripped_dots_in_local_part": R.GOOGLE_HELP.section("dots don't matter in Gmail addresses"),
    "stripped_plus_tag": R.GOOGLE_HELP.section("Gmail +alias addressing"),
    # --- recognition-layer transformations (authoritative spec) ---
    "collapsed_internal_whitespace": R.RFC_5322.section(
        "§1.3 (internal whitespace tolerated for obfuscation)"
    ),
    "deobfuscated_verbal_at_dot": _DEOBFUSCATION,
    # --- recognition-layer ambiguity (declared Paxman policy) ---
    "ambiguous_provider_equivalence": _PROVIDER_EQUIV,
    # --- recognition-layer rejection (authoritative spec) ---
    "unrecognized_format": _EMAIL_GRAMMAR,
}

_evidence = rule_authorities(_RULE_AUTHORITIES)
