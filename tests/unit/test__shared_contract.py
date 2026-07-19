from __future__ import annotations

import attrs

from paxman._capabilities._shared.contract import (
    _AUTHORITY_OVERRIDE_KEY,
    _authority_override_from_spec,
    authority_override_field,
)


def test_authority_override_field_is_neq_and_repr_false():
    @attrs.frozen
    class _C:
        authority_override = authority_override_field()

    a = _C(authority_override={"ISO 3166-1": "2024"})
    b = _C(authority_override=None)
    # eq=False → two instances with different overrides are still equal
    assert a == b
    assert repr(a).count("authority_override") == 0


def test_authority_override_field_default_none():
    @attrs.frozen
    class _C:
        authority_override = authority_override_field()

    assert _C().authority_override is None


def test_authority_override_from_spec_reads_key():
    spec = {"version": "any", _AUTHORITY_OVERRIDE_KEY: {"ISO 3166-1": "2024"}}
    assert _authority_override_from_spec(spec) == {"ISO 3166-1": "2024"}


def test_authority_override_from_spec_missing_returns_none():
    assert _authority_override_from_spec({"version": "any"}) is None


def test_authority_override_key_constant():
    assert _AUTHORITY_OVERRIDE_KEY == "authority_override"
