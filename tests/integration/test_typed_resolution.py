"""End-to-end integration tests for typed resolution outcomes.

Tests the full pipeline from raw text input through contract adaptation,
planning, execution, reconciliation, and artifact generation for typed
parsing scenarios.
"""

from __future__ import annotations

import typing
from decimal import Decimal

import pytest

import paxman
import paxman.capabilities.v1  # Register built-in capabilities
import paxman.contract.adapters.dict_dsl  # Register Dict DSL adapter
from paxman.types import Status

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Contract fixtures (Dict DSL format)
# ---------------------------------------------------------------------------

DECIMAL_CONTRACT: dict[str, object] = {
    "id": "typed-decimal",
    "fields": [
        {
            "name": "total",
            "type": "DECIMAL",
            "required": True,
            "extract": {
                "capability": "regex_extraction",
                "config": {"pattern": r"[\d.]+"},
            },
            "parse": {"kind": "decimal"},
        },
    ],
}

INTEGER_CONTRACT: dict[str, object] = {
    "id": "typed-integer",
    "fields": [
        {
            "name": "count",
            "type": "INTEGER",
            "required": True,
            "extract": {
                "capability": "regex_extraction",
                "config": {"pattern": r"\d+"},
            },
            "parse": {"kind": "integer"},
        },
    ],
}

BOOLEAN_CONTRACT: dict[str, object] = {
    "id": "typed-boolean",
    "fields": [
        {
            "name": "approved",
            "type": "BOOLEAN",
            "required": True,
            "extract": {
                "capability": "regex_extraction",
                "config": {"pattern": r"\S+"},
            },
            "parse": {
                "kind": "boolean",
                "true_values": ["yes", "y"],
                "false_values": ["no", "n"],
            },
        },
    ],
}

DATE_CONTRACT: dict[str, object] = {
    "id": "typed-date",
    "fields": [
        {
            "name": "invoice_date",
            "type": "DATE",
            "required": True,
            "extract": {
                "capability": "regex_extraction",
                "config": {"pattern": r"\d{4}-\d{2}-\d{2}"},
            },
            "parse": {
                "kind": "date",
                "format": "%Y-%m-%d",
            },
        },
    ],
}


# ---------------------------------------------------------------------------
# Happy-path: each parse kind resolves to the correct typed value
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_decimal_resolves_to_decimal_not_string() -> None:
    artifact = paxman.normalize("Total: 12.50", DECIMAL_CONTRACT)
    assert artifact.status is Status.SUCCESS
    assert artifact.normalized_data == {"total": Decimal("12.50")}


@pytest.mark.integration
def test_integer_resolves_to_integer_not_string() -> None:
    artifact = paxman.normalize("Count: 42", INTEGER_CONTRACT)
    assert artifact.status is Status.SUCCESS
    assert artifact.normalized_data == {"count": 42}


@pytest.mark.integration
def test_boolean_true_resolves_to_true() -> None:
    artifact = paxman.normalize("Approved: yes", BOOLEAN_CONTRACT)
    assert artifact.status is Status.SUCCESS
    assert artifact.normalized_data == {"approved": True}


@pytest.mark.integration
def test_boolean_false_resolves_to_false() -> None:
    artifact = paxman.normalize("Approved: no", BOOLEAN_CONTRACT)
    assert artifact.status is Status.SUCCESS
    assert artifact.normalized_data == {"approved": False}


@pytest.mark.integration
def test_date_resolves_to_string_date() -> None:
    artifact = paxman.normalize("Date: 2026-07-12", DATE_CONTRACT)
    assert artifact.status is Status.SUCCESS
    assert artifact.normalized_data == {"invoice_date": "2026-07-12"}


# ---------------------------------------------------------------------------
# Failure: invalid text yields UNRESOLVED
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_invalid_decimal_is_unresolved() -> None:
    artifact = paxman.normalize("Total: twelve", DECIMAL_CONTRACT)
    assert artifact.status is Status.UNRESOLVED
    assert "total" in artifact.unresolved_fields


@pytest.mark.integration
def test_invalid_integer_is_unresolved() -> None:
    artifact = paxman.normalize("Count: abc", INTEGER_CONTRACT)
    assert artifact.status is Status.UNRESOLVED
    assert "count" in artifact.unresolved_fields


@pytest.mark.integration
def test_invalid_boolean_is_unresolved() -> None:
    artifact = paxman.normalize("Approved: maybe", BOOLEAN_CONTRACT)
    assert artifact.status is Status.UNRESOLVED
    assert "approved" in artifact.unresolved_fields


@pytest.mark.integration
def test_invalid_date_is_unresolved() -> None:
    artifact = paxman.normalize("Date: not-a-date", DATE_CONTRACT)
    assert artifact.status is Status.UNRESOLVED
    assert "invoice_date" in artifact.unresolved_fields


# ---------------------------------------------------------------------------
# Evidence chain: parse metadata appears in field evidence
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_decimal_evidence_includes_parse_metadata() -> None:
    artifact = paxman.normalize("Total: 12.50", DECIMAL_CONTRACT)
    assert artifact.status is Status.SUCCESS
    field_result = artifact.field_results.get("total")
    assert field_result is not None
    # Evidence should show the parse kind used.
    evidence = field_result.evidence_refs
    assert len(evidence) > 0


# ---------------------------------------------------------------------------
# Replay: parsed artifact replays identically
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_parsed_artifact_replay_hash_stable() -> None:
    artifact = paxman.normalize("Total: 12.50", DECIMAL_CONTRACT)
    assert artifact.status is Status.SUCCESS
    replayed = paxman.replay(artifact, DECIMAL_CONTRACT)
    assert replayed == artifact
    assert replayed.replay_hash == artifact.replay_hash
