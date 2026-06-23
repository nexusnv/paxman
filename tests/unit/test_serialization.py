"""Unit tests for ``paxman.serialization`` — stable JSON encoder."""

from __future__ import annotations

import datetime
import decimal
import enum
import uuid

import attrs
import pytest

from paxman.serialization import stable_dump, stable_dumps, stable_load, stable_loads

# --- Basic types -------------------------------------------------------------


def test_dumps_dict_sorted_keys() -> None:
    """``stable_dumps`` returns sorted keys regardless of insertion order."""
    assert stable_dumps({"b": 1, "a": 2}) == '{"a":2,"b":1}'
    assert stable_dumps({"z": 1, "a": 2, "m": 3}) == '{"a":2,"m":3,"z":1}'


def test_dumps_compact_no_whitespace() -> None:
    """``stable_dumps`` uses no whitespace (compact JSON)."""
    result = stable_dumps({"a": 1, "b": [1, 2, 3]})
    assert " " not in result
    assert "\n" not in result


def test_dumps_nested_dicts() -> None:
    """Nested dicts are also sorted at every level."""
    result = stable_dumps({"outer": {"z": 1, "a": 2}, "list": [{"y": 1, "x": 2}]})
    # Both outer and inner keys are sorted.
    assert result == '{"list":[{"x":2,"y":1}],"outer":{"a":2,"z":1}}'


# --- Roundtrip --------------------------------------------------------------


def test_roundtrip_preserves_dict() -> None:
    """``stable_loads(stable_dumps(x)) == x`` for dicts."""
    data = {"b": 1, "a": 2, "nested": {"y": 1, "x": 2}}
    assert stable_loads(stable_dumps(data)) == data


def test_roundtrip_preserves_list() -> None:
    data = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5]
    assert stable_loads(stable_dumps(data)) == data


def test_roundtrip_preserves_string() -> None:
    assert stable_loads(stable_dumps("hello")) == "hello"


def test_roundtrip_preserves_int() -> None:
    assert stable_loads(stable_dumps(42)) == 42


def test_roundtrip_preserves_float() -> None:
    assert stable_loads(stable_dumps(3.14)) == 3.14


def test_roundtrip_preserves_bool() -> None:
    assert stable_loads(stable_dumps(True)) is True
    assert stable_loads(stable_dumps(False)) is False


def test_roundtrip_preserves_none() -> None:
    result = stable_loads(stable_dumps(None))
    assert result is None


# --- Decimal ----------------------------------------------------------------


def test_dumps_decimal_as_string() -> None:
    """Decimal is serialized as its string repr (no float precision loss)."""
    assert stable_dumps(decimal.Decimal("1.5")) == '"1.5"'
    assert stable_dumps(decimal.Decimal("0.1")) == '"0.1"'


def test_dumps_decimal_preserves_precision() -> None:
    """Decimal precision is preserved exactly (the core reason for using Decimal)."""
    result = stable_dumps(decimal.Decimal("1.12345678901234567890"))
    assert "1.12345678901234567890" in result


# --- datetime / date ---------------------------------------------------------


def test_dumps_datetime_to_iso() -> None:
    """datetime is serialized as ISO-8601 string."""
    dt = datetime.datetime(2026, 6, 22, 12, 30, 45, tzinfo=datetime.UTC)
    assert stable_dumps(dt) == '"2026-06-22T12:30:45+00:00"'


def test_dumps_naive_datetime_to_iso() -> None:
    """Naive datetime (no tzinfo) is serialized without timezone suffix."""
    dt = datetime.datetime(2026, 6, 22, 12, 30, 45)
    assert stable_dumps(dt) == '"2026-06-22T12:30:45"'


def test_dumps_date_to_iso() -> None:
    """date is serialized as ISO-8601 date string."""
    assert stable_dumps(datetime.date(2026, 6, 22)) == '"2026-06-22"'


# --- UUID -------------------------------------------------------------------


def test_dumps_uuid_to_hex() -> None:
    """UUID is serialized as its hex form (32 chars, no dashes)."""
    u = uuid.UUID("12345678123456781234567812345678")
    assert stable_dumps(u) == '"12345678123456781234567812345678"'


# --- bytes ------------------------------------------------------------------


def test_dumps_bytes_as_hex_with_0x_prefix() -> None:
    """bytes are serialized as ``"0x" + bytes.hex()`` to distinguish from strings."""
    assert stable_dumps(b"hi") == '"0x6869"'  # 'h' = 0x68, 'i' = 0x69


def test_dumps_bytearray_as_hex_with_0x_prefix() -> None:
    """bytearray follows the same convention as bytes."""
    assert stable_dumps(bytearray(b"abc")) == '"0x616263"'


# --- Enum -------------------------------------------------------------------


def test_dumps_enum_uses_value() -> None:
    """Enum is serialized using ``.value``."""

    class Color(enum.Enum):
        RED = "red"
        BLUE = "blue"

    assert stable_dumps(Color.RED) == '"red"'


# --- attrs ------------------------------------------------------------------


def test_dumps_attrs_instance_to_dict() -> None:
    """attrs instances are serialized via ``attrs.asdict``."""

    @attrs.frozen
    class Point:
        x: int
        y: int

    p = Point(x=1, y=2)
    # Sorted keys + compact.
    assert stable_dumps(p) == '{"x":1,"y":2}'


def test_dumps_nested_attrs() -> None:
    """Nested attrs instances are recursively serialized."""

    @attrs.frozen
    class Inner:
        value: int

    @attrs.frozen
    class Outer:
        name: str
        inner: Inner

    o = Outer(name="x", inner=Inner(value=42))
    result = stable_dumps(o)
    # Both inner and outer keys are sorted.
    assert result == '{"inner":{"value":42},"name":"x"}'


# --- sets -------------------------------------------------------------------


def test_dumps_set_as_sorted_list() -> None:
    """sets are serialized as a sorted list (deterministic)."""
    assert stable_dumps({3, 1, 2}) == "[1,2,3]"


def test_dumps_frozenset_as_sorted_list() -> None:
    """frozensets are serialized as a sorted list."""
    assert stable_dumps(frozenset({3, 1, 2})) == "[1,2,3]"


# --- TypeError on unsupported types -----------------------------------------


def test_dumps_unsupported_type_raises() -> None:
    """Unsupported types raise TypeError (instead of silently corrupting)."""

    class NotSerializable:
        pass

    with pytest.raises(TypeError, match="not JSON serializable"):
        stable_dumps(NotSerializable())


def test_dumps_object_raises() -> None:
    """Bare ``object()`` is not serializable."""
    with pytest.raises(TypeError):
        stable_dumps(object())


# --- Determinism ------------------------------------------------------------


def test_dumps_is_deterministic() -> None:
    """The same input produces the same output across many calls."""
    data = {"b": [3, 1, 2], "a": {"y": 1, "x": 2}}
    first = stable_dumps(data)
    for _ in range(50):
        assert stable_dumps(data) == first


# --- File I/O convenience --------------------------------------------------


def test_dump_to_file_and_load(tmp_path) -> None:
    """``stable_dump`` and ``stable_load`` work with file-like objects."""
    path = tmp_path / "test.json"
    data = {"b": 1, "a": 2}
    with path.open("w") as f:
        stable_dump(data, f)
    with path.open() as f:
        assert stable_load(f) == data


def test_dumps_supports_mappingproxy() -> None:
    """``types.MappingProxyType`` is serializable (used by frozen configs)."""
    import types

    mp = types.MappingProxyType({"a": 1, "b": 2})
    out = stable_dumps(mp)
    assert out == '{"a":1,"b":2}'
