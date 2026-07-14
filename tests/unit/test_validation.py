"""Tests for the post-capability validation step."""

from __future__ import annotations

from typing import Any, cast

import pytest

from paxman._contracts.contract import CanonicalEmailContract
from paxman._core.validation import validate
from paxman._errors import UnsupportedContractError


class _UnsupportedContract:
    """A contract kind that validation.py does not handle (forward-compat)."""

    version_field = 1

    def as_dict(self) -> dict[str, object]:
        return {"kind": "canonical_widget"}


def _contract(**overrides: object) -> CanonicalEmailContract:
    defaults: dict[str, object] = dict(
        lowercase=True,
        strip_whitespace=True,
        provider_aliases="none",
        strict=False,
    )
    defaults.update(overrides)
    return CanonicalEmailContract(**cast(Any, defaults))


class TestValidate:
    def test_simple_email_is_valid_in_default_mode(self) -> None:
        assert validate("a@b.c", _contract()).is_valid is True

    def test_empty_value_is_invalid(self) -> None:
        assert validate("", _contract()).is_valid is False

    def test_value_with_at_sign_is_required(self) -> None:
        assert validate("noatsign", _contract()).is_valid is False

    def test_strict_mode_rejects_embedded_space(self) -> None:
        assert validate("a b@c.d", _contract(strict=True)).is_valid is False

    def test_non_strict_mode_accepts_embedded_space(self) -> None:
        # Non-strict: only the @-sign requirement is enforced.
        assert validate("a b@c.d", _contract(strict=False)).is_valid is True

    def test_local_part_must_be_non_empty(self) -> None:
        assert validate("@b.c", _contract()).is_valid is False

    def test_domain_must_be_non_empty(self) -> None:
        assert validate("a@", _contract()).is_valid is False

    def test_unsupported_contract_kind_raises(self) -> None:
        # A contract that is neither email, uuid, nor date is unsupported.
        with pytest.raises(UnsupportedContractError):
            validate("x", _UnsupportedContract())

    def test_strict_mode_accepts_ascii(self) -> None:
        assert validate("a@b.c", _contract(strict=True)).is_valid is True

    def test_strict_mode_rejects_non_ascii(self) -> None:
        # IDN/unicode local parts are out of scope in v2.0.0 (strict mode).
        assert validate("café@b.c", _contract(strict=True)).is_valid is False
