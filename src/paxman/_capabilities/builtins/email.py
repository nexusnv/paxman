"""EmailCapability: the first built-in capability of Paxman v2.

Mandate Laws 4, 5, 7, 8, 8a, 11, 14:
- Law 4: rewrites known representations; does not interpret.
- Law 5: the contract declares the policy; the capability applies it.
- Law 7: the policy is explicit; no auto-detection.
- Law 8 + 8a: the capability is a pure function of (value, contract).
  No network, no time, no randomness, no filesystem.
- Law 11: the canonical form is a function of (value, contract). Two
  independent implementations must produce the same value.
- Law 14: every transformation rule has provenance. The rule→citation
  manifest is `_RULE_PROVENANCE`; `Evidence.provenance` is populated
  from it. See `docs/superpowers/specs/
  2026-07-13-email-canonicalization-design.md` §7 for the rule-by-rule
  audit.

Surface-grammar gate
---------------------

Pre-Law 14, the capability silently accepted any string with one `@`
and non-empty local+domain parts as `CANONICALIZED`. The user-experiment
report (2026-07-14) surfaced this as silent canonical-form invention for
malformed inputs like `user@example.com@example.com`,
`user@-domain.com`, `user@[127.0.0.300]`.

Post-Law 14, the capability gate-checks the local part against RFC 5322
§3.2.3 `dot-atom` and the domain against RFC 5321 §3.4 + RFC 1035
§2.3.1. Inputs that fail the gate return `Status.INVALID` with a
`grammar_rejected` evidence rule. Quoted-string local parts
(`RFC 5322 §3.2.4`) and bracketed domain literals
(`RFC 5321 §3.4.1 IPv4 / §3.4.2 IPv6`) are out of v2.0.0 scope and
fail this gate; v2.x may extend the gate to admit them.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from types import MappingProxyType

from paxman._contracts.contract import CanonicalEmailContract, Contract
from paxman._core.types import CapabilityResult, Evidence, Status

_GMAIL_DOMAINS = frozenset({"gmail.com", "googlemail.com"})

# Spec §1.3 step 1: "Strip leading and trailing ASCII whitespace."
# str.strip() also trims Unicode whitespace (e.g. U+00A0 NO-BREAK SPACE,
# U+2009 THIN SPACE) which the spec does not authorise; the explicit
# ASCII-only set is the contract.
_ASCII_WHITESPACE = " \t\n\r\f\v"

# RFC 5322 §3.2.3 `atext` — the ASCII atom-text character class. Used
# to validate the local part of the mailbox as a `dot-atom`:
#   dot-atom = atext *("." atext)
# Dots are allowed *between* atext runs only (no leading, no trailing,
# no consecutive dots). Quoted-string local parts (RFC 5322 §3.2.4)
# are out of v2.0.0 scope and fail the atext gate.
_ATEXT: frozenset[str] = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!#$%&'*+-/=?^_`{|}~"
)

# RFC 1035 §2.3.1 / RFC 5321 §3.4 `sub-domain` grammar:
#   Let-dig = ALPHA | DIGIT
#   Ldh-str = *( ALPHA | DIGIT | "-" )
#   sub-domain = Let-dig *Ldh-str
# i.e. each label starts and ends with a letter or digit, interior
# characters may be letters, digits, or hyphens, and the label length
# is 1-63. The total domain length is capped at 253 (RFC 1035 §2.3.4).
# Bracketed domain-literals (RFC 5321 §3.4.1 IPv4 / §3.4.2 IPv6) are
# out of v2.0.0 scope and fail the dot-atom-domain gate.
_LABEL_MAX_LEN = 63
_DOMAIN_MAX_LEN = 253

# Pre-compiled dot-atom regexes — dot-atom local part and dot-atom
# domain. Single labels validated by the `_LABEL` pattern; multiple
# labels are joined by dots.
_ATEXT_RUN = r"[!#$%&'*+/=?^_`{|}~A-Za-z0-9-]"
_LABEL_RUN = r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
_DOT_ATOM_LOCAL = re.compile(rf"^{_ATEXT_RUN}+(?:\.{_ATEXT_RUN}+)*$")
_DOT_ATOM_DOMAIN = re.compile(rf"^{_LABEL_RUN}(?:\.{_LABEL_RUN})*$")


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


def _validate_dot_atom_local(local: str) -> bool:
    """RFC 5322 §3.2.3 dot-atom local part.

    Rejects:
    - empty string
    - leading or trailing dot
    - consecutive dots
    - any character that is not atext and not `.`
    - quoted-string local parts (RFC 5322 §3.2.4)
    - internal whitespace, parentheses, comments, slashes
    """
    if not local:
        return False
    if not _DOT_ATOM_LOCAL.fullmatch(local):
        return False
    # belt-and-braces: atext set membership is the canonical check.
    for ch in local:
        if ch != "." and ch not in _ATEXT:
            return False
    return True


def _validate_dot_atom_domain(domain: str) -> bool:
    """RFC 5321 §3.4 dot-atom domain + RFC 1035 §2.3.1 label rules.

    Rejects:
    - empty string
    - leading or trailing dot
    - consecutive dots
    - label that starts or ends with `-`
    - label longer than 63 characters
    - total domain length longer than 253 characters
    - any label containing characters other than LDH (letters, digits,
      hyphens)
    - bracketed domain-literals (RFC 5321 §3.4.1/§3.4.2 IPv4/IPv6)

    NOTE on intentional acceptances: a single-label domain like
    `localhost` is *valid* under RFC 1035 §2.3.1 (a label is a
    sub-domain). This capability accepts `user@localhost` as
    CANONICALIZED under the v2.0.0 grammar gate. `strict=True` is
    intentionally narrow in v2.0.0 (whitespace + ASCII-only) and
    does NOT reject single-label domains; a contract author wanting
    a tighter multi-label requirement is not served by `strict=True`
    in v2.0.0 and would need a future v2.x capability extension.
    """
    if not domain:
        return False
    if len(domain) > _DOMAIN_MAX_LEN:
        return False
    if not _DOT_ATOM_DOMAIN.fullmatch(domain):
        return False
    labels = domain.split(".")
    for label in labels:
        if len(label) == 0 or len(label) > _LABEL_MAX_LEN:
            return False
        if label.startswith("-") or label.endswith("-"):
            return False
    return True


class EmailCapability:
    """A pure deterministic transformation that canonicalizes emails.

    `Capability` (from `paxman._capabilities.protocol`) is a structural
    Protocol — this class satisfies it by virtue of its `name` attribute
    and the `can_handle` / `canonicalize` methods, not by inheritance.

    Law 14 enforcement: every `Evidence` returned by `canonicalize`
    pulls its `provenance` from `_RULE_PROVENANCE` via the `_evidence`
    helper. Adding a new rule requires adding to the manifest; the
    manifest lookup will raise `KeyError` if a rule is constructed
    without one.
    """

    name: str = "email_canonicalization"

    def can_handle(self, contract: Contract, value: object) -> bool:
        return isinstance(contract, CanonicalEmailContract) and isinstance(value, str)

    def canonicalize(self, value: object, contract: Contract) -> CapabilityResult:
        if not isinstance(contract, CanonicalEmailContract):
            # Structural typecheck: a non-email contract must not reach
            # this capability. Return INVALID as a defensive default;
            # the orchestrator maps it through classification.
            return CapabilityResult(
                status=Status.INVALID,
                evidence=(_evidence("not_an_email_contract"),),
            )
        if not isinstance(value, str):
            return CapabilityResult(
                status=Status.INVALID,
                evidence=(_evidence("not_a_string_value"),),
            )

        # Strict-mode grammar check happens FIRST so a non-grammar input
        # is rejected before any rewriting (no partial canonicalization).
        if contract.strict:
            if " " in value or "\t" in value or "\n" in value:
                return CapabilityResult(
                    status=Status.INVALID,
                    evidence=(_evidence("strict_rejected_whitespace"),),
                )
            try:
                value.encode("ascii")
            except UnicodeEncodeError:
                return CapabilityResult(
                    status=Status.INVALID,
                    evidence=(_evidence("strict_rejected_non_ascii"),),
                )

        if "@" not in value:
            return CapabilityResult(status=Status.INVALID, evidence=(_evidence("missing_at_sign"),))
        local, _, domain = value.partition("@")
        if not local or not domain:
            return CapabilityResult(
                status=Status.INVALID, evidence=(_evidence("empty_local_or_domain"),)
            )

        evidence: list[Evidence] = []

        # 1. Strip ASCII whitespace (spec §1.3 step 1).
        if contract.strip_whitespace:
            stripped = value.strip(_ASCII_WHITESPACE)
            if stripped != value:
                evidence.append(_evidence("stripped_whitespace"))
                value = stripped
            # Re-parse after stripping (the @ position may have moved).
            local, _, domain = value.partition("@")

        # 2. Lowercase.
        if contract.lowercase:
            new_local = local.lower()
            new_domain = domain.lower()
            if new_local != local:
                evidence.append(_evidence("lowercased_local_part"))
            if new_domain != domain:
                evidence.append(_evidence("lowercased_domain"))
            local = new_local
            domain = new_domain

        # 3. Provider aliases (gmail). The casefold comparison makes the
        # Gmail rule trigger regardless of `lowercase`; the domain is
        # then normalized to its canonical-case form (`gmail.com`).
        if contract.provider_aliases == "gmail" and domain.casefold() in _GMAIL_DOMAINS:
            if domain != "gmail.com":
                evidence.append(_evidence("domain_synonym_gmail", detail=f"{domain} -> gmail.com"))
            domain = "gmail.com"
            # Strip dots in the local part.
            new_local = local.replace(".", "")
            if new_local != local:
                evidence.append(_evidence("stripped_dots_in_local_part"))
                local = new_local
            # Strip +tag.
            if "+" in local:
                evidence.append(_evidence("stripped_plus_tag"))
                local = local.split("+", 1)[0]

        # 4. Surface-grammar gate (RFC 5322 §3.2.3 + RFC 5321 §3.4 +
        # RFC 1035 §2.3.1). Run AFTER rewrites because gmail dot-stripping
        # or +tag-stripping would otherwise be rejected as non-dot-atom
        # locally (e.g. `..@gmail.com` would fail before stripping).
        # Idempotence is preserved: a canonical dot-atom email passes
        # the gate trivially on re-canonicalize.
        if not _validate_dot_atom_local(local) or not _validate_dot_atom_domain(domain):
            evidence.append(_evidence("grammar_rejected"))
            return CapabilityResult(
                status=Status.INVALID,
                evidence=tuple(evidence),
            )

        canonical = f"{local}@{domain}"
        return CapabilityResult(
            status=Status.CANONICALIZED, value=canonical, evidence=tuple(evidence)
        )
