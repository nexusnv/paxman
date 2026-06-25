"""Unit tests for ``paxman.artifact.evidence`` — EvidenceStore."""

from __future__ import annotations

import pytest

from paxman.artifact.evidence import EvidenceStore
from paxman.capabilities.result import EvidenceRef

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

_EV1 = EvidenceRef(
    capability_id="regex_extraction",
    capability_version="1.0",
    field_path="supplier_name",
)
_EV2 = EvidenceRef(
    capability_id="regex_extraction",
    capability_version="1.0",
    field_path="total_amount",
)
_EV3 = EvidenceRef(
    capability_id="text_extraction",
    capability_version="2.0",
    field_path="supplier_name",
)


# ============================================================================
# Construction
# ============================================================================


@pytest.mark.deterministic
def test_evidence_store_empty() -> None:
    """EvidenceStore defaults to empty records."""
    store = EvidenceStore()
    assert store.records == ()


@pytest.mark.deterministic
def test_evidence_store_with_records() -> None:
    """EvidenceStore accepts a tuple of EvidenceRef."""
    store = EvidenceStore(records=(_EV1, _EV2))
    assert store.records == (_EV1, _EV2)


@pytest.mark.deterministic
def test_evidence_store_frozen() -> None:
    """EvidenceStore is frozen."""
    store = EvidenceStore()
    with pytest.raises(AttributeError):
        store.records = (_EV1,)  # type: ignore[misc]


# ============================================================================
# by_field
# ============================================================================


@pytest.mark.deterministic
def test_by_field_filters_correctly() -> None:
    """by_field returns only evidence for the given field_path."""
    store = EvidenceStore(records=(_EV1, _EV2, _EV3))
    result = store.by_field("supplier_name")
    assert result == (_EV1, _EV3)

    result2 = store.by_field("total_amount")
    assert result2 == (_EV2,)


@pytest.mark.deterministic
def test_by_field_empty_result() -> None:
    """by_field returns empty tuple for non-existent field."""
    store = EvidenceStore(records=(_EV1, _EV2))
    assert store.by_field("nonexistent") == ()


@pytest.mark.deterministic
def test_by_field_empty_store() -> None:
    """by_field on empty store returns empty tuple."""
    store = EvidenceStore()
    assert store.by_field("anything") == ()


# ============================================================================
# by_capability
# ============================================================================


@pytest.mark.deterministic
def test_by_capability_filters_correctly() -> None:
    """by_capability returns only evidence from the given capability."""
    store = EvidenceStore(records=(_EV1, _EV2, _EV3))
    result = store.by_capability("regex_extraction")
    assert result == (_EV1, _EV2)

    result2 = store.by_capability("text_extraction")
    assert result2 == (_EV3,)


@pytest.mark.deterministic
def test_by_capability_empty_result() -> None:
    """by_capability returns empty tuple for non-existent capability."""
    store = EvidenceStore(records=(_EV1,))
    assert store.by_capability("nonexistent") == ()


@pytest.mark.deterministic
def test_by_capability_empty_store() -> None:
    """by_capability on empty store returns empty tuple."""
    store = EvidenceStore()
    assert store.by_capability("anything") == ()


# ============================================================================
# field_paths property
# ============================================================================


@pytest.mark.deterministic
def test_field_paths_empty_store() -> None:
    """field_paths returns empty tuple on empty store."""
    assert EvidenceStore().field_paths == ()


@pytest.mark.deterministic
def test_field_paths_unique_sorted() -> None:
    """field_paths returns sorted unique field paths."""
    store = EvidenceStore(records=(_EV3, _EV1, _EV2))
    assert store.field_paths == ("supplier_name", "total_amount")


@pytest.mark.deterministic
def test_field_paths_single() -> None:
    """field_paths returns single path when only one field is referenced."""
    store = EvidenceStore(records=(_EV1,))
    assert store.field_paths == ("supplier_name",)


# ============================================================================
# capability_ids property
# ============================================================================


@pytest.mark.deterministic
def test_capability_ids_empty_store() -> None:
    """capability_ids returns empty tuple on empty store."""
    assert EvidenceStore().capability_ids == ()


@pytest.mark.deterministic
def test_capability_ids_unique_sorted() -> None:
    """capability_ids returns sorted unique capability IDs."""
    store = EvidenceStore(records=(_EV1, _EV2, _EV3))
    assert store.capability_ids == ("regex_extraction", "text_extraction")


@pytest.mark.deterministic
def test_capability_ids_single() -> None:
    """capability_ids returns single id when only one capability is referenced."""
    store = EvidenceStore(records=(_EV1, _EV2))
    assert store.capability_ids == ("regex_extraction",)
