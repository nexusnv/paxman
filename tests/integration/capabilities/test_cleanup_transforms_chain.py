"""Integration test — post-extraction cleanup transforms invoked through the registry.

This test exercises the two V1.1.0 post-extraction cleanup
capabilities (``case_normalization`` and ``trim_extraction``)
through the same public surface that downstream code uses
(``paxman.capabilities.registry.get`` and
``paxman.capabilities.base.CapabilityContext``), and verifies a
``regex_extraction`` → ``case_normalization`` → ``trim_extraction``
chain resolves end-to-end against a real Dict DSL contract on a
real CSV input.

Scope note: the V1.1.0 slice adds the two cleanup capabilities
but does not change the executor's capability-selection logic
(the planner still iterates every registered tier-1 spec). A
follow-up (filed as a separate issue) is required to teach the
executor to dispatch ``config["value"]`` post-resolution
capabilities automatically. Until then, callers wire the chain
explicitly via :func:`paxman.capabilities.registry.register` and
direct ``invoke()`` calls. This integration test verifies the
slice's actual deliverable — the capabilities work correctly
through the public registry/contract surface in a realistic
three-step chain — and also verifies that ``paxman.normalize()``
on the same input produces a stable ``replay_hash`` even with
the chain step in place.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import paxman
import paxman.capabilities.registry as registry
import paxman.contract.adapters.dict_dsl  # self-registration of the Dict DSL adapter
from paxman.capabilities.base import CapabilityContext
from paxman.capabilities.registry import register, reset
from paxman.capabilities.result import DiagnosticCode
from paxman.capabilities.v1.case_normalization import CaseNormalizationCapability
from paxman.capabilities.v1.trim_extraction import TrimExtractionCapability
from tests.fixtures.contracts.dict_dsl.with_cleanup_chain import (
    DICT_DSL_WITH_CLEANUP_CHAIN,
)

pytestmark = pytest.mark.integration


_FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"


@pytest.fixture(autouse=True)
def _register_cleanup_transforms() -> None:
    """Register the two V1.1.0 cleanup transforms and reset on exit.

    Also registers ``regex_extraction`` and ``csv_extraction`` for
    the chain tests that exercise a
    ``regex_extraction → case_normalization → trim_extraction``
    chain. The two new capabilities follow the V1.1.0
    self-registration convention (ADR-0012), but we still call
    ``reset()`` at exit so this fixture does not leak state into
    other integration tests in the same run (golden-artifact
    tests in particular assume the registry is empty at start).
    """
    from paxman.capabilities.v1.csv_extraction import CsvExtractionCapability
    from paxman.capabilities.v1.regex_extraction import RegexExtractionCapability

    reset()
    register(RegexExtractionCapability(), replace=True)
    register(CsvExtractionCapability(), replace=True)
    register(CaseNormalizationCapability(), replace=True)
    register(TrimExtractionCapability(), replace=True)
    yield
    reset()


def _load_csv() -> bytes:
    return (_FIXTURES_DIR / "inputs" / "sample_invoices.csv").read_bytes()


# --- spec / registry -----------------------------------------------------


def test_case_normalization_is_in_registry() -> None:
    """The registered case_normalization spec is reachable via the registry."""
    spec = registry.get_latest("case_normalization").spec
    assert spec.id == "case_normalization"
    assert spec.version == "1.0"
    assert spec.tier.value == 1  # LOCAL_DETERMINISTIC
    assert spec.deterministic is True


def test_trim_extraction_is_in_registry() -> None:
    """The registered trim_extraction spec is reachable via the registry."""
    spec = registry.get_latest("trim_extraction").spec
    assert spec.id == "trim_extraction"
    assert spec.version == "1.0"
    assert spec.tier.value == 1  # LOCAL_DETERMINISTIC
    assert spec.deterministic is True


# --- direct chain (regex -> case -> trim) --------------------------------


def test_regex_to_case_to_trim_chain_produces_normalized_value() -> None:
    """The full three-step chain produces a normalized ``acme corp``.

    Step 1 — ``regex_extraction`` extracts ``ACME Corp`` from the
    second column of the first data row of the CSV (the pattern
    matches the supplier name between the ``INV-001,`` prefix and
    the ``,1234.56,USD`` suffix).

    Step 2 — ``case_normalization`` lower-cases it to ``acme corp``.

    Step 3 — ``trim_extraction`` strips a trailing ``:`` (added
    here to exercise the trim step) to ``acme corp``.

    The point of the test is to exercise the *config["value"]*
    post-resolution input pattern end-to-end: the chain hand-off
    uses ``ctx.config["value"]`` (not ``ctx.raw_input``), so this
    is the only test that proves the three capabilities compose.
    """
    csv_bytes = _load_csv()
    field_path = "supplier"
    field_type_name = "STRING"

    # Step 1: regex_extraction. The pattern matches the supplier
    # cell of the first non-empty row: ``INV-001,ACME Corp,...``.
    # We use a named group so ``regex_extraction`` extracts the
    # group value (per the V1 spec, a single named group is
    # extracted; without a named group, the whole match is used).
    regex_cap = registry.get_latest("regex_extraction")
    regex_ctx = CapabilityContext(
        raw_input=csv_bytes,
        field_path=field_path,
        field_type_name=field_type_name,
        config={"pattern": r"INV-\d+,(?P<supplier>[A-Z][A-Za-z ]+),"},
    )
    regex_result = regex_cap.invoke(regex_ctx)
    assert regex_result.candidates, "regex_extraction produced no candidates"
    extracted = regex_result.candidates[0].value
    assert extracted == "ACME Corp"

    # Step 2: case_normalization (lowercase).
    case_cap = registry.get_latest("case_normalization")
    case_ctx = CapabilityContext(
        raw_input=b"",
        field_path=field_path,
        field_type_name=field_type_name,
        config={"value": extracted, "mode": "lower"},
    )
    case_result = case_cap.invoke(case_ctx)
    assert case_result.candidates
    lower_cased = case_result.candidates[0].value
    assert lower_cased == "acme corp"

    # Step 3: trim_extraction (strip trailing colon).
    trim_cap = registry.get_latest("trim_extraction")
    trim_ctx = CapabilityContext(
        raw_input=b"",
        field_path=field_path,
        field_type_name=field_type_name,
        config={"value": lower_cased + ":", "chars": " :"},
    )
    trim_result = trim_cap.invoke(trim_ctx)
    assert trim_result.candidates
    final = trim_result.candidates[0].value
    assert final == "acme corp"

    # The chain produces byte-equal EvidenceRef.context shapes.
    ev = trim_result.candidates[0].evidence_refs[0]
    assert ev.capability_id == "trim_extraction"
    assert ev.context["original_value"] == "acme corp:"
    # 1 trailing colon was stripped (the space is not in the
    # explicit chars set " :", and str.strip only strips chars
    # in the set; the leading "acme corp" has no leading space,
    # so the strip removes only the trailing ":".)
    assert ev.context["stripped_count"] == 1


def test_chain_is_byte_equal_on_replay() -> None:
    """A second run of the chain produces a byte-equal final value.

    Determinism is a V1 hard invariant; the cleanup transforms are
    pure functions of their config, so re-running the chain must
    produce the same final candidate.
    """
    csv_bytes = _load_csv()
    extracted: str = (
        registry.get_latest("regex_extraction")
        .invoke(
            CapabilityContext(
                raw_input=csv_bytes,
                field_path="supplier",
                field_type_name="STRING",
                config={"pattern": r"INV-\d+,(?P<supplier>[A-Z][A-Za-z ]+),"},
            )
        )
        .candidates[0]
        .value
    )
    assert extracted == "ACME Corp"

    def _run_once() -> str:
        lower = (
            registry.get_latest("case_normalization")
            .invoke(
                CapabilityContext(
                    raw_input=b"",
                    field_path="supplier",
                    field_type_name="STRING",
                    config={"value": extracted, "mode": "lower"},
                )
            )
            .candidates[0]
            .value
        )
        return (
            registry.get_latest("trim_extraction")
            .invoke(
                CapabilityContext(
                    raw_input=b"",
                    field_path="supplier",
                    field_type_name="STRING",
                    config={"value": lower + ":", "chars": " :"},
                )
            )
            .candidates[0]
            .value
        )

    first = _run_once()
    second = _run_once()
    assert first == second == "acme corp"


# --- end-to-end paxman.normalize stability -------------------------------


def test_normalize_artifact_has_stable_replay_hash() -> None:
    """``normalize()`` on the CSV input produces a stable ``replay_hash``.

    The artifact's ``replay_hash`` is byte-equal across two runs of
    the same input, even though the slice does not yet wire the
    cleanup transforms into the executor (the fields stay
    unresolved, but the artifact is still deterministic).
    """
    csv_bytes = _load_csv()

    first = paxman.normalize(input_data=csv_bytes, contract=DICT_DSL_WITH_CLEANUP_CHAIN)
    second = paxman.normalize(input_data=csv_bytes, contract=DICT_DSL_WITH_CLEANUP_CHAIN)
    assert first.replay_hash == second.replay_hash
    assert len(first.replay_hash) == 64  # SHA-256 hex


def test_cleanup_chain_does_not_break_existing_csv_extractor() -> None:
    """The cleanup transforms live alongside the format extractors.

    The CSV extractor (``csv_extraction``, registered via the
    V1.1.0 format-extractors slice) must still be reachable; the
    cleanup transforms do not crowd it out.
    """
    csv_spec = registry.get_latest("csv_extraction").spec
    assert csv_spec.id == "csv_extraction"
    assert csv_spec.tier.value == 1


def test_chain_handles_chain_of_chains() -> None:
    """A chain can be invoked recursively through ``ctx.config["value"]``.

    This exercises the *config-driven-input* invariant: a
    cleanup-transform's output (``candidates[0].value``) is
    consumable as the next cleanup-transform's input
    (``ctx.config["value"]``), without going through the
    executor. This is the loop that an executor-side integration
    would build on top of these primitives.
    """
    # Stage 1: input is uppercase with a trailing colon.
    value = "  ACME Corp  :  "
    # Stage 2: trim first (preserves the rest of the content).
    trimmed = (
        registry.get_latest("trim_extraction")
        .invoke(
            CapabilityContext(
                raw_input=b"",
                field_path="supplier",
                field_type_name="STRING",
                config={"value": value, "chars": " :"},
            )
        )
        .candidates[0]
        .value
    )
    assert trimmed == "ACME Corp"
    # Stage 3: case_normalization then trim again.
    lower = (
        registry.get_latest("case_normalization")
        .invoke(
            CapabilityContext(
                raw_input=b"",
                field_path="supplier",
                field_type_name="STRING",
                config={"value": trimmed, "mode": "lower"},
            )
        )
        .candidates[0]
        .value
    )
    assert lower == "acme corp"
    final = (
        registry.get_latest("trim_extraction")
        .invoke(
            CapabilityContext(
                raw_input=b"",
                field_path="supplier",
                field_type_name="STRING",
                config={"value": lower, "chars": " :"},
            )
        )
        .candidates[0]
        .value
    )
    assert final == "acme corp"


def test_chain_with_unknown_mode_fails_loudly() -> None:
    """A bad mode in the middle of a chain aborts the chain with a diagnostic.

    The "validation rejects, doesn't guess" philosophy is honored
    by the case_normalization capability: a misspelled mode key
    in a contract fails loudly, not silently.
    """
    result = registry.get_latest("case_normalization").invoke(
        CapabilityContext(
            raw_input=b"",
            field_path="supplier",
            field_type_name="STRING",
            config={"value": "ACME Corp", "mode": "snake_case"},
        )
    )
    assert result.candidates == ()
    assert result.diagnostics[0].code.value == "CAPABILITY_INVOKE_FAILED"


def test_chain_with_missing_value_fails_loudly() -> None:
    """The cleanup transforms fail loudly when ``ctx.config["value"]`` is missing.

    The post-resolution input pattern is a hard contract:
    ``ctx.config["value"]`` is **required**. If the upstream step
    produced no candidate and the caller forwards a missing
    ``value`` to a cleanup transform, the capability does **not**
    silently no-op — it returns a ``CAPABILITY_INVOKE_FAILED``
    diagnostic. This test exercises that contract on both cleanup
    transforms directly, not on the regex step (a regex non-match
    is a separate concern owned by ``regex_extraction``).
    """
    # case_normalization: missing value is a hard failure.
    case_ctx = CapabilityContext(
        raw_input=b"",
        field_path="supplier",
        field_type_name="STRING",
        config={"mode": "lower"},
    )
    case_result = registry.get_latest("case_normalization").invoke(case_ctx)
    assert case_result.candidates == ()
    assert case_result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED

    # trim_extraction: missing value is a hard failure.
    trim_ctx = CapabilityContext(
        raw_input=b"",
        field_path="supplier",
        field_type_name="STRING",
        config={},
    )
    trim_result = registry.get_latest("trim_extraction").invoke(trim_ctx)
    assert trim_result.candidates == ()
    assert trim_result.diagnostics[0].code is DiagnosticCode.CAPABILITY_INVOKE_FAILED
