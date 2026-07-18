"""Golden 100+-email regression corpus for Law 14 (canonical-form provenance).

Spec: `docs/superpowers/specs/
2026-07-13-email-canonicalization-design.md` §7.

This test pins the expected ``(Status, canonical value, set of evidence
rule names)`` for every entry in the corpus. Unlike the existing
``test_five_minute_100_emails.py`` (which only asserts status counts and
replay byte-equality), this test asserts the *exact* canonical value and
the *exact* evidence rule set. Any drift — even a single evidence rule
changing — blocks the merge.

Construction (100+ entries):
- 95 canonicalizable inputs from ``test_five_minute_100_emails.py`` (all
  valid dot-atom @ dot-atom forms → CANONICALIZED, exact values pinned).
- 5 invalid inputs from ``test_five_minute_100_emails.py`` (still
  INVALID).
- 9 user-experiment permissiveness cases surfaced on 2026-07-14 (now
  INVALID under ``grammar_rejected`` — the Law 14 recalibration).
- 18 additional grammar-boundary cases (valid special chars, single-label
  domains, IP-as-domain, quoted-strings, bracketed literals, overlong
  labels, unicode local parts, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

import paxman
from paxman import Email, _orchestrator_runtime
from paxman._capabilities.email import EmailCapability
from paxman._core.status import Status
from paxman._registry.capability_registry import CapabilityRegistry


@dataclass(frozen=True)
class _Entry:
    """One golden-corpus entry.

    Fields:
        input_email: the raw input string.
        contract_kwargs: kwargs for the ``Email()`` factory (empty =
            default contract).
        expected_status: the expected ``Status``.
        expected_value: the expected canonical value (``None`` for
            non-CANONICALIZED).
        expected_evidence_rules: the exact set of evidence rule names.
    """

    input_email: str
    contract_kwargs: dict[str, object]
    expected_status: Status
    expected_value: str | None
    expected_evidence_rules: frozenset[str]


_GMAIL: dict[str, object] = {"provider_aliases": "gmail"}
_STRICT: dict[str, object] = {"strict": True}

# --- 95 canonicalizable inputs (contract = Email(provider_aliases="gmail")) ---
_CANONICALIZABLE: list[_Entry] = [
    _Entry(
        "JOHN.DOE@Example.COM",
        _GMAIL,
        Status.CANONICALIZED,
        "john.doe@example.com",
        frozenset({"lowercased_domain", "lowercased_local_part"}),
    ),
    _Entry(
        "JANE.ROE@Example.COM",
        _GMAIL,
        Status.CANONICALIZED,
        "jane.roe@example.com",
        frozenset({"lowercased_domain", "lowercased_local_part"}),
    ),
    _Entry(
        "USER@DOMAIN.COM",
        _GMAIL,
        Status.CANONICALIZED,
        "user@domain.com",
        frozenset({"lowercased_domain", "lowercased_local_part"}),
    ),
    _Entry(
        "ALICE@ALICE.COM",
        _GMAIL,
        Status.CANONICALIZED,
        "alice@alice.com",
        frozenset({"lowercased_domain", "lowercased_local_part"}),
    ),
    _Entry(
        "BOB@BOB.COM",
        _GMAIL,
        Status.CANONICALIZED,
        "bob@bob.com",
        frozenset({"lowercased_domain", "lowercased_local_part"}),
    ),
    _Entry(
        "Test.User@Test.Org",
        _GMAIL,
        Status.CANONICALIZED,
        "test.user@test.org",
        frozenset({"lowercased_domain", "lowercased_local_part"}),
    ),
    _Entry(
        "ADMIN@Company.COM",
        _GMAIL,
        Status.CANONICALIZED,
        "admin@company.com",
        frozenset({"lowercased_domain", "lowercased_local_part"}),
    ),
    _Entry(
        "Sales@COMPANY.COM",
        _GMAIL,
        Status.CANONICALIZED,
        "sales@company.com",
        frozenset({"lowercased_domain", "lowercased_local_part"}),
    ),
    _Entry(
        "John.Doe@Example.COM",
        _GMAIL,
        Status.CANONICALIZED,
        "john.doe@example.com",
        frozenset({"lowercased_domain", "lowercased_local_part"}),
    ),
    _Entry(
        "Jane.Roe@Example.COM",
        _GMAIL,
        Status.CANONICALIZED,
        "jane.roe@example.com",
        frozenset({"lowercased_domain", "lowercased_local_part"}),
    ),
    _Entry(
        "A.B@C.D",
        _GMAIL,
        Status.CANONICALIZED,
        "a.b@c.d",
        frozenset({"lowercased_domain", "lowercased_local_part"}),
    ),
    _Entry(
        "X.Y@Z.W",
        _GMAIL,
        Status.CANONICALIZED,
        "x.y@z.w",
        frozenset({"lowercased_domain", "lowercased_local_part"}),
    ),
    _Entry(
        "Mixed@Case.Domain.COM",
        _GMAIL,
        Status.CANONICALIZED,
        "mixed@case.domain.com",
        frozenset({"lowercased_domain", "lowercased_local_part"}),
    ),
    _Entry(
        "UpperLower@Domain.Org",
        _GMAIL,
        Status.CANONICALIZED,
        "upperlower@domain.org",
        frozenset({"lowercased_domain", "lowercased_local_part"}),
    ),
    _Entry(
        "CamelCase@Test.Com",
        _GMAIL,
        Status.CANONICALIZED,
        "camelcase@test.com",
        frozenset({"lowercased_domain", "lowercased_local_part"}),
    ),
    _Entry(
        "PascalCase@Test.Com",
        _GMAIL,
        Status.CANONICALIZED,
        "pascalcase@test.com",
        frozenset({"lowercased_domain", "lowercased_local_part"}),
    ),
    _Entry(
        "email@DOMAIN.com",
        _GMAIL,
        Status.CANONICALIZED,
        "email@domain.com",
        frozenset({"lowercased_domain"}),
    ),
    _Entry(
        "USER.Name@Domain.COM",
        _GMAIL,
        Status.CANONICALIZED,
        "user.name@domain.com",
        frozenset({"lowercased_domain", "lowercased_local_part"}),
    ),
    _Entry(
        "First.Last@Example.COM",
        _GMAIL,
        Status.CANONICALIZED,
        "first.last@example.com",
        frozenset({"lowercased_domain", "lowercased_local_part"}),
    ),
    _Entry(
        "Middle.Name@Test.Org",
        _GMAIL,
        Status.CANONICALIZED,
        "middle.name@test.org",
        frozenset({"lowercased_domain", "lowercased_local_part"}),
    ),
    _Entry(
        "  john.doe@example.com",
        _GMAIL,
        Status.CANONICALIZED,
        "john.doe@example.com",
        frozenset({"stripped_whitespace"}),
    ),
    _Entry(
        "jane.roe@example.com  ",
        _GMAIL,
        Status.CANONICALIZED,
        "jane.roe@example.com",
        frozenset({"stripped_whitespace"}),
    ),
    _Entry(
        "  user@domain.com  ",
        _GMAIL,
        Status.CANONICALIZED,
        "user@domain.com",
        frozenset({"stripped_whitespace"}),
    ),
    _Entry(
        "\talice@alice.com",
        _GMAIL,
        Status.CANONICALIZED,
        "alice@alice.com",
        frozenset({"stripped_whitespace"}),
    ),
    _Entry(
        "bob@bob.com\t",
        _GMAIL,
        Status.CANONICALIZED,
        "bob@bob.com",
        frozenset({"stripped_whitespace"}),
    ),
    _Entry(
        "\nTest.User@Test.Org",
        _GMAIL,
        Status.CANONICALIZED,
        "test.user@test.org",
        frozenset({"stripped_whitespace", "lowercased_domain", "lowercased_local_part"}),
    ),
    _Entry(
        "ADMIN@Company.COM\n",
        _GMAIL,
        Status.CANONICALIZED,
        "admin@company.com",
        frozenset({"stripped_whitespace", "lowercased_domain", "lowercased_local_part"}),
    ),
    _Entry(
        " Sales@COMPANY.COM ",
        _GMAIL,
        Status.CANONICALIZED,
        "sales@company.com",
        frozenset({"stripped_whitespace", "lowercased_domain", "lowercased_local_part"}),
    ),
    _Entry(
        "  John.Doe@Example.COM  ",
        _GMAIL,
        Status.CANONICALIZED,
        "john.doe@example.com",
        frozenset({"stripped_whitespace", "lowercased_domain", "lowercased_local_part"}),
    ),
    _Entry(
        "\tJane.Roe@Example.COM\t",
        _GMAIL,
        Status.CANONICALIZED,
        "jane.roe@example.com",
        frozenset({"stripped_whitespace", "lowercased_domain", "lowercased_local_part"}),
    ),
    _Entry(
        "  hello@world.org",
        _GMAIL,
        Status.CANONICALIZED,
        "hello@world.org",
        frozenset({"stripped_whitespace"}),
    ),
    _Entry(
        "hello@world.org  ",
        _GMAIL,
        Status.CANONICALIZED,
        "hello@world.org",
        frozenset({"stripped_whitespace"}),
    ),
    _Entry(
        "\rfoo@bar.com",
        _GMAIL,
        Status.CANONICALIZED,
        "foo@bar.com",
        frozenset({"stripped_whitespace"}),
    ),
    _Entry(
        "foo@bar.com\r",
        _GMAIL,
        Status.CANONICALIZED,
        "foo@bar.com",
        frozenset({"stripped_whitespace"}),
    ),
    _Entry(
        " \tpadded@domain.com\t ",
        _GMAIL,
        Status.CANONICALIZED,
        "padded@domain.com",
        frozenset({"stripped_whitespace"}),
    ),
    _Entry(
        "\n\tindented@x.org\t\n",
        _GMAIL,
        Status.CANONICALIZED,
        "indented@x.org",
        frozenset({"stripped_whitespace"}),
    ),
    _Entry(
        "  middle.space@example.org   ",
        _GMAIL,
        Status.CANONICALIZED,
        "middle.space@example.org",
        frozenset({"stripped_whitespace"}),
    ),
    _Entry(
        "\ttrim.me@x.y\t",
        _GMAIL,
        Status.CANONICALIZED,
        "trim.me@x.y",
        frozenset({"stripped_whitespace"}),
    ),
    _Entry(
        "  even.more@spaced.com  ",
        _GMAIL,
        Status.CANONICALIZED,
        "even.more@spaced.com",
        frozenset({"stripped_whitespace"}),
    ),
    _Entry(
        "\r\nwrap@x.y\r\n",
        _GMAIL,
        Status.CANONICALIZED,
        "wrap@x.y",
        frozenset({"stripped_whitespace"}),
    ),
    _Entry("someone@gmail.com", _GMAIL, Status.CANONICALIZED, "someone@gmail.com", frozenset()),
    _Entry("person@gmail.com", _GMAIL, Status.CANONICALIZED, "person@gmail.com", frozenset()),
    _Entry(
        "user@googlemail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "user@gmail.com",
        frozenset({"domain_synonym_gmail"}),
    ),
    _Entry(
        "customer@googlemail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "customer@gmail.com",
        frozenset({"domain_synonym_gmail"}),
    ),
    _Entry("buyer@gmail.com", _GMAIL, Status.CANONICALIZED, "buyer@gmail.com", frozenset()),
    _Entry(
        "subscriber@gmail.com", _GMAIL, Status.CANONICALIZED, "subscriber@gmail.com", frozenset()
    ),
    _Entry(
        "member@googlemail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "member@gmail.com",
        frozenset({"domain_synonym_gmail"}),
    ),
    _Entry("client@gmail.com", _GMAIL, Status.CANONICALIZED, "client@gmail.com", frozenset()),
    _Entry(
        "someone@googlemail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "someone@gmail.com",
        frozenset({"domain_synonym_gmail"}),
    ),
    _Entry("user2@gmail.com", _GMAIL, Status.CANONICALIZED, "user2@gmail.com", frozenset()),
    _Entry(
        "client2@googlemail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "client2@gmail.com",
        frozenset({"domain_synonym_gmail"}),
    ),
    _Entry(
        "gmail_user@gmail.com", _GMAIL, Status.CANONICALIZED, "gmail_user@gmail.com", frozenset()
    ),
    _Entry(
        "googlemail_user@googlemail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "googlemail_user@gmail.com",
        frozenset({"domain_synonym_gmail"}),
    ),
    _Entry(
        "john.doe@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "johndoe@gmail.com",
        frozenset({"stripped_dots_in_local_part"}),
    ),
    _Entry(
        "jane.roe@googlemail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "janeroe@gmail.com",
        frozenset({"domain_synonym_gmail", "stripped_dots_in_local_part"}),
    ),
    _Entry("sender@gmail.com", _GMAIL, Status.CANONICALIZED, "sender@gmail.com", frozenset()),
    _Entry(
        "recipient@googlemail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "recipient@gmail.com",
        frozenset({"domain_synonym_gmail"}),
    ),
    _Entry("mail@gmail.com", _GMAIL, Status.CANONICALIZED, "mail@gmail.com", frozenset()),
    _Entry(
        "letter@googlemail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "letter@gmail.com",
        frozenset({"domain_synonym_gmail"}),
    ),
    _Entry("note@gmail.com", _GMAIL, Status.CANONICALIZED, "note@gmail.com", frozenset()),
    _Entry(
        "user+newsletter@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "user@gmail.com",
        frozenset({"stripped_plus_tag"}),
    ),
    _Entry(
        "user+promotions@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "user@gmail.com",
        frozenset({"stripped_plus_tag"}),
    ),
    _Entry(
        "user+updates@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "user@gmail.com",
        frozenset({"stripped_plus_tag"}),
    ),
    _Entry(
        "someone+tag@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "someone@gmail.com",
        frozenset({"stripped_plus_tag"}),
    ),
    _Entry(
        "someone+filter@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "someone@gmail.com",
        frozenset({"stripped_plus_tag"}),
    ),
    _Entry(
        "person+label@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "person@gmail.com",
        frozenset({"stripped_plus_tag"}),
    ),
    _Entry(
        "person+work@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "person@gmail.com",
        frozenset({"stripped_plus_tag"}),
    ),
    _Entry(
        "customer+123@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "customer@gmail.com",
        frozenset({"stripped_plus_tag"}),
    ),
    _Entry(
        "buyer+abc@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "buyer@gmail.com",
        frozenset({"stripped_plus_tag"}),
    ),
    _Entry(
        "subscriber+xyz@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "subscriber@gmail.com",
        frozenset({"stripped_plus_tag"}),
    ),
    _Entry(
        "member+mail@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "member@gmail.com",
        frozenset({"stripped_plus_tag"}),
    ),
    _Entry(
        "client+sort@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "client@gmail.com",
        frozenset({"stripped_plus_tag"}),
    ),
    _Entry(
        "gmail_user+anything@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "gmail_user@gmail.com",
        frozenset({"stripped_plus_tag"}),
    ),
    _Entry(
        "john.doe+tag@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "johndoe@gmail.com",
        frozenset({"stripped_plus_tag", "stripped_dots_in_local_part"}),
    ),
    _Entry(
        "jane.roe+filter@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "janeroe@gmail.com",
        frozenset({"stripped_plus_tag", "stripped_dots_in_local_part"}),
    ),
    _Entry(
        "sender+newsletter@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "sender@gmail.com",
        frozenset({"stripped_plus_tag"}),
    ),
    _Entry(
        "recipient+promo@googlemail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "recipient@gmail.com",
        frozenset({"stripped_plus_tag", "domain_synonym_gmail"}),
    ),
    _Entry(
        "mail+updates@googlemail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "mail@gmail.com",
        frozenset({"stripped_plus_tag", "domain_synonym_gmail"}),
    ),
    _Entry(
        "letter+blog@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "letter@gmail.com",
        frozenset({"stripped_plus_tag"}),
    ),
    _Entry(
        "note+alerts@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "note@gmail.com",
        frozenset({"stripped_plus_tag"}),
    ),
    _Entry(
        "j.o.h.n@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "john@gmail.com",
        frozenset({"stripped_dots_in_local_part"}),
    ),
    _Entry(
        "j.a.n.e@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "jane@gmail.com",
        frozenset({"stripped_dots_in_local_part"}),
    ),
    _Entry(
        "a.l.i.c.e@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "alice@gmail.com",
        frozenset({"stripped_dots_in_local_part"}),
    ),
    _Entry(
        "u.s.e.r@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "user@gmail.com",
        frozenset({"stripped_dots_in_local_part"}),
    ),
    _Entry(
        "d.o.t.s@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "dots@gmail.com",
        frozenset({"stripped_dots_in_local_part"}),
    ),
    _Entry(
        "m.a.n.y.d.o.t.s@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "manydots@gmail.com",
        frozenset({"stripped_dots_in_local_part"}),
    ),
    _Entry(
        "s.o.m.e.o.n.e@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "someone@gmail.com",
        frozenset({"stripped_dots_in_local_part"}),
    ),
    _Entry(
        "p.e.r.s.o.n@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "person@gmail.com",
        frozenset({"stripped_dots_in_local_part"}),
    ),
    _Entry(
        "c.u.s.t.o.m.e.r@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "customer@gmail.com",
        frozenset({"stripped_dots_in_local_part"}),
    ),
    _Entry(
        "b.u.y.e.r@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "buyer@gmail.com",
        frozenset({"stripped_dots_in_local_part"}),
    ),
    _Entry(
        "s.u.b.s.c.r.i.b.e.r@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "subscriber@gmail.com",
        frozenset({"stripped_dots_in_local_part"}),
    ),
    _Entry(
        "m.e.m.b.e.r@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "member@gmail.com",
        frozenset({"stripped_dots_in_local_part"}),
    ),
    _Entry(
        "c.l.i.e.n.t@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "client@gmail.com",
        frozenset({"stripped_dots_in_local_part"}),
    ),
    _Entry(
        "j.o.h.n.d.o.e@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "johndoe@gmail.com",
        frozenset({"stripped_dots_in_local_part"}),
    ),
    _Entry(
        "j.a.n.e.r.o.e@gmail.com",
        _GMAIL,
        Status.CANONICALIZED,
        "janeroe@gmail.com",
        frozenset({"stripped_dots_in_local_part"}),
    ),
]

# --- 5 invalid (from test_five_minute_100_emails.py) ---
_INVALID: list[_Entry] = [
    _Entry("not.an.email", {}, Status.INVALID, None, frozenset({"missing_at_sign"})),
    _Entry("@example.com", {}, Status.INVALID, None, frozenset({"empty_local_or_domain"})),
    _Entry("user@", {}, Status.INVALID, None, frozenset({"empty_local_or_domain"})),
    _Entry("  a@b.c  ", _STRICT, Status.INVALID, None, frozenset({"strict_rejected_whitespace"})),
    _Entry(
        "jöhn@example.com", _STRICT, Status.INVALID, None, frozenset({"strict_rejected_non_ascii"})
    ),
]

# --- 9 user-experiment permissiveness cases (Law 14 recalibration) ---
_PERMISSIVENESS: list[_Entry] = [
    _Entry(
        "user @example.com",
        {},
        Status.CANONICALIZED,
        "user@example.com",
        frozenset({"collapsed_internal_whitespace"}),
    ),
    _Entry(
        "user@ example.com",
        {},
        Status.CANONICALIZED,
        "user@example.com",
        frozenset({"collapsed_internal_whitespace"}),
    ),
    _Entry("user..name@example.com", {}, Status.INVALID, None, frozenset({"grammar_rejected"})),
    _Entry("user@[127.0.0.300]", {}, Status.INVALID, None, frozenset({"grammar_rejected"})),
    _Entry("user@[127.0.0.1", {}, Status.INVALID, None, frozenset({"grammar_rejected"})),
    _Entry("(comment)user@example.com", {}, Status.INVALID, None, frozenset({"grammar_rejected"})),
    _Entry("user@example.com/", {}, Status.INVALID, None, frozenset({"grammar_rejected"})),
    _Entry(
        "user@example.com@example.com", {}, Status.INVALID, None, frozenset({"unrecognized_format"})
    ),
    _Entry("user@-domain.com", {}, Status.INVALID, None, frozenset({"grammar_rejected"})),
]

# --- 18 additional grammar-boundary cases ---
_GRAMMAR_BOUNDARY: list[_Entry] = [
    # Valid single-label domain (RFC 1035 §2.3.1 allows it)
    _Entry("user@localhost", {}, Status.CANONICALIZED, "user@localhost", frozenset()),
    # Valid atext special chars in local part (RFC 5322 §3.2.3)
    _Entry(
        "!#$%&'*+-/=?^_`{|}~@example.com",
        {},
        Status.CANONICALIZED,
        "!#$%&'*+-/=?^_`{|}~@example.com",
        frozenset(),
    ),
    # IP address as domain — valid dot-atom under RFC 1035 (digits are LDH)
    _Entry("user@127.0.0.1", {}, Status.CANONICALIZED, "user@127.0.0.1", frozenset()),
    # Emoji domain — non-LDH, grammar_rejected
    _Entry("user@😊.com", {}, Status.INVALID, None, frozenset({"grammar_rejected"})),
    # Leading/trailing dots in local part — grammar_rejected
    _Entry(".user@example.com", {}, Status.INVALID, None, frozenset({"grammar_rejected"})),
    _Entry("user.@example.com", {}, Status.INVALID, None, frozenset({"grammar_rejected"})),
    # Leading/trailing dots in domain — grammar_rejected
    _Entry("user@.example.com", {}, Status.INVALID, None, frozenset({"grammar_rejected"})),
    _Entry("user@example.com.", {}, Status.INVALID, None, frozenset({"grammar_rejected"})),
    # Overlong label (64 chars) — grammar_rejected (RFC 1035 §2.3.1 max 63)
    _Entry("user@" + "a" * 64 + ".com", {}, Status.INVALID, None, frozenset({"grammar_rejected"})),
    # Consecutive dots in domain — grammar_rejected
    _Entry("user@example..com", {}, Status.INVALID, None, frozenset({"grammar_rejected"})),
    # Quoted-string local part (RFC 5322 §3.2.4) — v2.0.0 out of scope
    _Entry('"user name"@example.com', {}, Status.INVALID, None, frozenset({"grammar_rejected"})),
    # Bracketed IPv4 domain literal (RFC 5321 §3.4.1) — v2.0.0 out of scope
    _Entry("user@[127.0.0.1]", {}, Status.INVALID, None, frozenset({"grammar_rejected"})),
    # Bracketed IPv6 domain literal (RFC 5321 §3.4.2) — v2.0.0 out of scope
    _Entry(
        "user@[IPv6:2001:db8::1]",
        {},
        Status.INVALID,
        None,
        frozenset({"grammar_rejected"}),
    ),
    # Unicode local part — grammar_rejected (non-atext)
    _Entry("ü@ser.de", {}, Status.INVALID, None, frozenset({"grammar_rejected"})),
    # Double @ with empty local — empty_local_or_domain (partition yields empty local)
    _Entry("@user@example.com", {}, Status.INVALID, None, frozenset({"empty_local_or_domain"})),
    # Empty input — missing_at_sign
    _Entry("", {}, Status.INVALID, None, frozenset({"missing_at_sign"})),
    # Minimal valid email
    _Entry("a@b.c", {}, Status.CANONICALIZED, "a@b.c", frozenset()),
    # RFC 1035 label with internal hyphen — valid
    _Entry(
        "user@my-host.example.com",
        {},
        Status.CANONICALIZED,
        "user@my-host.example.com",
        frozenset(),
    ),
]

# --- recognition-layer cases (grammar + resolver + validation) ---
_RECOGNITION_LAYER: list[_Entry] = [
    # ws_padded grammar: internal whitespace around @ / . collapses.
    _Entry(
        "azahari @ gmail.com",
        {},
        Status.CANONICALIZED,
        "azahari@gmail.com",
        frozenset({"collapsed_internal_whitespace"}),
    ),
    # verbal 'at'/'dot' obfuscation deobfuscated to a canonical mailbox.
    _Entry(
        "azahari at gmail dot com",
        {},
        Status.CANONICALIZED,
        "azahari@gmail.com",
        frozenset({"deobfuscated_verbal_at_dot"}),
    ),
    # Gmail provider-equivalence yields two valid forms -> AMBIGUOUS.
    # Evidence unions both survivors' derivation rules (dot removal applies
    # to the gmail-canonical form) plus the ambiguity marker.
    _Entry(
        "john.doe@gmail.com",
        {},
        Status.AMBIGUOUS,
        None,
        frozenset({"stripped_dots_in_local_part", "ambiguous_provider_equivalence"}),
    ),
]

_ALL_ENTRIES: list[_Entry] = (
    _CANONICALIZABLE + _INVALID + _PERMISSIVENESS + _GRAMMAR_BOUNDARY + _RECOGNITION_LAYER
)


@pytest.fixture(autouse=True)
def _fresh_registry(monkeypatch: pytest.MonkeyPatch):
    """Fresh registry with EmailCapability registered and frozen."""
    r = CapabilityRegistry()
    r.register(EmailCapability())
    r.freeze()
    monkeypatch.setattr(_orchestrator_runtime, "default_registry", r)
    yield


class TestEmailLaw14Corpus:
    """Golden regression corpus — pins (status, value, evidence rules)
    for every entry. Any drift blocks the merge.
    """

    def test_corpus_has_100_plus_entries(self) -> None:
        assert len(_ALL_ENTRIES) >= 100, f"corpus must have 100+ entries; got {len(_ALL_ENTRIES)}"

    @pytest.mark.parametrize("entry", _ALL_ENTRIES)
    def test_corpus_entry_matches_golden(self, entry: _Entry) -> None:
        """Pin (status, value, evidence rule set) for every entry."""
        _kw: dict[str, Any] = entry.contract_kwargs
        contract = Email(**_kw) if _kw else Email()
        result = paxman.canonicalize(entry.input_email, contract)

        # Status must match exactly.
        assert result.status is entry.expected_status, (
            f"INPUT={entry.input_email!r} CONTRACT={entry.contract_kwargs!r}\n"
            f"  expected status: {entry.expected_status.name}\n"
            f"  actual status:   {result.status.name}\n"
            f"  evidence: {[(e.rule, e.detail) for e in result.evidence]}"
        )

        # Value must match exactly (None for non-CANONICALIZED).
        assert result.value == entry.expected_value, (
            f"INPUT={entry.input_email!r} CONTRACT={entry.contract_kwargs!r}\n"
            f"  expected value: {entry.expected_value!r}\n"
            f"  actual value:   {result.value!r}"
        )

        # Evidence rule set must match exactly.
        actual_rules = frozenset({e.rule for e in result.evidence})
        assert actual_rules == entry.expected_evidence_rules, (
            f"INPUT={entry.input_email!r} CONTRACT={entry.contract_kwargs!r}\n"
            f"  expected evidence rules: {sorted(entry.expected_evidence_rules)}\n"
            f"  actual evidence rules:   {sorted(actual_rules)}\n"
            f"  full evidence: {[(e.rule, e.detail, e.authority) for e in result.evidence]}"
        )

    def test_no_empty_provenance_except_dispatch_invariants(self) -> None:
        """Law 14 audit: every Evidence entry on every corpus artifact
        has non-empty ``provenance`` except the two allow-listed
        dispatch invariants (``not_an_email_contract``,
        ``not_a_string_value``).
        """
        allowlist = frozenset(
            {"not_an_email_contract", "not_a_string_value", "unrecognized_format"}
        )
        for entry in _ALL_ENTRIES:
            _kw: dict[str, Any] = entry.contract_kwargs
            contract = Email(**_kw) if _kw else Email()
            result = paxman.canonicalize(entry.input_email, contract)
            for ev in result.evidence:
                if ev.rule in allowlist:
                    continue
                assert ev.authority is not None, (
                    f"Law 14 violation: rule {ev.rule!r} on input "
                    f"{entry.input_email!r} has empty provenance."
                )

    def test_all_canonicalized_replay_byte_equal(self) -> None:
        """Law 12: every CANONICALIZED artifact replays byte-equal."""
        for entry in _ALL_ENTRIES:
            if entry.expected_status is not Status.CANONICALIZED:
                continue
            _kw: dict[str, Any] = entry.contract_kwargs
            contract = Email(**_kw) if _kw else Email()
            result = paxman.canonicalize(entry.input_email, contract)
            rehydrated = paxman.replay(result, contract)
            assert rehydrated == result, (
                f"replay drift for {entry.input_email!r}: "
                f"{rehydrated.canonical_bytes()!r} != "
                f"{result.canonical_bytes()!r}"
            )
            assert rehydrated.canonical_bytes() == result.canonical_bytes()
