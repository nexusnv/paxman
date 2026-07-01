"""Unit tests for :mod:`paxman.capabilities.spec` and :mod:`paxman.capabilities.registry`."""

from __future__ import annotations

import pytest

from paxman.capabilities.base import CapabilityContext
from paxman.capabilities.registry import (
    all_capabilities,
    get,
    get_latest,
    register,
    reset,
    unregister,
)
from paxman.capabilities.result import CapabilityResult
from paxman.capabilities.spec import (
    CapabilitySpec,
    CapabilityTier,
    CostHint,
)
from paxman.errors import InvalidContractError

pytestmark = pytest.mark.unit


# --- CostHint --------------------------------------------------------------


def test_cost_hint_defaults() -> None:
    """The default CostHint is free (0 tokens, 1 ms, $0.0)."""
    h = CostHint()
    assert h.tokens == 0
    assert h.ms == 1
    assert h.usd == 0.0


def test_cost_hint_rejects_negative_tokens() -> None:
    with pytest.raises(ValueError, match="tokens must be non-negative"):
        CostHint(tokens=-1)


def test_cost_hint_rejects_negative_ms() -> None:
    with pytest.raises(ValueError, match="ms must be non-negative"):
        CostHint(ms=-1)


def test_cost_hint_rejects_negative_usd() -> None:
    with pytest.raises(ValueError, match="usd must be non-negative"):
        CostHint(usd=-0.01)


def test_cost_hint_rejects_bool_as_int() -> None:
    """Bool is an int subclass; reject to avoid sneaky truthy coercion."""
    with pytest.raises(TypeError, match="tokens must be an int"):
        CostHint(tokens=True)  # type: ignore[arg-type]


def test_cost_hint_rejects_bool_as_usd() -> None:
    with pytest.raises(TypeError, match="usd must be a number"):
        CostHint(usd=True)  # type: ignore[arg-type]


# --- CapabilityTier --------------------------------------------------------


def test_capability_tier_values() -> None:
    """The V1 tier integer values match the spec."""
    assert CapabilityTier.LOCAL_DETERMINISTIC.value == 1
    assert CapabilityTier.STRUCTURED_LOOKUP.value == 2
    assert CapabilityTier.LOCAL_INFERENCE.value == 4
    assert CapabilityTier.REMOTE_INFERENCE.value == 5


# --- CapabilitySpec --------------------------------------------------------


def _spec(**overrides: object) -> CapabilitySpec:
    """Return a sample CapabilitySpec with overrides."""
    base: dict = {
        "id": "regex_extraction",
        "version": "1.0",
        "input_types": ("STRING",),
        "output_type": "STRING",
    }
    base.update(overrides)
    return CapabilitySpec(**base)  # type: ignore[arg-type]


def test_spec_minimal() -> None:
    """A minimal CapabilitySpec is valid (defaults apply)."""
    s = _spec()
    assert s.id == "regex_extraction"
    assert s.version == "1.0"
    assert s.output_type == "STRING"
    assert s.cost_estimate == CostHint()  # default
    assert s.tier is CapabilityTier.LOCAL_DETERMINISTIC  # default
    assert s.deterministic is True  # default


def test_spec_rejects_empty_id() -> None:
    with pytest.raises(ValueError, match="id must be a non-empty string"):
        _spec(id="")


def test_spec_rejects_uppercase_id() -> None:
    """The spec's id is a stable identifier; reject mixed/upper case."""
    with pytest.raises(ValueError, match="id must be lowercase ASCII"):
        _spec(id="Regex_Extraction")


def test_spec_rejects_whitespace_id() -> None:
    with pytest.raises(ValueError, match="id must be lowercase ASCII"):
        _spec(id="regex extraction")  # type: ignore[arg-type]


def test_spec_rejects_empty_version() -> None:
    with pytest.raises(ValueError, match="version must be a non-empty string"):
        _spec(version="")


def test_spec_rejects_empty_output_type() -> None:
    with pytest.raises(ValueError, match="output_type must be a non-empty string"):
        _spec(output_type="")


def test_spec_rejects_non_costhint() -> None:
    with pytest.raises(TypeError, match="cost_estimate must be a CostHint"):
        _spec(cost_estimate={"tokens": 0})  # type: ignore[arg-type]


