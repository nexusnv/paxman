"""100-email regression for the 5-Minute Promise (spec §4.8).

Runs a deterministic 100-email dataset through paxman.canonicalize via
the README path. Asserts exactly 95 Status.CANONICALIZED and 5
Status.INVALID. All canonicalized artifacts round-trip through replay
byte-equal. The novice-did-nothing fixture is reused.

The dataset is inlined here as a one-off local fixture — no
tests/fixtures/ directory, no external file reads (path instructions
forbid tests reading from a path not under tests/, and forbid any
test reading data from outside tests/).
"""

from __future__ import annotations

from collections import Counter
from typing import Any

import pytest

import paxman
from paxman import Email, _orchestrator_runtime
from paxman._capabilities.registry import CapabilityRegistry
from paxman._core.types import Status

# ---------------------------------------------------------------------------
# Deterministic 100-email dataset (inlined as a one-off local fixture).
#
# Construction rules (95 canonicalizable):
# - 20 lowercase mixed-case variants (e.g. 'JOHN.DOE@Example.COM').
# - 20 ASCII whitespace-padded variants.
# - 20 gmail.com <-> googlemail.com alias mappings under
#   provider_aliases='gmail' (both domains canonicalize to gmail.com).
# - 20 plus-tag variants under provider_aliases='gmail' (the +tag is stripped).
# - 15 dot-ignoring variants under provider_aliases='gmail'.
#
# Construction rules (5 invalid):
# - 1 missing '@' sign: 'not.an.email'.
# - 1 empty local part: '@example.com'.
# - 1 empty domain part: 'user@'.
# - 2 strict-mode rejections: '  a@b.c  ' and 'jöhn@example.com' (each
#   requires Email(strict=True); the v2 EmailCapability only rejects
#   whitespace / non-ASCII when strict mode is active).
#
# The breakdown is 20+20+20+20+15 = 95 canonicalizable + 5 invalid = 100.
# ---------------------------------------------------------------------------
_CANONICALIZABLE: list[str] = [
    # 20 lowercase mixed-case variants.
    "JOHN.DOE@Example.COM",
    "JANE.ROE@Example.COM",
    "USER@DOMAIN.COM",
    "ALICE@ALICE.COM",
    "BOB@BOB.COM",
    "Test.User@Test.Org",
    "ADMIN@Company.COM",
    "Sales@COMPANY.COM",
    "John.Doe@Example.COM",
    "Jane.Roe@Example.COM",
    "A.B@C.D",
    "X.Y@Z.W",
    "Mixed@Case.Domain.COM",
    "UpperLower@Domain.Org",
    "CamelCase@Test.Com",
    "PascalCase@Test.Com",
    "email@DOMAIN.com",
    "USER.Name@Domain.COM",
    "First.Last@Example.COM",
    "Middle.Name@Test.Org",
    # 20 ASCII whitespace-padded variants.
    "  john.doe@example.com",
    "jane.roe@example.com  ",
    "  user@domain.com  ",
    "\talice@alice.com",
    "bob@bob.com\t",
    "\nTest.User@Test.Org",
    "ADMIN@Company.COM\n",
    " Sales@COMPANY.COM ",
    "  John.Doe@Example.COM  ",
    "\tJane.Roe@Example.COM\t",
    "  hello@world.org",
    "hello@world.org  ",
    "\rfoo@bar.com",
    "foo@bar.com\r",
    " \tpadded@domain.com\t ",
    "\n\tindented@x.org\t\n",
    "  middle.space@example.org   ",
    "\ttrim.me@x.y\t",
    "  even.more@spaced.com  ",
    "\r\nwrap@x.y\r\n",
    # 20 gmail.com <-> googlemail.com alias mappings.
    "someone@gmail.com",
    "person@gmail.com",
    "user@googlemail.com",
    "customer@googlemail.com",
    "buyer@gmail.com",
    "subscriber@gmail.com",
    "member@googlemail.com",
    "client@gmail.com",
    "someone@googlemail.com",
    "user2@gmail.com",
    "client2@googlemail.com",
    "gmail_user@gmail.com",
    "googlemail_user@googlemail.com",
    "john.doe@gmail.com",
    "jane.roe@googlemail.com",
    "sender@gmail.com",
    "recipient@googlemail.com",
    "mail@gmail.com",
    "letter@googlemail.com",
    "note@gmail.com",
    # 20 plus-tag variants (stripped under provider_aliases="gmail").
    "user+newsletter@gmail.com",
    "user+promotions@gmail.com",
    "user+updates@gmail.com",
    "someone+tag@gmail.com",
    "someone+filter@gmail.com",
    "person+label@gmail.com",
    "person+work@gmail.com",
    "customer+123@gmail.com",
    "buyer+abc@gmail.com",
    "subscriber+xyz@gmail.com",
    "member+mail@gmail.com",
    "client+sort@gmail.com",
    "gmail_user+anything@gmail.com",
    "john.doe+tag@gmail.com",
    "jane.roe+filter@gmail.com",
    "sender+newsletter@gmail.com",
    "recipient+promo@googlemail.com",
    "mail+updates@googlemail.com",
    "letter+blog@gmail.com",
    "note+alerts@gmail.com",
    # 15 dot-ignoring variants under provider_aliases="gmail".
    "j.o.h.n@gmail.com",
    "j.a.n.e@gmail.com",
    "a.l.i.c.e@gmail.com",
    "u.s.e.r@gmail.com",
    "d.o.t.s@gmail.com",
    "m.a.n.y.d.o.t.s@gmail.com",
    "s.o.m.e.o.n.e@gmail.com",
    "p.e.r.s.o.n@gmail.com",
    "c.u.s.t.o.m.e.r@gmail.com",
    "b.u.y.e.r@gmail.com",
    "s.u.b.s.c.r.i.b.e.r@gmail.com",
    "m.e.m.b.e.r@gmail.com",
    "c.l.i.e.n.t@gmail.com",
    "j.o.h.n.d.o.e@gmail.com",
    "j.a.n.e.r.o.e@gmail.com",
]
assert len(_CANONICALIZABLE) == 95, "internal error: canonicalizable list must be 95 entries"

