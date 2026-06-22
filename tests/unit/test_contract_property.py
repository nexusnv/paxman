"""Property tests for the contract subsystem adapters (Hypothesis).

Per Sprint 2 D2.12 and V1 acceptance §1.5 / exit criterion #9, the
Pydantic and Dict DSL adapters must round-trip preserves structure
within the adapter's expressible subset:

    adapt(export(adapt(contract))) == adapt(contract)

for 100 random Pydantic / Dict DSL contracts. We use Hypothesis
with ``derandomize=True`` and ``deadline=None`` (per the Sprint 2
risk register) and ``max_examples=100``.

The Dict DSL strategy generates hand-rolled contract dicts. The
Pydantic strategy generates small ``BaseModel`` subclasses (built
dynamically via ``pydantic.create_model``) and round-trips them.

These tests are slow compared to unit tests, so they are marked
``@pytest.mark.property`` and excluded from the fast unit test run.
"""

from __future__ import annotations

import string

import pydantic
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

import paxman.contract.adapters.dict_dsl
import paxman.contract.adapters.pydantic  # noqa: F401
from paxman.contract.adapters.dict_dsl import DictDSLAdapter
from paxman.contract.adapters.pydantic import PydanticAdapter
from paxman.contract.canonical import CanonicalContract
from paxman.types import FieldType

# --- Hypothesis strategies ---------------------------------------------------

#: A short identifier (1-10 lowercase ASCII letters).
_id_strategy = st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=10).filter(
    lambda s: s.isidentifier()
)

#: A field name (1-10 lowercase ASCII letters).
_field_name_strategy = st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=10).filter(
    lambda s: s.isidentifier() and s not in {"id", "fields", "constraints", "policy"}
)

#: An integer default.
_int_default = st.integers(min_value=-(10**6), max_value=10**6)

#: A string default.
_str_default = st.text(alphabet=string.ascii_letters + string.digits, min_size=0, max_size=20)

#: A boolean default.
_bool_default = st.booleans()

#: A type literal.
_type_literal = st.sampled_from(
    ["STRING", "INTEGER", "BOOLEAN", "DATE", "DECIMAL", "OBJECT", "ARRAY"]
)

#: A single field spec (no MONEY or ENUM for simplicity; covered by unit tests).
_field_spec_strategy = st.one_of(
    st.fixed_dictionaries(
        {"name": _field_name_strategy, "type": st.just("STRING"), "required": st.booleans()}
    ),
    st.fixed_dictionaries(
        {"name": _field_name_strategy, "type": st.just("INTEGER"), "required": st.booleans()}
    ),
    st.fixed_dictionaries(
        {"name": _field_name_strategy, "type": st.just("BOOLEAN"), "required": st.booleans()}
    ),
    st.fixed_dictionaries(
        {"name": _field_name_strategy, "type": st.just("DECIMAL"), "required": st.booleans()}
    ),
    st.fixed_dictionaries(
        {"name": _field_name_strategy, "type": st.just("DATE"), "required": st.booleans()}
    ),
    st.fixed_dictionaries(
        {"name": _field_name_strategy, "type": st.just("OBJECT"), "required": st.booleans()}
    ),
    st.fixed_dictionaries(
        {"name": _field_name_strategy, "type": st.just("ARRAY"), "required": st.booleans()}
    ),
)


#: A complete contract spec (id + 1-3 fields, no duplicates).
@st.composite
def _contract_spec_strategy(draw: st.DrawFn) -> dict:
    """Build a complete Dict DSL contract spec (1-3 fields, no duplicates)."""
    return {
        "id": draw(_id_strategy),
        "version": "1",
        "fields": draw(
            st.lists(_field_spec_strategy, min_size=1, max_size=3, unique_by=lambda f: f["name"])
        ),
    }


# --- Pydantic strategy ------------------------------------------------------

