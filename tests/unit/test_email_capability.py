"""Tests for the EmailCapability.

These tests assert the v2.0.0 default behaviour:
- Default: lowercase + strip whitespace, no provider rules.
- `provider_aliases='gmail'`: strip +tag and dots for gmail.com / googlemail.com.
- `strict=True`: reject non-RFC-5321 grammar (no spaces).
- Idempotent (mandate Law 2).
- Pure function (mandate Law 8a).
"""

from __future__ import annotations

from typing import Any, cast

from paxman._capabilities.builtins.email import _RULE_PROVENANCE, EmailCapability
from paxman._contracts.contract import CanonicalEmailContract, Contract
from paxman._core.types import Status


def _cap() -> EmailCapability:
    return EmailCapability()


def _contract(**kw: object) -> CanonicalEmailContract:
    base: dict[str, object] = dict(
        lowercase=True, strip_whitespace=True, provider_aliases="none", strict=False
    )
    base.update(kw)
    return CanonicalEmailContract(**cast(Any, base))


class TestEmailCapability:
    def test_capability_metadata(self) -> None:
        c = _cap()
        assert c.name == "email_canonicalization"

    def test_can_handle_matches_email_contract(self) -> None:
        c = _cap()
        assert c.can_handle(_contract(), "a@b.c") is True

    def test_can_handle_rejects_non_email_contract(self) -> None:
        c = _cap()
        assert c.can_handle(cast(Contract, "not a contract"), "a@b.c") is False

    def test_default_lowercases(self) -> None:
        c = _cap()
        r = c.canonicalize("John.Doe@Example.COM", _contract())
        assert r.status is Status.CANONICALIZED
        assert r.value == "john.doe@example.com"

    def test_default_strips_whitespace(self) -> None:
        c = _cap()
        r = c.canonicalize("  a@b.c  ", _contract())
        assert r.value == "a@b.c"

    def test_default_preserves_plus_alias(self) -> None:
        c = _cap()
        r = c.canonicalize("user+tag@example.com", _contract())
        assert r.value == "user+tag@example.com"

    def test_gmail_alias_strips_plus_tag(self) -> None:
        c = _cap()
        r = c.canonicalize("user+tag@gmail.com", _contract(provider_aliases="gmail"))
        assert r.value == "user@gmail.com"

    def test_gmail_alias_strips_dots(self) -> None:
        c = _cap()
        r = c.canonicalize("u.s.e.r@gmail.com", _contract(provider_aliases="gmail"))
        assert r.value == "user@gmail.com"

    def test_gmail_alias_normalizes_googlemail_to_gmail(self) -> None:
        c = _cap()
        r = c.canonicalize("user@googlemail.com", _contract(provider_aliases="gmail"))
        assert r.value == "user@gmail.com"

    def test_gmail_alias_case_insensitive_domain(self) -> None:
        # Mandate Law 1 + casefold: Gmail rule applies regardless of
        # domain casing, even when `lowercase=False`.
        c = _cap()
        r = c.canonicalize("user@GMAIL.COM", _contract(provider_aliases="gmail", lowercase=False))
        assert r.value == "user@gmail.com"

    def test_gmail_alias_does_not_apply_to_non_gmail_domains(self) -> None:
        c = _cap()
        r = c.canonicalize("u.s.e.r+tag@example.com", _contract(provider_aliases="gmail"))
        # Provider rule is gmail-only; the policy does not authorize
        # rewriting for unknown domains.
        assert r.value == "u.s.e.r+tag@example.com"

    def test_gmail_rewrite_yields_invalid_when_local_becomes_empty(self) -> None:
        # Mandate Law 4: stripping dots or a +tag must not silently
        # produce a value with an empty local part. e.g. "@gmail.com"
        # after dot/plus stripping has no local part.
        c = _cap()
        r = c.canonicalize("+tag@gmail.com", _contract(provider_aliases="gmail"))
        assert r.status is Status.INVALID

    def test_strict_mode_rejects_embedded_space(self) -> None:
        c = _cap()
        r = c.canonicalize("a b@c.d", _contract(strict=True))
        assert r.status is Status.INVALID

    def test_strict_mode_rejects_unicode(self) -> None:
        c = _cap()
        r = c.canonicalize("ü@ser.de", _contract(strict=True))
        assert r.status is Status.INVALID

    def test_no_at_sign_yields_invalid(self) -> None:
        c = _cap()
        r = c.canonicalize("not-an-email", _contract())
        assert r.status is Status.INVALID

    def test_idempotence(self) -> None:
        # Mandate Law 2: canonicalize(canonicalize(x)) == canonicalize(x).
        c = _cap()
        contract = _contract()
        once = c.canonicalize("  John.Doe@Example.COM  ", contract)
        assert once.status is Status.CANONICALIZED
        twice = c.canonicalize(once.value, contract)
        assert twice.status is Status.CANONICALIZED
        assert twice.value == once.value

    def test_lowercase_false_preserves_case(self) -> None:
        c = _cap()
        r = c.canonicalize("John.Doe@Example.COM", _contract(lowercase=False))
        assert r.value == "John.Doe@Example.COM"

    def test_evidence_is_recorded(self) -> None:
        # Mandate Law 9: evidence, not confidence.
        c = _cap()
        r = c.canonicalize("User@Example.COM", _contract())
        rule_names = {e.rule for e in r.evidence}
        assert "lowercased_local_part" in rule_names
        assert "lowercased_domain" in rule_names

    def test_evidence_carries_provenance_citation(self) -> None:
        # Mandate Law 14: every Evidence entry has a non-empty provenance
        # citation, except the two dispatch invariants.
        c = _cap()
        r = c.canonicalize("User@Example.COM", _contract())
        allowlist = {"not_an_email_contract", "not_a_string_value"}
        for ev in r.evidence:
            if ev.rule in allowlist:
                continue
            assert ev.provenance != "", f"Law 14 violation: rule {ev.rule!r} has empty provenance"

    def test_grammar_rejects_internal_whitespace_in_local_part(self) -> None:
        c = _cap()
        r = c.canonicalize("user @example.com", _contract())
        assert r.status is Status.INVALID
        assert "grammar_rejected" in {e.rule for e in r.evidence}

    def test_grammar_rejects_whitespace_in_domain(self) -> None:
        c = _cap()
        r = c.canonicalize("user@ example.com", _contract())
        assert r.status is Status.INVALID
        assert "grammar_rejected" in {e.rule for e in r.evidence}

    def test_grammar_rejects_consecutive_dots_in_local_part(self) -> None:
        c = _cap()
        r = c.canonicalize("user..name@example.com", _contract())
        assert r.status is Status.INVALID
        assert "grammar_rejected" in {e.rule for e in r.evidence}

    def test_grammar_rejects_bracketed_domain_literal(self) -> None:
        c = _cap()
        r = c.canonicalize("user@[127.0.0.1]", _contract())
        assert r.status is Status.INVALID
        assert "grammar_rejected" in {e.rule for e in r.evidence}

    def test_grammar_rejects_unclosed_bracket(self) -> None:
        c = _cap()
        r = c.canonicalize("user@[127.0.0.1", _contract())
        assert r.status is Status.INVALID
        assert "grammar_rejected" in {e.rule for e in r.evidence}

    def test_grammar_rejects_parenthesized_comment(self) -> None:
        c = _cap()
        r = c.canonicalize("(comment)user@example.com", _contract())
        assert r.status is Status.INVALID
        assert "grammar_rejected" in {e.rule for e in r.evidence}

    def test_grammar_rejects_trailing_slash_in_domain(self) -> None:
        c = _cap()
        r = c.canonicalize("user@example.com/", _contract())
        assert r.status is Status.INVALID
        assert "grammar_rejected" in {e.rule for e in r.evidence}

    def test_grammar_rejects_double_at_sign(self) -> None:
        c = _cap()
        r = c.canonicalize("user@example.com@example.com", _contract())
        assert r.status is Status.INVALID
        assert "grammar_rejected" in {e.rule for e in r.evidence}

    def test_grammar_rejects_leading_dash_in_domain(self) -> None:
        c = _cap()
        r = c.canonicalize("user@-domain.com", _contract())
        assert r.status is Status.INVALID
        assert "grammar_rejected" in {e.rule for e in r.evidence}

    def test_grammar_rejects_leading_dot_in_local_part(self) -> None:
        c = _cap()
        r = c.canonicalize(".user@example.com", _contract())
        assert r.status is Status.INVALID
        assert "grammar_rejected" in {e.rule for e in r.evidence}

    def test_grammar_rejects_trailing_dot_in_local_part(self) -> None:
        c = _cap()
        r = c.canonicalize("user.@example.com", _contract())
        assert r.status is Status.INVALID
        assert "grammar_rejected" in {e.rule for e in r.evidence}

    def test_grammar_rejects_quoted_string_local_part_v1_scope(self) -> None:
        c = _cap()
        r = c.canonicalize('"user name"@example.com', _contract())
        assert r.status is Status.INVALID
        assert "grammar_rejected" in {e.rule for e in r.evidence}

    def test_grammar_rejects_non_atext_in_local_part(self) -> None:
        c = _cap()
        r = c.canonicalize("user,name@example.com", _contract())
        assert r.status is Status.INVALID
        assert "grammar_rejected" in {e.rule for e in r.evidence}

    def test_grammar_accepts_single_label_domain(self) -> None:
        # RFC 1035 §2.3.1: a single label is valid.
        c = _cap()
        r = c.canonicalize("user@localhost", _contract())
        assert r.status is Status.CANONICALIZED
        assert r.value == "user@localhost"

    def test_grammar_accepts_special_atext_chars(self) -> None:
        # RFC 5322 §3.2.3: atext includes !#$%&'*+-/=?^_`{|}~
        c = _cap()
        special = "!#$%&'*+-/=?^_`{|}~"
        r = c.canonicalize(f"{special}@example.com", _contract())
        assert r.status is Status.CANONICALIZED

    def test_grammar_accepts_internal_hyphen_in_domain_label(self) -> None:
        c = _cap()
        r = c.canonicalize("user@my-host.example.com", _contract())
        assert r.status is Status.CANONICALIZED
        assert r.value == "user@my-host.example.com"


