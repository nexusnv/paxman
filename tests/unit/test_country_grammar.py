"""Tests for the country recognition grammar (Layer 1)."""

from __future__ import annotations

import pytest

from paxman import Country
from paxman._capabilities.country.grammar import GRAMMARS, recognize


def test_recognize_alpha2() -> None:
    reps = recognize("US", Country())
    assert len(reps) == 1
    assert reps[0].shape == "alpha2"


def test_recognize_alpha3() -> None:
    reps = recognize("USA", Country())
    assert len(reps) == 1
    assert reps[0].shape == "alpha3"


def test_recognize_name() -> None:
    reps = recognize("United States", Country())
    assert len(reps) == 1
    assert reps[0].shape == "name"


def test_recognize_trims_whitespace() -> None:
    reps = recognize("  US  ", Country())
    assert len(reps) == 1
    assert reps[0].shape == "alpha2"


def test_recognize_none_returns_empty() -> None:
    assert recognize("", Country()) == []


def test_grammars_carry_source() -> None:
    for g in GRAMMARS:
        assert g.source
