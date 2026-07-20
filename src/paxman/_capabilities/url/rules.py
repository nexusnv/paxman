from __future__ import annotations

from collections.abc import Mapping

from paxman._capabilities._shared.evidence import rule_authorities
from paxman._provenance import Authority
from paxman._provenance import registries as R

# Law 14 — every emitted rule cites a source:
#   RFC 3986 (IETF STD 66) for the default normalizations,
#   the WHATWG URL Standard (retrieved 2026-07-16) for the whatwg_* rules,
#   an explicitly declared Paxman policy (this spec + docs/capabilities/url/index.md)
#   for strip_*/sort_query/scheme_not_allowed.
# Dispatch invariants carry ``None`` authority (Law 14 allow-list).
_RULE_AUTHORITIES: Mapping[str, Authority | None] = {
    # --- dispatch invariants (allow-listed, no authority) ---
    "not_a_url_contract": None,
    "not_a_string_value": None,
    # --- rejecting rules ---
    "unrecognized_format": R.RFC_3986.section("§3 (generic URI syntax ABNF)"),
    "grammar_rejected": R.RFC_3986.section("§3.1 / §3.2.2 / §3.2.3 (scheme/host/port form)"),
    "scheme_not_allowed": R.PAXMAN_SPEC_URL.section(
        "§3.1 (contract declares the in-scope scheme set)"
    ),
    # --- transforming rules (RFC 3986 authority) ---
    "lowercase_scheme": R.RFC_3986.section("§3.1 (MUST canonical lowercase)"),
    "uppercase_pct_hex": R.RFC_3986.section("§2.1 / §6.2.2.1 (SHOULD -> elevated to MUST)"),
    "lowercase_host": R.RFC_3986.section("§3.2.2 (SHOULD -> elevated to MUST)"),
    "decode_unreserved_pct": R.RFC_3986.section("§2.3 / §6.2.2.2 (SHOULD -> elevated to MUST)"),
    "keep_reserved_pct": R.RFC_3986.section("§2.2 (MUST NOT decode reserved)"),
    "elide_default_port": R.RFC_3986.section("§3.2.3 / §6.2.3 (SHOULD -> elevated to MUST)"),
    "remove_dot_segments": R.RFC_3986.section("§6.2.2.3 / §5.2.4 (SHOULD -> elevated to MUST)"),
    "empty_path_to_slash": R.RFC_3986.section("§6.2.3 (SHOULD -> elevated to MUST)"),
    "strip_userinfo": R.PAXMAN_SPEC_URL.section("§3.2 (opts into §3.2.1 delimiter elision)"),
    "strip_fragment": R.PAXMAN_SPEC_URL.section(
        "§3.2 (default-on; fragments excluded from canonical resource identifier)"
    ),
    "sort_query": R.PAXMAN_SPEC_URL.section(
        "§3.2 (explicit reorder; RFC 3986 §6.2.3 does not normalize query order)"
    ),
    "no_transformation_needed": R.RFC_3986.section("§6.2.2 (input already the normal form)"),
    # --- WHATWG-divergence rules (fire ONLY when contract.whatwg is True) ---
    "whatwg_trailing_dot_host": R.WHATWG_URL.section("host parsing / cert comparison"),
    "whatwg_pct_dot_in_path": R.WHATWG_URL.section("§4.4 (path states), issue #658"),
    "whatwg_infinite_slashes": R.WHATWG_URL.section("§4.2 (scheme state)"),
    "whatwg_backslash_coerce": R.WHATWG_URL.section("§4.4 (authority/path states)"),
}

_evidence = rule_authorities(_RULE_AUTHORITIES)
