"""Tests for the Email() domain-type factory (spec §2.2).

MANDATE §4: the contract is the user's language; the capability is
Paxman's language. Email() is user vocabulary; EmailCapability is SPI.
Email() returns a configured CanonicalEmailContract value object — not a
subclass — so all isinstance checks and @attrs.frozen immutability are
inherited from the existing value object (Law 13, Law 5).
"""

from __future__ import annotations

import attrs
import pytest

from paxman import Email
from paxman._contracts.contract import CanonicalEmailContract


class TestEmailFactory:
    def test_email_returns_canonical_email_contract_instance(self) -> None:
        result = Email()
        assert isinstance(result, CanonicalEmailContract)

    def test_email_defaults_match_contract_defaults(self) -> None:
        # The four factory defaults MUST exactly mirror CanonicalEmailContract's
        # own field defaults (spec §2.2 — defaults invariant).
        assert Email().strict == CanonicalEmailContract().strict
        assert Email().provider_aliases == CanonicalEmailContract().provider_aliases
        assert Email().lowercase == CanonicalEmailContract().lowercase
        assert Email().strip_whitespace == CanonicalEmailContract().strip_whitespace

    def test_email_defaults_are_explicit(self) -> None:
        # Law 7 (Explicit Over Clever): the defaults are explicit values
        # recorded in the factory signature, not "hoped" from the callee.
        assert Email().strict is False
        assert Email().provider_aliases == "none"
        assert Email().lowercase is True
        assert Email().strip_whitespace is True

    def test_email_accepts_all_four_kwargs(self) -> None:
        result = Email(
            strict=True, provider_aliases="gmail", lowercase=False, strip_whitespace=False
        )
        assert result.strict is True
        assert result.provider_aliases == "gmail"
        assert result.lowercase is False
        assert result.strip_whitespace is False

    def test_email_kwargs_are_keyword_only(self) -> None:
        # The '*' in the signature enforces keyword-only. A positional
        # call must raise TypeError.
        with pytest.raises(TypeError):
            Email(True)  # type: ignore[call-arg]

    def test_email_result_is_immutable(self) -> None:
        # Law 13: the returned contract is @attrs.frozen. Assignment
        # must raise FrozenInstanceError.
        result = Email()
        with pytest.raises(attrs.exceptions.FrozenInstanceError):
            result.strict = True  # type: ignore[misc]

    def test_email_with_gmail_aliases(self) -> None:
        # A common Quickstart form (spec §3.1).
        result = Email(provider_aliases="gmail")
        assert result.provider_aliases == "gmail"

    def test_email_factory_is_reexported_from_paxman(self) -> None:
        # Spec §6: Email is the ONE new symbol in paxman.__all__.
        import paxman

        assert hasattr(paxman, "Email")
        assert paxman.Email is Email