def test_spec_rejects_non_tier() -> None:
    with pytest.raises(TypeError, match="tier must be a CapabilityTier"):
        _spec(tier="LOCAL_DETERMINISTIC")  # type: ignore[arg-type]


# --- Registry --------------------------------------------------------------


class _SampleCapability:
    """Minimal test capability that satisfies the Protocol."""

    def __init__(self, spec: CapabilitySpec) -> None:
        self._spec = spec

    @property
    def spec(self) -> CapabilitySpec:
        return self._spec

    def invoke(self, ctx: CapabilityContext) -> CapabilityResult:  # pragma: no cover
        return CapabilityResult()


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    """Reset the global registry between tests."""
    reset()
    yield
    reset()


def test_register_and_get() -> None:
    """Register a capability, then get it back."""
    s = _spec(id="alpha", version="1.0")
    register(_SampleCapability(s))
    cap = get("alpha", "1.0")
    assert cap.spec.id == "alpha"


def test_get_unknown_raises() -> None:
    """get() raises InvalidContractError for unknown capability."""
    with pytest.raises(InvalidContractError) as exc_info:
        get("nope", "1.0")
    assert exc_info.value.error_code == "CAPABILITY_NOT_FOUND"


def test_unregister() -> None:
    """unregister() returns True on success, False if not present."""
    s = _spec(id="alpha", version="1.0")
    register(_SampleCapability(s))
    assert unregister("alpha", "1.0") is True
    assert unregister("alpha", "1.0") is False


def test_register_rejects_duplicate() -> None:
    """Re-registering a different instance with the same key raises."""
    s = _spec(id="alpha", version="1.0")
    register(_SampleCapability(s))
    with pytest.raises(InvalidContractError) as exc_info:
        register(_SampleCapability(s))  # different instance, same key
    assert exc_info.value.error_code == "CAPABILITY_ALREADY_REGISTERED"


def test_register_idempotent_for_same_instance() -> None:
    """Re-registering the same instance is a no-op."""
    cap = _SampleCapability(_spec(id="alpha", version="1.0"))
    register(cap)
    register(cap)  # no-op
    assert get("alpha", "1.0") is cap


def test_register_replace_overrides() -> None:
    """register(replace=True) replaces the existing instance."""
    s = _spec(id="alpha", version="1.0")
    cap1 = _SampleCapability(s)
    cap2 = _SampleCapability(s)
    register(cap1)
    register(cap2, replace=True)
    assert get("alpha", "1.0") is cap2


def test_get_latest() -> None:
    """get_latest returns the highest semver."""
    for v in ("1.0", "2.0", "1.5"):
        register(_SampleCapability(_spec(id="alpha", version=v)))
    cap = get_latest("alpha")
    assert cap.spec.version == "2.0"


def test_get_latest_prefers_most_recently_registered_non_semver() -> None:
    """For non-semver versions, get_latest returns the most recently registered."""
    # Register in order; the second is "more recent" by the secondary key.
    cap1 = _SampleCapability(_spec(id="alpha", version="1.0-rc1"))
    cap2 = _SampleCapability(_spec(id="alpha", version="1.0-rc2"))
    register(cap1)
    register(cap2)
    cap = get_latest("alpha")
    # cap2 was registered later, so it should be preferred.
    assert cap is cap2


def test_get_latest_unknown_raises() -> None:
    with pytest.raises(InvalidContractError) as exc_info:
        get_latest("nope")
    assert exc_info.value.error_code == "CAPABILITY_NOT_FOUND"


def test_all_capabilities_returns_readonly_snapshot() -> None:
    """all_capabilities() returns a MappingProxyType."""
    s = _spec(id="alpha", version="1.0")
    register(_SampleCapability(s))
    snap = all_capabilities()
    assert ("alpha", "1.0") in snap
    with pytest.raises(TypeError):
        snap[("alpha", "1.0")] = None  # type: ignore[index]


def test_all_capabilities_is_a_point_in_time_snapshot() -> None:
    """A new registration after a snapshot does not affect the snapshot."""
    s1 = _spec(id="alpha", version="1.0")
    register(_SampleCapability(s1))
    snap_before = all_capabilities()
    assert ("alpha", "1.0") in snap_before
    # Register a new capability.
    s2 = _spec(id="beta", version="1.0")
    register(_SampleCapability(s2))
    # The snapshot is unchanged.
    assert ("alpha", "1.0") in snap_before
    assert ("beta", "1.0") not in snap_before
    # A fresh call returns the new state.
    snap_after = all_capabilities()
    assert ("beta", "1.0") in snap_after