class TestLaw14ProvenanceManifest:
    """Audit the `_RULE_PROVENANCE` manifest against the capability source.

    Mandate §10.2: a reviewer gate. Mandate Law 14 §3.6: two dispatch
    invariants are allow-listed with empty provenance; every *other* rule
    in the manifest must carry a non-empty citation.
    """

    _DISPATCH_INVARIANTS = frozenset({"not_an_email_contract", "not_a_string_value"})

    def test_every_manifest_entry_beyond_dispatch_has_provenance(self) -> None:
        for rule_name, provenance in _RULE_PROVENANCE.items():
            if rule_name in self._DISPATCH_INVARIANTS:
                continue
            assert provenance != "", (
                f"Law 14 violation: manifest entry {rule_name!r} has empty provenance"
            )

    def test_dispatch_invariants_are_allow_listed_with_empty_provenance(self) -> None:
        for invariant in self._DISPATCH_INVARIANTS:
            assert invariant in _RULE_PROVENANCE, (
                f"dispatch invariant {invariant!r} missing from manifest"
            )
            assert _RULE_PROVENANCE[invariant] == "", (
                f"dispatch invariant {invariant!r} should have empty provenance"
            )

    def test_manifest_keys_cover_every_fired_rule(self) -> None:
        """Firing every capability code path (canonicalize, grammar
        rejection, gmail rewrite, strict rejection) and asserting each
        fired Evidence rule is in the manifest — surfaces a code path
        that forgot to add a manifest entry.
        """
        c = _cap()
        contract = _contract()
        gmail = _contract(provider_aliases="gmail")
        strict = _contract(strict=True)
        inputs: list[tuple[object, Contract]] = [
            ("User@Example.COM", contract),
            ("  a@b.c  ", contract),
            ("user @example.com", contract),
            ("x@y.z", gmail),
            ("u.s.e.r+tag@googlemail.com", gmail),
            ("not-an-email", contract),
            ("a@b.c", strict),
            ("a b@c.d", strict),
            ("jöhn@example.com", strict),
        ]
        fired: set[str] = set()
        for value, contract in inputs:
            r = c.canonicalize(value, contract)
            for ev in r.evidence:
                fired.add(ev.rule)
        # Also exercise the two dispatch-invariant paths directly.
        from paxman._contracts.contract import CanonicalEmailContract

        not_contract: Contract = cast(Contract, "not_a_contract")
        r1 = c.canonicalize("a@b.c", not_contract)
        r2 = c.canonicalize(object(), cast(Contract, CanonicalEmailContract()))
        for ev in r1.evidence + r2.evidence:
            fired.add(ev.rule)
        for rule in fired:
            assert rule in _RULE_PROVENANCE, (
                f"fired rule {rule!r} missing from _RULE_PROVENANCE manifest"
            )
