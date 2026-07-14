"""100-email regression for the 5-Minute Promise (spec §4.8).

Runs the deterministic 100-email dataset through paxman.canonicalize
via the README path. Asserts exactly 95 Status.CANONICALIZED and 5
Status.INVALID. All canonicalized artifacts round-trip through replay
byte-equal. The novice-did-nothing fixture is reused.
"""

from __future__ import annotations

import sys
from collections import Counter
from typing import Any

import pytest

import paxman
from paxman import Email, _orchestrator_runtime
from paxman._capabilities.registry import CapabilityRegistry
from paxman._core.types import Status


# Make the underscore-prefixed data module importable. pytest refuses
# to collect modules named with leading underscores (e.g. _five_minute_data.py
# is not discovered), so we add its directory to sys.path for the
# duration of this test file. The data module is private to the test
# suite; nothing outside tests/ should import it.
_DATA_DIR = __file__.rsplit("/", 1)[0]  # tests/integration/
if _DATA_DIR not in sys.path:
    sys.path.insert(0, _DATA_DIR)
from _five_minute_data import (  # noqa: E402
    all_canonicalizable_emails,
    all_invalid_pairs,
)


@pytest.fixture(autouse=True)
def _fresh_empty_registry(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(_orchestrator_runtime, "default_registry", CapabilityRegistry())
    yield


class TestFiveMinute100Emails:
    def test_95_canonicalized(self) -> None:
        canonical_count = 0
        for email in all_canonicalizable_emails():
            result = paxman.canonicalize(email, Email(provider_aliases="gmail"))
            if result.status is Status.CANONICALIZED:
                canonical_count += 1
            else:
                # Diagnostic on failure: print the email + status + evidence
                pytest.fail(
                    f"expected CANONICALIZED for {email!r}; got "
                    f"{result.status.name} with evidence "
                    f"{[(e.rule, e.detail) for e in result.evidence]}"
                )
        assert canonical_count == 95, (
            f"expected 95 CANONICALIZED, got {canonical_count}"
        )

    def test_5_invalid(self) -> None:
        invalid_count = 0
        for email, contract_kwargs in all_invalid_pairs():
            _kwargs: dict[str, Any] = contract_kwargs
            contract = Email(**_kwargs) if _kwargs else Email()
            result = paxman.canonicalize(email, contract)
            if result.status is Status.INVALID:
                invalid_count += 1
            else:
                pytest.fail(
                    f"expected INVALID for {email!r} with contract "
                    f"{contract!r}; got {result.status.name} with value "
                    f"{result.value!r}"
                )
        assert invalid_count == 5, (
            f"expected 5 INVALID, got {invalid_count}"
        )

    def test_exactly_100_total(self) -> None:
        total = len(all_canonicalizable_emails()) + len(all_invalid_pairs())
        assert total == 100, f"expected 100 total, got {total}"

    def test_count_by_status_resilient_to_order(self) -> None:
        all_results: list[Status] = []
        for email in all_canonicalizable_emails():
            result = paxman.canonicalize(email, Email(provider_aliases="gmail"))
            all_results.append(result.status)
        for email, contract_kwargs in all_invalid_pairs():
            _kwargs: dict[str, Any] = contract_kwargs
            contract = Email(**_kwargs) if _kwargs else Email()
            result = paxman.canonicalize(email, contract)
            all_results.append(result.status)
        counts = Counter(all_results)
        assert counts[Status.CANONICALIZED] == 95
        assert counts[Status.INVALID] == 5
        assert sum(counts.values()) == 100

    def test_all_canonicalized_round_trip_replay(self) -> None:
        # Every canonicalized artifact must replay byte-equal (Law 12).
        for email in all_canonicalizable_emails():
            contract = Email(provider_aliases="gmail")
            result = paxman.canonicalize(email, contract)
            if result.status is Status.CANONICALIZED:
                rehydrated = paxman.replay(result, contract)
                assert rehydrated == result, (
                    f"replay drift for {email!r}: "
                    f"{rehydrated.canonical_bytes()!r} != "
                    f"{result.canonical_bytes()!r}"
                )
                assert rehydrated.canonical_bytes() == result.canonical_bytes()
