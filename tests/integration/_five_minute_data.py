"""Deterministic 100-email dataset for the 5-Minute Promise regression.

Spec §4.8: exactly 95 inputs canonicalize under Email(provider_aliases=
'gmail') and exactly 5 inputs are INVALID. The categorization is fixed
in-source — no random, no fixtures dir, no external file reads
(.coderabbit.yaml and PROPOSED_STRUCTURE.md both forbid tests/fixtures/).

Construction rules (95 canonicalizable):
- 20 lowercase mixed-case variants (e.g. 'JOHN.DOE@Example.COM').
- 20 ASCII whitespace-padded variants (e.g. '  jane.roe@Example.com  ',
  '\\tjohn@x.org\\n').
- 20 gmail.com <-> googlemail.com alias mappings under
  provider_aliases='gmail' (both 'gmail.com' and 'googlemail.com'
  should canonicalize to 'something@gmail.com').
- 20 plus-tag variants under provider_aliases='gmail' (e.g.
  'user+newsletter@gmail.com' -> 'user@gmail.com').
- 15 dot-ignoring variants under provider_aliases='gmail' (e.g.
  'j.o.h.n@gmail.com' -> 'john@gmail.com').

Construction rules (5 invalid):
- 1 missing '@' sign: 'not.an.email'.
- 1 empty local part: '@example.com'.
- 1 empty domain part: 'user@'.
- 1 non-ASCII character in local part: 'jöhn@example.com'.
- 1 leading/trailing whitespace under strict=True: '  a@b.c  ' with
  Email(strict=True).

The breakdown is 20+20+20+20+15 = 95 canonicalizable + 5 invalid = 100.
"""

from __future__ import annotations

# 95 canonicalizable inputs. All should produce Status.CANONICALIZED
# under Email(provider_aliases="gmail").
CANONICALIZABLE: list[str] = [
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

# 5 invalid inputs. The contract form used for each is noted in the
# test file because some require a non-default Email() kwarg.
INVALID: list[str] = [
    "not.an.email",        # missing '@' sign
    "@example.com",        # empty local part
    "user@",               # empty domain part
    "jöhn@example.com",    # non-ASCII character in local part
]

# Inputs that require a non-default contract form are kept separate so
# the test can build the matching Email() for each. This one is the
# strict=True whitespace rejection case.
STRICT_INVALID: list[tuple[str, dict[str, object]]] = [
    ("  a@b.c  ", {"strict": True}),
]


def all_canonicalizable_emails() -> list[str]:
    """Return the 95 inputs that should be Status.CANONICALIZED."""
    assert len(CANONICALIZABLE) == 95, (
        f"expected 95 canonicalizable, got {len(CANONICALIZABLE)}"
    )
    return list(CANONICALIZABLE)


def all_invalid_pairs() -> list[tuple[str, dict[str, object]]]:
    """Return the 5 inputs that should be Status.INVALID with their contracts."""
    invalid_with_contracts: list[tuple[str, dict[str, object]]] = [
        (email, {}) for email in INVALID
    ]
    invalid_with_contracts.extend(
        (email, contract_kwargs) for email, contract_kwargs in STRICT_INVALID
    )
    assert len(invalid_with_contracts) == 5, (
        f"expected 5 invalid, got {len(invalid_with_contracts)}"
    )
    return invalid_with_contracts