#: A small Pydantic model generated dynamically. Pydantic v2's
#: ``create_model`` accepts a dict of ``name -> (annotation, default)``.
#: We restrict the annotation set to types the adapter can express so
#: the round-trip stays in the expressible subset.
_pydantic_field_strategy = st.sampled_from(
    [
        ("s", str, ...),
        ("i", int, ...),
        ("b", bool, ...),
        ("d", float, ...),
    ]
)


@st.composite
def _pydantic_model(draw: st.DrawFn) -> type:
    """Generate a Pydantic v2 model with 1-3 primitive fields."""
    selected = draw(
        st.lists(
            _pydantic_field_strategy,
            min_size=1,
            max_size=3,
            unique_by=lambda t: t[0],
        )
    )
    fields_dict: dict = {name: (annotation, default) for name, annotation, default in selected}
    return pydantic.create_model("Generated", **fields_dict)


# --- Property: Dict DSL round-trip ------------------------------------------


@pytest.mark.property
@given(spec=_contract_spec_strategy())
@settings(
    derandomize=True,
    deadline=None,
    max_examples=100,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_dict_dsl_round_trip(spec: dict) -> None:
    """``adapt(export(adapt(d))) == adapt(d)`` for Dict DSL contracts."""
    adapter = DictDSLAdapter()
    c1 = adapter.adapt(spec)
    out = adapter.export(c1)
    c2 = adapter.adapt(out)
    assert c1.id == c2.id
    assert [f.name for f in c1.fields] == [f.name for f in c2.fields]
    assert [f.type for f in c1.fields] == [f.type for f in c2.fields]
    assert [f.required for f in c1.fields] == [f.required for f in c2.fields]


# --- Property: Pydantic round-trip ------------------------------------------


@pytest.mark.property
@given(model=_pydantic_model())
@settings(
    derandomize=True,
    deadline=None,
    max_examples=100,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_pydantic_round_trip(model: type) -> None:
    """``adapt(export(adapt(M)))`` preserves field count, names, and types for Pydantic models."""
    adapter = PydanticAdapter()
    c1 = adapter.adapt(model)
    M2 = adapter.export(c1)
    c2 = adapter.adapt(M2)
    assert [f.name for f in c1.fields] == [f.name for f in c2.fields]
    assert [f.type for f in c1.fields] == [f.type for f in c2.fields]


# --- Property: Dict DSL all-v1-types fixture round-trips --------------------


@pytest.mark.property
def test_dict_dsl_all_v1_types_fixture_round_trips() -> None:
    """The all-V1-types fixture round-trips structurally."""
    from tests.fixtures.contracts.dict_dsl import all_v1_types as mod

    adapter = DictDSLAdapter()
    c1 = adapter.adapt(mod.DICT_DSL_ALL_V1_TYPES)
    out = adapter.export(c1)
    c2 = adapter.adapt(out)
    assert c1.id == c2.id
    assert {f.name for f in c1.fields} == {f.name for f in c2.fields}
    assert {f.type for f in c1.fields} == {f.type for f in c2.fields}
    assert len(c1.fields) == 9
    assert FieldType.MONEY in {f.type for f in c1.fields}
    assert FieldType.ENUM in {f.type for f in c1.fields}


# --- Property: CanonicalContract direct construction is hashable / frozen ---


@pytest.mark.deterministic
def test_canonical_contract_is_frozen() -> None:
    """A :class:`CanonicalContract` is frozen (immutable)."""
    f = pydantic.Field  # just to avoid unused-import noise
    from paxman.contract.canonical import CanonicalField

    f = CanonicalField(
        id="f1",
        path="x",
        name="x",
        type=FieldType.STRING,
        required=True,
    )
    c = CanonicalContract(id="c", fields=(f,))
    with pytest.raises(attrs_frozen_error()):  # type: ignore[arg-type]
        c.id = "new_id"  # type: ignore[misc]


def attrs_frozen_error() -> type[Exception]:
    """Return ``attrs.exceptions.FrozenInstanceError`` for the frozen test."""
    import attrs.exceptions as _ae

    return _ae.FrozenInstanceError
