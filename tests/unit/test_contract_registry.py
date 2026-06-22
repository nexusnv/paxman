"""Unit tests for ``paxman.contract.registry`` — adapter lookup by ``format_id``.

The registry is process-local: adapters self-register on import, and
the public ``register_adapter()`` API lands in Sprint 6. These tests
cover the current internal API and verify that all three Sprint 2
adapters are registered after their modules are imported.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from paxman.contract import registry
from paxman.contract.adapters.base import ContractAdapter
from paxman.contract.adapters.dict_dsl import DictDSLAdapter
from paxman.errors import InvalidContractError


@pytest.fixture
def isolated_registry() -> Iterator[None]:
    """Snapshot the registry, restore after the test.

    Several tests register custom adapters; we don't want to leak them
    into other tests.
    """
    saved = dict(registry._adapters)  # type: ignore[attr-defined]
    yield
    registry._adapters.clear()  # type: ignore[attr-defined]
    registry._adapters.update(saved)  # type: ignore[attr-defined]


# --- Registered adapters after import ---------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_dict_dsl_adapter_is_registered() -> None:
    """The Dict DSL adapter is registered on import (D2.9 / D2.5)."""
    import paxman.contract.adapters.dict_dsl  # noqa: F401

    assert "dict_dsl" in registry.all_adapters()


@pytest.mark.deterministic
@pytest.mark.unit
def test_pydantic_adapter_is_registered() -> None:
    """The Pydantic adapter is registered on import (D2.7)."""
    import paxman.contract.adapters.pydantic  # noqa: F401

    assert "pydantic" in registry.all_adapters()


@pytest.mark.deterministic
@pytest.mark.unit
def test_json_schema_adapter_is_registered() -> None:
    """The JSON Schema adapter is registered on import (D2.8)."""
    import paxman.contract.adapters.json_schema  # noqa: F401

    assert "json_schema:draft-2020-12" in registry.all_adapters()


@pytest.mark.deterministic
@pytest.mark.unit
def test_all_three_v1_adapters_registered() -> None:
    """All 3 V1 required adapters are registered (Sprint 2 exit criterion)."""
    import paxman.contract.adapters.dict_dsl
    import paxman.contract.adapters.json_schema
    import paxman.contract.adapters.pydantic  # noqa: F401

    fmts = set(registry.all_adapters().keys())
    assert {"dict_dsl", "pydantic", "json_schema:draft-2020-12"} <= fmts


# --- register / unregister ---------------------------------------------------


@pytest.mark.unit
def test_register_and_get_adapter(isolated_registry: None) -> None:
    """A registered adapter is retrievable by format_id."""

    class _MyAdapter:
        @property
        def format_id(self) -> str:
            return "my_format"

        def adapt(self, external: object) -> object:  # type: ignore[override]
            return external

        def export(self, canonical: object) -> object:  # type: ignore[override]
            return canonical

    adapter: ContractAdapter = _MyAdapter()  # type: ignore[assignment]
    registry.register(adapter)
    assert registry.get_adapter("my_format") is adapter


@pytest.mark.unit
def test_register_replaces_with_replace_flag(isolated_registry: None) -> None:
    """``replace=True`` lets a new adapter supersede an existing one."""

    class _A1:
        @property
        def format_id(self) -> str:
            return "x"

        def adapt(self, external: object) -> object:  # type: ignore[override]
            return "a1"

        def export(self, canonical: object) -> object:  # type: ignore[override]
            return canonical

    class _A2:
        @property
        def format_id(self) -> str:
            return "x"

        def adapt(self, external: object) -> object:  # type: ignore[override]
            return "a2"

        def export(self, canonical: object) -> object:  # type: ignore[override]
            return canonical

    registry.register(_A1())  # type: ignore[arg-type]
    registry.register(_A2(), replace=True)  # type: ignore[arg-type]
    assert registry.get_adapter("x").adapt(None) == "a2"


@pytest.mark.unit
def test_register_duplicate_without_replace_raises(isolated_registry: None) -> None:
    """Duplicate registration without ``replace=True`` raises."""

    class _A:
        @property
        def format_id(self) -> str:
            return "dup_test_format"

        def adapt(self, external: object) -> object:  # type: ignore[override]
            return None

        def export(self, canonical: object) -> object:  # type: ignore[override]
            return None

    registry.register(_A())  # type: ignore[arg-type]
    with pytest.raises(InvalidContractError, match="already registered"):
        registry.register(_A())  # type: ignore[arg-type]


@pytest.mark.unit
def test_register_missing_format_id_raises(isolated_registry: None) -> None:
    """An adapter with no ``format_id`` raises TypeError."""

    class _NoFmt:
        def adapt(self, external: object) -> object:  # type: ignore[override]
            return None

        def export(self, canonical: object) -> object:  # type: ignore[override]
            return None

    with pytest.raises(TypeError, match="format_id"):
        registry.register(_NoFmt())  # type: ignore[arg-type]


@pytest.mark.unit
def test_register_empty_format_id_raises(isolated_registry: None) -> None:
    """An adapter with empty ``format_id`` raises InvalidContractError."""

    class _EmptyFmt:
        @property
        def format_id(self) -> str:
            return ""

        def adapt(self, external: object) -> object:  # type: ignore[override]
            return None

        def export(self, canonical: object) -> object:  # type: ignore[override]
            return None

    with pytest.raises(InvalidContractError, match="format_id must be a non-empty string"):
        registry.register(_EmptyFmt())  # type: ignore[arg-type]


@pytest.mark.unit
def test_unregister_returns_true_when_removed(isolated_registry: None) -> None:
    """``unregister`` returns True when the adapter was present."""
    registry.register(DictDSLAdapter(), replace=True)
    assert registry.unregister("dict_dsl") is True


@pytest.mark.unit
def test_unregister_returns_false_when_missing(isolated_registry: None) -> None:
    """``unregister`` returns False when no adapter was registered."""
    assert registry.unregister("nonexistent") is False


# --- get_adapter -------------------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_get_adapter_unknown_raises_not_found() -> None:
    """``get_adapter`` raises InvalidContractError for unknown format_id."""
    with pytest.raises(InvalidContractError, match="no adapter registered"):
        registry.get_adapter("nonsense_format")


# --- all_adapters ------------------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_all_adapters_is_read_only() -> None:
    """``all_adapters`` returns a read-only mapping."""
    adapters = registry.all_adapters()
    with pytest.raises(TypeError):
        adapters["foo"] = None  # type: ignore[index]


@pytest.mark.deterministic
@pytest.mark.unit
def test_all_adapters_returns_current_snapshot() -> None:
    """``all_adapters`` reflects the current registered set."""
    import paxman.contract.adapters.dict_dsl  # noqa: F401

    assert "dict_dsl" in registry.all_adapters().keys()


# --- adapt -------------------------------------------------------------------


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_dispatches_to_dict_dsl() -> None:
    """``adapt`` with ``format_id="dict_dsl"`` calls the Dict DSL adapter."""
    import paxman.contract.adapters.dict_dsl  # noqa: F401

    contract = registry.adapt(
        {"id": "x", "fields": [{"name": "f", "type": "STRING", "required": True}]},
        format_id="dict_dsl",
    )
    assert contract.id == "x"


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_dispatches_to_pydantic() -> None:
    """``adapt`` with ``format_id="pydantic"`` calls the Pydantic adapter."""
    from pydantic import BaseModel

    import paxman.contract.adapters.pydantic  # noqa: F401

    class M(BaseModel):
        f: str

    contract = registry.adapt(M, format_id="pydantic")
    assert contract.id == "M"


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_dispatches_to_json_schema() -> None:
    """``adapt`` with ``format_id="json_schema:draft-2020-12"`` calls JSON Schema adapter."""
    import paxman.contract.adapters.json_schema  # noqa: F401

    contract = registry.adapt(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "X",
            "type": "object",
            "properties": {"f": {"type": "string"}},
            "required": ["f"],
        },
        format_id="json_schema:draft-2020-12",
    )
    assert contract.id == "X"


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_without_format_id_raises() -> None:
    """``adapt`` without a format_id raises (V1 does not infer)."""
    with pytest.raises(InvalidContractError, match="format_id is required"):
        registry.adapt({"x": 1})


@pytest.mark.deterministic
@pytest.mark.unit
def test_adapt_unknown_format_raises_not_found() -> None:
    """``adapt`` with an unknown format_id raises ADAPTER_NOT_FOUND."""
    with pytest.raises(InvalidContractError, match="no adapter registered"):
        registry.adapt({}, format_id="nonexistent_format_xyz")