def test_register_rejects_missing_spec_attribute() -> None:
    """A capability without a spec attribute raises TypeError."""

    class _NoSpec:
        def invoke(self, ctx: object) -> object:  # pragma: no cover
            return None

    with pytest.raises(TypeError, match="capability must implement spec and invoke"):
        register(_NoSpec())  # type: ignore[arg-type]


def test_register_rejects_missing_invoke() -> None:
    class _NoInvoke:
        @property
        def spec(self) -> object:
            return _spec()

    with pytest.raises(TypeError, match="capability must implement spec and invoke"):
        register(_NoInvoke())  # type: ignore[arg-type]


def test_register_rejects_non_capabilityspec() -> None:
    """If the spec is not a CapabilitySpec, raise TypeError."""

    class _BadSpec:
        @property
        def spec(self) -> object:
            return {"id": "alpha", "version": "1.0"}

        def invoke(self, ctx: CapabilityContext) -> CapabilityResult:  # pragma: no cover
            return CapabilityResult()

    with pytest.raises(TypeError, match=r"capability\.spec must be a CapabilitySpec"):
        register(_BadSpec())  # type: ignore[arg-type]


# --- V1.1.0 format-aware extraction specs ---------------------------------


def test_json_path_extraction_spec_is_registerable() -> None:
    """The V1.1.0 json_path_extraction spec is registerable with the correct shape."""
    from paxman.capabilities.v1.json_path_extraction import (
        JsonPathExtractionCapability,
    )

    cap = JsonPathExtractionCapability()
    register(cap, replace=True)
    looked_up = get("json_path_extraction", "1.0")
    assert looked_up.spec.id == "json_path_extraction"
    assert looked_up.spec.version == "1.0"
    assert looked_up.spec.tier is CapabilityTier.LOCAL_DETERMINISTIC
    assert looked_up.spec.deterministic is True
    assert looked_up.spec.cost_estimate == CostHint(tokens=0, ms=1, usd=0.0)
    assert "STRING" in looked_up.spec.input_types
    assert "MIXED" in looked_up.spec.input_types


def test_csv_extraction_spec_is_registerable() -> None:
    """The V1.1.0 csv_extraction spec is registerable with the correct shape."""
    from paxman.capabilities.v1.csv_extraction import CsvExtractionCapability

    cap = CsvExtractionCapability()
    register(cap, replace=True)
    looked_up = get("csv_extraction", "1.0")
    assert looked_up.spec.id == "csv_extraction"
    assert looked_up.spec.version == "1.0"
    assert looked_up.spec.tier is CapabilityTier.LOCAL_DETERMINISTIC
    assert looked_up.spec.deterministic is True
    assert looked_up.spec.cost_estimate == CostHint(tokens=0, ms=1, usd=0.0)
    assert "STRING" in looked_up.spec.input_types
    assert "MIXED" in looked_up.spec.input_types


def test_xpath_extraction_spec_is_registerable() -> None:
    """The V1.1.0 xpath_extraction spec is registerable with the correct shape."""
    from paxman.capabilities.v1.xpath_extraction import XPathExtractionCapability

    cap = XPathExtractionCapability()
    register(cap, replace=True)
    looked_up = get("xpath_extraction", "1.0")
    assert looked_up.spec.id == "xpath_extraction"
    assert looked_up.spec.version == "1.0"
    assert looked_up.spec.tier is CapabilityTier.LOCAL_DETERMINISTIC
    assert looked_up.spec.deterministic is True
    assert looked_up.spec.cost_estimate == CostHint(tokens=0, ms=1, usd=0.0)
    assert "STRING" in looked_up.spec.input_types
    assert "MIXED" in looked_up.spec.input_types


# --- ADR-0012: V1 capabilities self-register on import --------------------
#
# V1 ships 8 built-in capabilities (per PACKAGE_STRUCTURE.md §12,
# ARCHITECTURE.md §4.3, and ADR-0012):
#
# - 5 original V1 capabilities (Sprint 3):
#   text_extraction, regex_extraction, lookup, inference, validation
# - 3 V1.1.0 format-aware extraction capabilities (PR #71, sub-issue
#   of #67):
#   json_path_extraction, csv_extraction, xpath_extraction
#
# All 8 self-register on import and are re-registered by
# ``_bootstrap_v1_capabilities()`` after a ``reset()`` call. This
# constant is the single source of truth for the V1 built-in set; any
# new first-party capability MUST be added here AND to the
# import-linter ``source_modules`` list in pyproject.toml (see #80).

