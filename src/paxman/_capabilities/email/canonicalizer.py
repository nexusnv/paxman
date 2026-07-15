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

from paxman._capabilities.email.contract import CanonicalEmailContract
from paxman._capabilities.email.parser import _validate_dot_atom_domain, _validate_dot_atom_local
from paxman._capabilities.email.rules import _evidence
from paxman._core.contracts import Contract
from paxman._core.provenance import Evidence
from paxman._core.result import CapabilityResult
from paxman._core.status import Status

_GMAIL_DOMAINS = frozenset({"gmail.com", "googlemail.com"})

# Spec §1.3 step 1: "Strip leading and trailing ASCII whitespace."
# str.strip() also trims Unicode whitespace (e.g. U+00A0 NO-BREAK SPACE,
# U+2009 THIN SPACE) which the spec does not authorise; the explicit
# ASCII-only set is the contract.
_ASCII_WHITESPACE = " \t\n\r\f\v"


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
