"""End-to-end test for the CountryCapability public API."""

from __future__ import annotations

import pytest

from paxman import Country, canonicalize, parse_contract, replay
from paxman._core.status import Status


def test_end_to_end_name() -> None:
    result = canonicalize("United States", Country())
    assert result.status == Status.CANONICALIZED
    assert result.value == "US"
    rehydrated = replay(result, Country())
    assert rehydrated == result


def test_end_to_end_alpha3() -> None:
    result = canonicalize("USA", Country())
    assert result.status == Status.CANONICALIZED
    assert result.value == "US"


def test_end_to_end_uk_to_gb() -> None:
    result = canonicalize("uk", Country())
    assert result.status == Status.CANONICALIZED
    assert result.value == "GB"


def test_end_to_end_idempotent() -> None:
    result = canonicalize("US", Country())
    again = canonicalize(result.value, Country())
    assert again.value == "US"


def test_missing() -> None:
    result = canonicalize("", Country())
    assert result.status == Status.MISSING


def test_invalid() -> None:
    result = canonicalize("Atlantis", Country())
    assert result.status == Status.INVALID


def test_policy_disabled_alpha3() -> None:
    result = canonicalize("USA", Country(allow_alpha3=False))
    assert result.status == Status.INVALID


def test_dict_dsl_dispatch() -> None:
    result = canonicalize("US", parse_contract({"kind": "canonical_country"}))
    assert result.status == Status.CANONICALIZED
    assert result.value == "US"


def test_unknown_kind_unsupported() -> None:
    # Pass the dict to canonicalize so the engine's parse step maps the
    # unknown-kind ContractError to Status.UNSUPPORTED.
    result = canonicalize("US", {"kind": "unknown_kind"})
    assert result.status == Status.UNSUPPORTED


def test_evidence_records_rejection_rule() -> None:
    result = canonicalize("Atlantis", Country())
    assert any(ev.rule == "unrecognized_format" for ev in result.evidence)
