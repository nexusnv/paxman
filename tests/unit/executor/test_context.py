"""Unit tests for :mod:`paxman.executor.context`.

Per Sprint 4 D4.2: ``ContextBuilder`` is a stateless builder
that produces :class:`CapabilityContext` records for capability
invocations. The tests pin the contract that:

- The builder copies the step's config (so the capability cannot
  affect the plan).
- The builder injects ``tier`` into the config.
- The builder rejects invalid inputs (non-bytes raw_input,
  empty field_path, etc.) before constructing a context.
"""

from __future__ import annotations

import pytest

from paxman.capabilities.base import CapabilityContext
from paxman.capabilities.spec import CapabilityTier
from paxman.executor.context import ContextBuilder
from paxman.planner.field_plan import FieldPlanStep

pytestmark = pytest.mark.unit


def _step(**config: object) -> FieldPlanStep:
    return FieldPlanStep(
        capability_id="regex_extraction",
        capability_version="1.0",
        config=config,
    )


def test_build_minimal() -> None:
    builder = ContextBuilder()
    ctx = builder.build(
        step=_step(pattern=r"^ACME"),
        raw_input=b"ACME Corp",
        field_path="supplier_name",
        field_type_name="STRING",
        input_profile_type="text",
        tier=CapabilityTier.LOCAL_DETERMINISTIC,
    )
    assert isinstance(ctx, CapabilityContext)
    assert ctx.field_path == "supplier_name"
    assert ctx.field_type_name == "STRING"
    assert ctx.input_profile_type == "text"
    assert ctx.raw_input == b"ACME Corp"
    assert ctx.span is None


def test_build_copies_config() -> None:
    """The capability's config is a copy, not a reference to the step's config."""
    builder = ContextBuilder()
    step = _step(pattern=r"^ACME", flags=("IGNORECASE",))
    ctx = builder.build(
        step=step,
        raw_input=b"acme",
        field_path="x",
        field_type_name="STRING",
        input_profile_type="text",
        tier=CapabilityTier.LOCAL_DETERMINISTIC,
    )
    assert ctx.config["pattern"] == r"^ACME"
    assert ctx.config["flags"] == ("IGNORECASE",)
    # Mutate the capability's config; the step's config is
    # unaffected (the step's config is also a MappingProxyType,
    # so direct mutation is impossible, but verify the
    # copy semantics by checking identity).
    ctx.config["extra"] = "value"
    assert "extra" not in step.config


def test_build_injects_tier_into_config() -> None:
    builder = ContextBuilder()
    ctx = builder.build(
        step=_step(),
        raw_input=b"",
        field_path="x",
        field_type_name="STRING",
        input_profile_type="text",
        tier=CapabilityTier.REMOTE_INFERENCE,
    )
    assert ctx.config["tier"] == "REMOTE_INFERENCE"


def test_build_preserves_existing_tier_in_config() -> None:
    """If the step already supplied a ``tier`` key, do not overwrite it."""
    builder = ContextBuilder()
    ctx = builder.build(
        step=_step(tier="LOCAL_DETERMINISTIC"),
        raw_input=b"",
        field_path="x",
        field_type_name="STRING",
        input_profile_type="text",
        tier=CapabilityTier.REMOTE_INFERENCE,
    )
    assert ctx.config["tier"] == "LOCAL_DETERMINISTIC"


def test_build_with_span() -> None:
    builder = ContextBuilder()
    ctx = builder.build(
        step=_step(),
        raw_input=b"abcdef",
        field_path="x",
        field_type_name="STRING",
        input_profile_type="text",
        tier=CapabilityTier.LOCAL_DETERMINISTIC,
        span=(0, 3),
    )
    assert ctx.span == (0, 3)


# --- input validation ------------------------------------------------


def test_build_rejects_non_bytes_raw_input() -> None:
    builder = ContextBuilder()
    with pytest.raises(TypeError, match="raw_input must be bytes"):
        builder.build(
            step=_step(),
            raw_input="not bytes",  # type: ignore[arg-type]
            field_path="x",
            field_type_name="STRING",
            input_profile_type="text",
            tier=CapabilityTier.LOCAL_DETERMINISTIC,
        )


def test_build_rejects_empty_field_path() -> None:
    builder = ContextBuilder()
    with pytest.raises(ValueError, match="field_path must be a non-empty string"):
        builder.build(
            step=_step(),
            raw_input=b"",
            field_path="",
            field_type_name="STRING",
            input_profile_type="text",
            tier=CapabilityTier.LOCAL_DETERMINISTIC,
        )


def test_build_rejects_empty_field_type_name() -> None:
    builder = ContextBuilder()
    with pytest.raises(ValueError, match="field_type_name must be a non-empty string"):
        builder.build(
            step=_step(),
            raw_input=b"",
            field_path="x",
            field_type_name="",
            input_profile_type="text",
            tier=CapabilityTier.LOCAL_DETERMINISTIC,
        )


def test_build_rejects_non_str_input_profile_type() -> None:
    builder = ContextBuilder()
    with pytest.raises(TypeError, match="input_profile_type must be a str"):
        builder.build(
            step=_step(),
            raw_input=b"",
            field_path="x",
            field_type_name="STRING",
            input_profile_type=123,  # type: ignore[arg-type]
            tier=CapabilityTier.LOCAL_DETERMINISTIC,
        )


def test_build_rejects_non_tier() -> None:
    builder = ContextBuilder()
    with pytest.raises(TypeError, match="tier must be a CapabilityTier"):
        builder.build(
            step=_step(),
            raw_input=b"",
            field_path="x",
            field_type_name="STRING",
            input_profile_type="text",
            tier="LOCAL_DETERMINISTIC",  # type: ignore[arg-type]
        )
