"""Tests for ModelRef (V1.2.0 design spec #50 §4).

Per design spec #50 §4 (D11): provider identity is separate from
endpoint configuration. The ``provider`` field is a short identifier
(e.g. ``"openai"``, ``"anthropic"``); the endpoint URL lives on the
provider instance, not in the name. The dataclass does not validate
the string shape beyond "non-empty str" — the openai-compatible:
URL form documented in the spec is permitted but not enforced.
"""
from __future__ import annotations

import attrs
import pytest

from paxman.providers._model import ModelRef


class TestModelRefBasics:
    """``ModelRef`` is a frozen attrs dataclass carrying (provider, model)."""

    def test_frozen(self) -> None:
        """Mutating a ModelRef raises FrozenInstanceError."""
        ref = ModelRef(provider="openai", model="gpt-4o-2024-08-06")
        with pytest.raises(attrs.exceptions.FrozenInstanceError):
            ref.provider = "anthropic"  # type: ignore[misc]

    def test_str_round_trip(self) -> None:
        """``str(ref)`` returns the ``"provider:model"`` form."""
        ref = ModelRef(provider="openai", model="gpt-4o-2024-08-06")
        assert str(ref) == "openai:gpt-4o-2024-08-06"

    def test_equality(self) -> None:
        """Two ModelRefs with the same (provider, model) are equal and hashable."""
        a = ModelRef(provider="openai", model="gpt-4o-2024-08-06")
        b = ModelRef(provider="openai", model="gpt-4o-2024-08-06")
        assert a == b
        assert hash(a) == hash(b)

    def test_inequality_different_model(self) -> None:
        """Different model identifiers produce unequal refs."""
        a = ModelRef(provider="openai", model="gpt-4o-2024-08-06")
        b = ModelRef(provider="openai", model="gpt-4o-mini-2024-07-18")
        assert a != b

    def test_inequality_different_provider(self) -> None:
        """Different provider identifiers produce unequal refs."""
        a = ModelRef(provider="openai", model="gpt-4o-2024-08-06")
        b = ModelRef(provider="anthropic", model="gpt-4o-2024-08-06")
        assert a != b

    def test_url_safe_provider_field(self) -> None:
        """Spec §4 (D11): the provider field may carry URL-bearing
        names like ``"openai-compatible:https://api.openrouter.ai/v1"``
        (the recommended pattern is a short identifier plus endpoint
        config on the instance, but the dataclass does not enforce
        this — the example from the design spec must be accepted
        verbatim)."""
        ref = ModelRef(
            provider="openai-compatible:https://api.openrouter.ai/v1",
            model="meta-llama/llama-3.1-70b-instruct",
        )
        assert ref.provider == "openai-compatible:https://api.openrouter.ai/v1"
        assert str(ref) == "openai-compatible:https://api.openrouter.ai/v1:meta-llama/llama-3.1-70b-instruct"

    def test_rejects_empty_provider(self) -> None:
        with pytest.raises(ValueError, match="provider"):
            ModelRef(provider="", model="x")

    def test_rejects_empty_model(self) -> None:
        with pytest.raises(ValueError, match="model"):
            ModelRef(provider="openai", model="")

    def test_rejects_non_string_provider(self) -> None:
        with pytest.raises(ValueError):
            ModelRef(provider=123, model="x")  # type: ignore[arg-type]

    def test_rejects_non_string_model(self) -> None:
        with pytest.raises(ValueError):
            ModelRef(provider="openai", model=42)  # type: ignore[arg-type]
