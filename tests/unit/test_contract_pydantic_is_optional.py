"""Tests for issue #62 — ``_is_optional()`` PEP 604 detection robustness.

The PEP 604 branch of ``_is_optional`` must use ``origin is types.UnionType``
(identity check), not a fragile ``__name__`` string comparison.
"""

from __future__ import annotations

from typing import Annotated, Optional
from unittest import mock

import pytest
from pydantic import Field

from paxman.contract.adapters.pydantic import _is_optional


@pytest.mark.unit
class TestIsOptionalPEP604:
    """Regression tests for GitHub issue #62."""

    def test_detects_pep_604_union_with_none(self) -> None:
        """``int | None`` is detected as Optional with inner ``int``."""
        is_opt, inner = _is_optional(int | None)
        assert is_opt is True
        assert inner is int

    def test_detects_typing_optional(self) -> None:
        """``Optional[int]`` is detected as Optional with inner ``int``."""
        is_opt, inner = _is_optional(Optional[int])
        assert is_opt is True
        assert inner is int

    def test_non_optional_returns_false(self) -> None:
        """A bare ``int`` is not Optional."""
        is_opt, inner = _is_optional(int)
        assert is_opt is False
        assert inner is int

    def test_does_not_depend_on_uniontype_dunder_name(self) -> None:
        """Regression for #62: detection must not rely on ``__name__``.

        ``types.UnionType.__name__`` is immutable on CPython 3.13+ (C type),
        so we cannot monkey-patch it directly.  Instead we inject a fake origin
        via ``typing.get_origin`` that has ``__name__ == "UnionType"`` but is
        **not** the real ``types.UnionType`` singleton.

        * Before the fix (``__name__`` check): the fake is accepted →
          ``_is_optional`` returns ``(True, int)``.
        * After the fix (identity check): the fake is rejected →
          ``_is_optional`` returns ``(False, annotation)``.
        """

        class _FakeOrigin:
            """Mimics ``types.UnionType`` by name but not by identity."""

            __name__ = "UnionType"

        with mock.patch("typing.get_origin", return_value=_FakeOrigin()):
            is_opt, _inner = _is_optional(int | None)
            # The fake is NOT types.UnionType, so identity check rejects it.
            assert is_opt is False

    def test_pep_604_with_annotated_inner(self) -> None:
        """Combined with #58 fix (T2): ``Optional[Annotated[int, ...]]`` must work.

        Uses ``is`` identity because ``pydantic.FieldInfo`` does not implement
        ``__eq__``, making ``==`` unreliable on ``Annotated`` wrappers.
        """
        annotated = Annotated[int, Field(ge=0)]
        is_opt, inner = _is_optional(annotated | None)
        assert is_opt is True
        assert inner is annotated
