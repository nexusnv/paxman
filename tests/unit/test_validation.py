"""Tests for the post-capability validation step."""
from __future__ import annotations

import pytest

from paxman._core.validation import validate
from paxman._contracts.contract import CanonicalEmailContract


def _contract(**overrides: object) -> CanonicalEmailContract:
    defaults: dict[str, object] = dict(
        lowercase=True,
        strip_whitespace=True,
        provider_aliases="none",
        strict=False,
    )
    defaults.update(overrides)
    return CanonicalEmailContract(**defaults)  # type: ignore[arg-type]


class TestValidate:
    def test_simple_email_is_valid_in_default_mode(self) -> None:
        assert validate("a@b.c", _contract()).is_valid is True

    def test_empty_value_is_invalid(self) -> None:
        assert validate("", _contract()).is_valid is False

    def test_value_with_at_sign_is_required(self) -> None:
        assert validate("noatsign", _contract()).is_valid is False

    def test_strict_mode_rejects_embedded_space(self) -> None:
        assert (
            validate("a b@c.d", _contract(strict=True)).is_valid is False
        )

    def test_non_strict_mode_accepts_embedded_space(self) -> None:
        # Non-strict: only the @-sign requirement is enforced.
        assert validate("a b@c.d", _contract(strict=False)).is_valid is True

    def test_local_part_must_be_non_empty(self) -> None:
        assert validate("@b.c", _contract()).is_valid is False

    def test_domain_must_be_non_empty(self) -> None:
        assert validate("a@", _contract()).is_valid is False
