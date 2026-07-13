"""Shared pytest fixtures for the Paxman v2 test suite."""
from __future__ import annotations

import pytest


@pytest.fixture
def fresh_registry() -> object:  # returns CapabilityRegistry once Task 8 lands
    """A new, unfrozen CapabilityRegistry for tests that do not want the default."""
    from paxman._capabilities.registry import CapabilityRegistry

    return CapabilityRegistry()