# 5 invalid: 3 with default Email() contract, 2 that require strict=True.
# Each entry is (input_string, contract_kwargs_for_Email_factory).
_INVALID_PAIRS: list[tuple[str, dict[str, object]]] = [
    ("not.an.email", {}),  # missing '@' sign
    ("@example.com", {}),  # empty local part
    ("user@", {}),  # empty domain part
    ("  a@b.c  ", {"strict": True}),  # whitespace under strict mode
    ("jöhn@example.com", {"strict": True}),  # non-ASCII under strict mode
]
assert len(_INVALID_PAIRS) == 5, "internal error: invalid pairs must be 5 entries"


def _all_invalid_pairs() -> list[tuple[str, dict[str, object]]]:
    return list(_INVALID_PAIRS)


def _all_canonicalizable_emails() -> list[str]:
    return list(_CANONICALIZABLE)


@pytest.fixture(autouse=True)
def _fresh_empty_registry(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(_orchestrator_runtime, "default_registry", CapabilityRegistry())
    yield


class TestFiveMinute100Emails:
    def test_95_canonicalized(self) -> None:
        canonical_count = 0
        for email in _all_canonicalizable_emails():
            result = paxman.canonicalize(email, Email(provider_aliases="gmail"))
            if result.status is Status.CANONICALIZED:
                canonical_count += 1
            else:
                pytest.fail(
                    f"expected CANONICALIZED for {email!r}; got "
                    f"{result.status.name} with evidence "
                    f"{[(e.rule, e.detail) for e in result.evidence]}"
                )
        assert canonical_count == 95, f"expected 95 CANONICALIZED, got {canonical_count}"

    def test_5_invalid(self) -> None:
        invalid_count = 0
        for email, contract_kwargs in _all_invalid_pairs():
            _kwargs: dict[str, Any] = contract_kwargs
            contract = Email(**_kwargs) if _kwargs else Email()
            result = paxman.canonicalize(email, contract)
            if result.status is Status.INVALID:
                invalid_count += 1
            else:
                pytest.fail(
                    f"expected INVALID for {email!r} with contract "
                    f"{contract!r}; got {result.status.name} with value "
                    f"{result.value!r}"
                )
        assert invalid_count == 5, f"expected 5 INVALID, got {invalid_count}"

    def test_exactly_100_total(self) -> None:
        total = len(_all_canonicalizable_emails()) + len(_all_invalid_pairs())
        assert total == 100, f"expected 100 total, got {total}"

    def test_count_by_status_resilient_to_order(self) -> None:
        all_results: list[Status] = []
        for email in _all_canonicalizable_emails():
            result = paxman.canonicalize(email, Email(provider_aliases="gmail"))
            all_results.append(result.status)
        for email, contract_kwargs in _all_invalid_pairs():
            _kwargs: dict[str, Any] = contract_kwargs
            contract = Email(**_kwargs) if _kwargs else Email()
            result = paxman.canonicalize(email, contract)
            all_results.append(result.status)
        counts = Counter(all_results)
        assert counts[Status.CANONICALIZED] == 95
        assert counts[Status.INVALID] == 5
        assert sum(counts.values()) == 100

    def test_all_canonicalized_round_trip_replay(self) -> None:
        # Every canonicalized artifact must replay byte-equal (Law 12).
        for email in _all_canonicalizable_emails():
            contract = Email(provider_aliases="gmail")
            result = paxman.canonicalize(email, contract)
            if result.status is Status.CANONICALIZED:
                rehydrated = paxman.replay(result, contract)
                assert rehydrated == result, (
                    f"replay drift for {email!r}: "
                    f"{rehydrated.canonical_bytes()!r} != "
                    f"{result.canonical_bytes()!r}"
                )
                assert rehydrated.canonical_bytes() == result.canonical_bytes()
