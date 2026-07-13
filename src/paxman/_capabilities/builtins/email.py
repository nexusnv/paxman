"""EmailCapability: the first built-in capability of Paxman v2.

Mandate Laws 4, 5, 7, 8, 8a, 11:
- Law 4: rewrites known representations; does not interpret.
- Law 5: the contract declares the policy; the capability applies it.
- Law 7: the policy is explicit; no auto-detection.
- Law 8 + 8a: the capability is a pure function of (value, contract).
  No network, no time, no randomness, no filesystem.
- Law 11: the canonical form is a function of (value, contract). Two
  independent implementations must produce the same value.
"""
from __future__ import annotations

from paxman._contracts.contract import CanonicalEmailContract, Contract
from paxman._core.types import CapabilityResult, Evidence, Status


_GMAIL_DOMAINS = frozenset({"gmail.com", "googlemail.com"})


class EmailCapability:
    """A pure deterministic transformation that canonicalizes emails.

    `Capability` (from `paxman._capabilities.protocol`) is a structural
    Protocol — this class satisfies it by virtue of its `name` attribute
    and the `can_handle` / `canonicalize` methods, not by inheritance.
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
                evidence=(Evidence(rule="not_an_email_contract"),),
            )
        if not isinstance(value, str):
            return CapabilityResult(
                status=Status.INVALID,
                evidence=(Evidence(rule="not_a_string_value"),),
            )

        # Strict-mode grammar check happens FIRST so a non-grammar input
        # is rejected before any rewriting (no partial canonicalization).
        if contract.strict:
            if " " in value or "\t" in value or "\n" in value:
                return CapabilityResult(
                    status=Status.INVALID,
                    evidence=(Evidence(rule="strict_rejected_whitespace"),),
                )
            try:
                value.encode("ascii")
            except UnicodeEncodeError:
                return CapabilityResult(
                    status=Status.INVALID,
                    evidence=(Evidence(rule="strict_rejected_non_ascii"),),
                )

        if "@" not in value:
            return CapabilityResult(
                status=Status.INVALID, evidence=(Evidence(rule="missing_at_sign"),)
            )
        local, _, domain = value.partition("@")
        if not local or not domain:
            return CapabilityResult(
                status=Status.INVALID, evidence=(Evidence(rule="empty_local_or_domain"),)
            )

        evidence: list[Evidence] = []

        # 1. Strip whitespace.
        if contract.strip_whitespace:
            stripped = value.strip()
            if stripped != value:
                evidence.append(Evidence(rule="stripped_whitespace"))
                value = stripped
            # Re-parse after stripping (the @ position may have moved).
            local, _, domain = value.partition("@")

        # 2. Lowercase.
        if contract.lowercase:
            new_local = local.lower()
            new_domain = domain.lower()
            if new_local != local:
                evidence.append(Evidence(rule="lowercased_local_part"))
            if new_domain != domain:
                evidence.append(Evidence(rule="lowercased_domain"))
            local = new_local
            domain = new_domain

        # 3. Provider aliases (gmail). The casefold comparison makes the
        # Gmail rule trigger regardless of `lowercase`; the domain is
        # then normalized to its canonical-case form (`gmail.com`).
        if contract.provider_aliases == "gmail" and domain.casefold() in _GMAIL_DOMAINS:
            if domain != "gmail.com":
                evidence.append(
                    Evidence(
                        rule="domain_synonym_gmail",
                        detail=f"{domain} -> gmail.com",
                    )
                )
            domain = "gmail.com"
            # Strip dots in the local part.
            new_local = local.replace(".", "")
            if new_local != local:
                evidence.append(Evidence(rule="stripped_dots_in_local_part"))
                local = new_local
            # Strip +tag.
            if "+" in local:
                evidence.append(Evidence(rule="stripped_plus_tag"))
                local = local.split("+", 1)[0]

        # Re-validate after rewrites: stripping dots or a +tag can empty
        # the local part. Mandate Law 4: a malformed canonical form
        # is INVALID, not silently emitted.
        if not local or not domain:
            return CapabilityResult(
                status=Status.INVALID,
                evidence=(Evidence(rule="empty_local_or_domain"),),
            )

        canonical = f"{local}@{domain}"
        return CapabilityResult(
            status=Status.CANONICALIZED, value=canonical, evidence=tuple(evidence)
        )
