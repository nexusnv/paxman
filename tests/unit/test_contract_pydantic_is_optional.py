"""Tests for issues #62 and #58 — ``_is_optional()`` PEP 604 detection + ``_adapt_field`` order.

#62: The PEP 604 branch of ``_is_optional`` must use ``origin is types.UnionType``
(identity check), not a fragile ``__name__`` string comparison.

#58: ``_adapt_field`` must call ``_is_optional`` before ``_unwrap_annotated`` so that
``Optional[Annotated[int, Field(ge=0)]]`` produces a field (not UNSUPPORTED_FIELD_TYPE).
"""

from __future__ import annotations

from typing import Annotated, Optional, Union
from unittest import mock

import pytest
from pydantic import BaseModel, Field

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


@pytest.mark.unit
class TestAdaptFieldOptionalAnnotated:
    """Tests for issue #58 — ``Optional[Annotated[T, ...]]`` must produce a field."""

    def test_optional_annotated_int_adapts_to_integer_field(self) -> None:
        """The end-to-end contract: ``Optional[Annotated[int, Field(ge=0)]]``
        must adapt to a CanonicalField with type=INTEGER and nullable=True.

        Note: Pydantic v2 stores ``Ge(ge=0)`` inside the ``Annotated`` wrapper
        (not in ``field_info.metadata``) when ``Optional`` is outer, so the
        constraint is not visible to ``_constraints_from_field``. This is a
        known limitation; the critical fix here is that the field is *accepted*
        (type is detected) rather than raising ``UNSUPPORTED_FIELD_TYPE``.
        """
        from paxman.contract.adapters.pydantic import PydanticAdapter

        class M(BaseModel):
            x: Optional[Annotated[int, Field(ge=0)]] = None

        contract = PydanticAdapter().adapt(M)
        assert len(contract.fields) == 1
        field = contract.fields[0]
        assert field.name == "x"
        assert field.type.name == "INTEGER"
        assert field.nullable is True

    def test_pep_604_optional_annotated_int_adapts_to_integer_field(self) -> None:
        """PEP 604 syntax equivalent: ``Annotated[int, ...] | None``."""
        from paxman.contract.adapters.pydantic import PydanticAdapter

        class M(BaseModel):
            x: Annotated[int, Field(ge=0)] | None = None

        contract = PydanticAdapter().adapt(M)
        assert len(contract.fields) == 1
        field = contract.fields[0]
        assert field.type.name == "INTEGER"
        assert field.nullable is True

    def test_typing_union_annotated_with_none_adapts(self) -> None:
        """The original failure mode in #58: ``Union[Annotated[int, ...], None]``."""
        from paxman.contract.adapters.pydantic import PydanticAdapter

        class M(BaseModel):
            x: Union[Annotated[int, Field(ge=0)], None] = None

        contract = PydanticAdapter().adapt(M)
        assert len(contract.fields) == 1
        field = contract.fields[0]
        assert field.type.name == "INTEGER"
        assert field.nullable is True
