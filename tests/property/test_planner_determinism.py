"""Property tests for the planner — same inputs produce the same plan.

Per Sprint 3 D3.18 (Hypothesis property test, derandomize=True,
max_examples=100) and V1 acceptance §1.2 (planner determinism).

The planner is a **pure function** (per ADR-0002): for the same
(canonical, profile, budget, policy, registry) tuple, it produces
the same :class:`ExecutionPlan` byte-for-byte.

We use :func:`paxman.serialization.stable_dumps` to compare plans
deterministically (sorted keys, no whitespace, RFC 8785-style).
"""

from __future__ import annotations

import string

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from paxman.budget import Policy
from paxman.capabilities.registry import register, reset
from paxman.capabilities.v1.inference import InferenceCapability
from paxman.capabilities.v1.regex_extraction import RegexExtractionCapability
from paxman.capabilities.v1.text_extraction import TextExtractionCapability
from paxman.capabilities.v1.validation import ValidationCapability
from paxman.contract._types import ContractPolicy
from paxman.contract.canonical import CanonicalContract, CanonicalField
from paxman.planner.input_profile import make_profile
from paxman.planner.planner import plan
from paxman.serialization import stable_dumps
from paxman.types import FieldType

# --- Hypothesis strategies ------------------------------------------------


_FIELD_NAMES = st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=10).filter(
    lambda s: s.isidentifier() and s not in {"id", "fields", "version", "policies"}
)


_FIELD_TYPES = st.sampled_from(
    [
        FieldType.STRING,
        FieldType.INTEGER,
        FieldType.DECIMAL,
        FieldType.BOOLEAN,
        FieldType.DATE,
    ]
)


_INPUTS = st.binary(min_size=0, max_size=512).filter(
    # Skip inputs that are likely undecodable as UTF-8; this avoids
    # Hypothesis raising during profile construction. The filter is
    # a safety belt; the planner itself never reads the raw input.
    lambda b: True  # Accept all bytes; make_profile handles them.
)


@st.composite
def _field_strategy(draw: st.DrawFn) -> CanonicalField:
    name = draw(_FIELD_NAMES)
    type_ = draw(_FIELD_TYPES)
    required = draw(st.booleans())
    threshold = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    return CanonicalField(
        id=f"field_{name}",
        path=name,
        name=name,
        type=type_,
        required=required,
        confidence_threshold=threshold,
    )


@st.composite
def _contract_strategy(draw: st.DrawFn) -> CanonicalContract:
    fields = draw(
        st.lists(
            _field_strategy(),
            min_size=1,
            max_size=4,
            unique_by=lambda f: f.name,
        )
    )
    return CanonicalContract(
        id="prop-test",
        fields=tuple(fields),
    )


@st.composite
def _policy_strategy(draw: st.DrawFn) -> Policy:
    return Policy(
        allow_remote_inference=draw(st.booleans()),
        allow_local_inference=draw(st.booleans()),
        confidence_floor=draw(
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
        ),
        unresolved_acceptable=draw(st.booleans()),
    )


# --- Fixtures -------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    """Register the 4 V1 capabilities, then reset between tests."""
    reset()
    register(RegexExtractionCapability())
    register(ValidationCapability())
    register(TextExtractionCapability())
    register(InferenceCapability())
    yield
    reset()


# --- Property tests -------------------------------------------------------


@pytest.mark.property
@given(contract=_contract_strategy(), raw=_INPUTS)
@settings(
    derandomize=True,
    deadline=None,
    max_examples=100,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_planner_is_byte_deterministic(contract: CanonicalContract, raw: bytes) -> None:
    """Same (contract, input, budget, policy, registry) → same plan JSON."""
    profile = make_profile(raw)
    p1 = plan(contract, profile)
    p2 = plan(contract, profile)
    assert stable_dumps(p1) == stable_dumps(p2)


@pytest.mark.property
@given(contract=_contract_strategy(), raw=_INPUTS, policy=_policy_strategy())
@settings(
    derandomize=True,
    deadline=None,
    max_examples=100,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_planner_is_byte_deterministic_with_policy(
    contract: CanonicalContract, raw: bytes, policy: Policy
) -> None:
    """Same (contract, input, policy) → same plan JSON."""
    profile = make_profile(raw)
    p1 = plan(contract, profile, policy=policy)
    p2 = plan(contract, profile, policy=policy)
    assert stable_dumps(p1) == stable_dumps(p2)


@pytest.mark.property
@given(contract=_contract_strategy(), raw=_INPUTS)
@settings(
    derandomize=True,
    deadline=None,
    max_examples=100,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_planner_plan_count_matches_required_fields(
    contract: CanonicalContract, raw: bytes
) -> None:
    """The plan has one FieldPlan per required field (per ADR-0001)."""
    profile = make_profile(raw)
    p = plan(contract, profile)
    required_count = sum(1 for f in contract.fields if f.required)
    assert len(p.field_plans) == required_count


@pytest.mark.property
@given(raw=_INPUTS)
@settings(
    derandomize=True,
    deadline=None,
    max_examples=100,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_planner_input_content_hash_matches_profile(raw: bytes) -> None:
    """The plan's input_content_hash equals the profile's content_hash."""
    contract = CanonicalContract(
        id="h",
        fields=(
            CanonicalField(
                id="f1",
                path="f1",
                name="f1",
                type=FieldType.STRING,
                required=True,
            ),
        ),
    )
    profile = make_profile(raw)
    p = plan(contract, profile)
    assert p.input_content_hash == profile.content_hash


@pytest.mark.property
def test_planner_with_contract_policy_is_deterministic() -> None:
    """A contract-level ContractPolicy is honored and is deterministic."""
    contract = CanonicalContract(
        id="c",
        fields=(
            CanonicalField(
                id="f1",
                path="f1",
                name="f1",
                type=FieldType.STRING,
                required=True,
                confidence_threshold=0.95,
            ),
        ),
        policies=ContractPolicy(confidence_floor=0.95),
    )
    profile = make_profile(b"hello world")
    p1 = plan(contract, profile)
    p2 = plan(contract, profile)
    assert stable_dumps(p1) == stable_dumps(p2)
    # The field's target_confidence reflects the field's threshold,
    # NOT the contract's confidence_floor (the latter is a Reconciler
    # decision, not a planner one).
    assert p1.field_plans[0].target_confidence == 0.95
