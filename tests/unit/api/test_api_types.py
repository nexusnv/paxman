"""Unit tests for ``paxman.api.types`` — public type re-exports.

All 10 public types should be importable from ``paxman.api.types`` and
be instances of the correct base types (enum.Enum for enum types,
proper classes for data types).
"""

from __future__ import annotations

import enum

import attrs
import pytest

from paxman.api.types import (
    Budget,
    CanonicalContract,
    CanonicalField,
    ConfidenceBand,
    CurrencyPolicy,
    ExecutionArtifact,
    FieldType,
    Policy,
    ResolutionPolicy,
    Status,
)

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# All 10 types are importable
# ---------------------------------------------------------------------------


class TestAllTypesImportable:
    """All 10 types are importable from ``paxman.api.types``."""

    def test_budget_importable(self) -> None:
        assert Budget is not None

    def test_canonical_contract_importable(self) -> None:
        assert CanonicalContract is not None

    def test_canonical_field_importable(self) -> None:
        assert CanonicalField is not None

    def test_confidence_band_importable(self) -> None:
        assert ConfidenceBand is not None

    def test_currency_policy_importable(self) -> None:
        assert CurrencyPolicy is not None

    def test_execution_artifact_importable(self) -> None:
        assert ExecutionArtifact is not None

    def test_field_type_importable(self) -> None:
        assert FieldType is not None

    def test_policy_importable(self) -> None:
        assert Policy is not None

    def test_resolution_policy_importable(self) -> None:
        assert ResolutionPolicy is not None

    def test_status_importable(self) -> None:
        assert Status is not None


# ---------------------------------------------------------------------------
# Enum type checks (isinstance)
# ---------------------------------------------------------------------------


class TestEnumTypes:
    """Enum types are proper ``enum.Enum`` subclasses."""

    def test_status_is_enum(self) -> None:
        assert issubclass(Status, enum.Enum)

    def test_status_member_is_enum_instance(self) -> None:
        assert isinstance(Status.SUCCESS, enum.Enum)

    def test_confidence_band_is_enum(self) -> None:
        assert issubclass(ConfidenceBand, enum.Enum)

    def test_confidence_band_member_is_enum_instance(self) -> None:
        assert isinstance(ConfidenceBand.CERTAIN, enum.Enum)

    def test_field_type_is_enum(self) -> None:
        assert issubclass(FieldType, enum.Enum)

    def test_field_type_member_is_enum_instance(self) -> None:
        assert isinstance(FieldType.STRING, enum.Enum)

    def test_currency_policy_is_enum(self) -> None:
        assert issubclass(CurrencyPolicy, enum.Enum)

    def test_currency_policy_member_is_enum_instance(self) -> None:
        assert isinstance(CurrencyPolicy.STRICT_MATCH, enum.Enum)

    def test_resolution_policy_is_attrs_frozen(self) -> None:
        assert attrs.has(ResolutionPolicy)

    def test_resolution_policy_default_strategy(self) -> None:
        rp = ResolutionPolicy()
        assert rp.strategy.value == "UNRESOLVED"


# ---------------------------------------------------------------------------
# Data-type checks (attrs frozen classes)
# ---------------------------------------------------------------------------


class TestDataTypeClasses:
    """Data-type classes are proper ``attrs`` frozen classes."""

    def test_budget_is_attrs_frozen(self) -> None:
        assert attrs.has(Budget)

    def test_policy_is_attrs_frozen(self) -> None:
        assert attrs.has(Policy)

    def test_canonical_field_is_attrs_frozen(self) -> None:
        assert attrs.has(CanonicalField)

    def test_canonical_contract_is_attrs_frozen(self) -> None:
        assert attrs.has(CanonicalContract)

    def test_execution_artifact_is_attrs_frozen(self) -> None:
        assert attrs.has(ExecutionArtifact)


# ---------------------------------------------------------------------------
# Construction smoke tests
# ---------------------------------------------------------------------------


class TestConstruction:
    """Smoke tests: each type can be constructed with minimal args."""

    def test_budget_default(self) -> None:
        b = Budget()
        assert b.max_total_cost_usd is None

    def test_policy_default(self) -> None:
        p = Policy()
        assert p.allow_remote_inference is True

    def test_canonical_field_minimal(self) -> None:
        cf = CanonicalField(
            id="f1",
            path="name",
            name="Name",
            type=FieldType.STRING,
            required=True,
        )
        assert cf.path == "name"
        assert cf.type is FieldType.STRING

    def test_canonical_contract_minimal(self) -> None:
        cf = CanonicalField(
            id="f1",
            path="name",
            name="Name",
            type=FieldType.STRING,
            required=True,
        )
        cc = CanonicalContract(id="test", fields=(cf,))
        assert cc.id == "test"
        assert len(cc.fields) == 1

    def test_execution_artifact_minimal(self) -> None:
        ea = ExecutionArtifact(
            status=Status.UNRESOLVED,
            normalized_data={},
            field_results={},
            unresolved_fields=[],
            evidence=(),
            diagnostics=(),
            execution_plan=None,
            statistics=None,
            contract_id="",
        )
        assert ea.status is Status.UNRESOLVED
        assert ea.normalized_data == {}

    def test_currency_policy_values(self) -> None:
        assert CurrencyPolicy.STRICT_MATCH.value == "STRICT_MATCH"
        assert CurrencyPolicy.ALLOW_FX.value == "ALLOW_FX"
        assert CurrencyPolicy.REJECT_WITHOUT_RATE.value == "REJECT_WITHOUT_RATE"

    def test_status_values(self) -> None:
        assert Status.SUCCESS.value == "SUCCESS"
        assert Status.UNRESOLVED.value == "UNRESOLVED"

    def test_confidence_band_values(self) -> None:
        assert ConfidenceBand.CERTAIN.value == "CERTAIN"
        assert ConfidenceBand.UNTRUSTED.value == "UNTRUSTED"

    def test_field_type_values(self) -> None:
        assert FieldType.STRING.value == "STRING"
        assert FieldType.MONEY.value == "MONEY"
