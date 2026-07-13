"""Shared pytest fixtures for the Paxman v2 test suite."""
from __future__ import annotations

import pytest


@pytest.fixture
def fresh_registry() -> object:
    """A new, unfrozen CapabilityRegistry for tests that do not want the default.

    The `CapabilityRegistry` import is lazy so conftest does not pull
    in the paxman package at collection time (per-task fixture
    isolation, not a load-ordering requirement).
    """
    from paxman._capabilities.registry import CapabilityRegistry

    return CapabilityRegistry()
