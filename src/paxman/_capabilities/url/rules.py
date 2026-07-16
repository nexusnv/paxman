from __future__ import annotations

from collections.abc import Mapping

from paxman._core.provenance import Evidence

# Law 14 — every emitted rule cites a source:
#   RFC 3986 (IETF STD 66) for the default normalizations,
#   the WHATWG URL Standard (retrieved 2026-07-16) for the whatwg_* rules,
#   an explicitly declared Paxman policy (this spec + docs/capabilities/url/index.md)
#   for strip_*/sort_query/scheme_not_allowed.
# Dispatch invariants carry "" (Law 14 allow-list).
_RULE_PROVENANCE: Mapping[str, str] = {
    # --- dispatch invariants (allow-listed, empty provenance) ---
    "not_a_url_contract": "",
    "not_a_string_value": "",
    # --- rejecting rules ---
    "unrecognized_format": "RFC 3986 §3 (generic URI syntax ABNF)",
    "grammar_rejected": "RFC 3986 §3.1 / §3.2.2 / §3.2.3 (scheme/host/port form)",
    "scheme_not_allowed": "Declared Paxman policy (spec §3.1): contract declares the "
    "in-scope scheme set",
    # --- transforming rules (RFC 3986 authority) ---
    "lowercase_scheme": "RFC 3986 §3.1 (MUST canonical lowercase)",
    "uppercase_pct_hex": "RFC 3986 §2.1 / §6.2.2.1 (SHOULD -> elevated to MUST)",
    "lowercase_host": "RFC 3986 §3.2.2 (SHOULD -> elevated to MUST)",
    "decode_unreserved_pct": "RFC 3986 §2.3 / §6.2.2.2 (SHOULD -> elevated to MUST)",
    "keep_reserved_pct": "RFC 3986 §2.2 (MUST NOT decode reserved)",
    "elide_default_port": "RFC 3986 §3.2.3 / §6.2.3 (SHOULD -> elevated to MUST)",
    "remove_dot_segments": "RFC 3986 §6.2.2.3 / §5.2.4 (SHOULD -> elevated to MUST)",
    "empty_path_to_slash": "RFC 3986 §6.2.3 (SHOULD -> elevated to MUST)",
    "strip_userinfo": "Declared Paxman policy (spec §3.2): opts into §3.2.1 delimiter elision",
    "strip_fragment": "Declared Paxman policy (spec §3.2): default-on; fragments excluded "
    "from canonical resource identifier",
    "sort_query": "Declared Paxman policy (spec §3.2): explicit reorder, RFC 3986 §6.2.3 "
    "does not normalize query order",
    "no_transformation_needed": "RFC 3986 §6.2.2 (input already the normal form)",
    # --- WHATWG-divergence rules (fire ONLY when contract.whatwg is True) ---
    "whatwg_trailing_dot_host": "WHATWG URL Standard, host parsing / cert comparison "
    "(retrieved 2026-07-16)",
    "whatwg_pct_dot_in_path": "WHATWG URL Standard §4.4 (path states), issue #658 "
    "(retrieved 2026-07-16)",
    "whatwg_infinite_slashes": "WHATWG URL Standard §4.2 (scheme state) (retrieved 2026-07-16)",
    "whatwg_backslash_coerce": "WHATWG URL Standard §4.4 (authority/path states) "
    "(retrieved 2026-07-16)",
}


def _evidence(rule: str, detail: str = "") -> Evidence:
    """Build an Evidence entry; raises KeyError on an unmanifested rule (Law 14)."""
    return Evidence(rule=rule, detail=detail, provenance=_RULE_PROVENANCE[rule])
