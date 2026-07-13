"""Tests for the EmailCapability.

These tests assert the v1.0.0 default behaviour:
- Default: lowercase + strip whitespace, no provider rules.
- `provider_aliases='gmail'`: strip +tag and dots for gmail.com / googlemail.com.
- `strict=True`: reject non-RFC-5321 grammar (no spaces).
- Idempotent (mandate Law 2).
- Pure function (mandate Law 8a).
"""
from __future__ import annotations

from typing import Any, cast

import pytest

from paxman._capabilities.builtins.email import EmailCapability
from paxman._contracts.contract import CanonicalEmailContract, Contract
from paxman._core.types import CapabilityResult, Evidence, Status


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
        r = c.canonicalize(
            "user+tag@gmail.com", _contract(provider_aliases="gmail")
        )
        assert r.value == "user@gmail.com"

    def test_gmail_alias_strips_dots(self) -> None:
        c = _cap()
        r = c.canonicalize(
            "u.s.e.r@gmail.com", _contract(provider_aliases="gmail")
        )
        assert r.value == "user@gmail.com"

    def test_gmail_alias_normalizes_googlemail_to_gmail(self) -> None:
        c = _cap()
        r = c.canonicalize(
            "user@googlemail.com", _contract(provider_aliases="gmail")
        )
        assert r.value == "user@gmail.com"

    def test_gmail_alias_case_insensitive_domain(self) -> None:
        # Mandate Law 1 + casefold: Gmail rule applies regardless of
        # domain casing, even when `lowercase=False`.
        c = _cap()
        r = c.canonicalize(
            "user@GMAIL.COM", _contract(provider_aliases="gmail", lowercase=False)
        )
        assert r.value == "user@gmail.com"

    def test_gmail_alias_does_not_apply_to_non_gmail_domains(self) -> None:
        c = _cap()
        r = c.canonicalize(
            "u.s.e.r+tag@example.com", _contract(provider_aliases="gmail")
        )
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