_V1_CAPABILITY_IDS: tuple[str, ...] = (
    "text_extraction",
    "regex_extraction",
    "lookup",
    "inference",
    "validation",
    "json_path_extraction",
    "csv_extraction",
    "xpath_extraction",
)


def test_v1_capabilities_self_register_on_import() -> None:
    """All eight V1 capabilities self-register on import (ADR-0012).

    The fixtures above call :func:`reset` between tests, which
    clears the registry. Importing the V1 module is what
    repopulates it, via the ``_register_on_import()`` hook at the
    bottom of each :mod:`paxman.capabilities.v1.*` module.
    """
    reset()
    # Importing the V1 module triggers the per-module
    # ``_register_on_import()`` hooks (ADR-0012).
    import paxman.capabilities.v1  # noqa: F401  (side effect: self-registration)

    registered = {cid for cid, _ in all_capabilities().keys()}
    for cid in _V1_CAPABILITY_IDS:
        assert cid in registered, (
            f"V1 capability {cid!r} did not self-register on import; "
            f"registry contains: {sorted(registered)}"
        )


def test_bootstrap_re_registers_all_v1_capabilities_after_reset() -> None:
    """After :func:`reset`, the next :func:`all_capabilities` call
    re-registers **all eight** V1 capabilities uniformly (ADR-0012).

    Pre-ADR-0012, the bootstrap only re-registered ``lookup``;
    the other seven were silently absent until the caller
    explicitly registered them.

    Regression test for #79: the 3 V1.1.0 format extractors
    (``json_path_extraction``, ``csv_extraction``, ``xpath_extraction``)
    were added in PR #71 but not wired into
    ``_bootstrap_v1_capabilities()``; the bootstrap dropped them
    silently after any ``reset()`` call (e.g. in
    ``tests/unit/test_planner_heuristics_planner.py`` and
    ``tests/property/test_planner_determinism.py`` fixtures).
    """
    # Populate the registry once, then wipe it.
    import paxman.capabilities.v1  # noqa: F401

    reset()
    # The internal table is now empty. ``all_capabilities()`` is
    # self-healing — calling it triggers the bootstrap, so it
    # always returns the V1 surface after a ``reset()`` as long
    # as the V1 module has been imported. We assert on the result
    # of the self-heal, not on the empty state (which is private
    # and would require touching ``_capabilities``).
    registered = {cid for cid, _ in all_capabilities().keys()}
    for cid in _V1_CAPABILITY_IDS:
        assert cid in registered, (
            f"Bootstrap did not re-register V1 capability {cid!r} "
            f"after reset(); got: {sorted(registered)}"
        )


def test_v1_1_format_extractors_have_import_time_registration_hook() -> None:
    """The 3 V1.1.0 format extractors each ship a module-level
    ``_register_on_import()`` hook that registers the capability on
    import (ADR-0012, per-module invariant).

    This is the import-time side of the ADR-0012 contract; the
    ``_bootstrap_v1_capabilities()`` helper is the post-``reset()``
    side. Both must be present for a V1 first-party capability.
    """
    import paxman.capabilities.v1.csv_extraction as csv_mod
    import paxman.capabilities.v1.json_path_extraction as json_path_mod
    import paxman.capabilities.v1.xpath_extraction as xpath_mod

    for mod in (csv_mod, json_path_mod, xpath_mod):
        assert hasattr(mod, "_register_on_import"), (
            f"{mod.__name__} is missing the _register_on_import() hook "
            f"required by ADR-0012 (see #79)"
        )
        assert callable(mod._register_on_import), (
            f"{mod.__name__}._register_on_import is not callable"
        )
        # And the hook must have been invoked at module load time —
        # i.e. the capability must already be in the registry before
        # we call reset() here. We assert by checking the hook is the
        # function object (not None) and by inspecting the module's
        # own capability class identity (verified by the
        # self-registration test above; here we only assert the
        # hook is present and importable).
