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


# ---------------------------------------------------------------------------
# Bootstrap fix (v1.0.2 #64 regression): _bootstrap_v1_capabilities
# ---------------------------------------------------------------------------


class TestBootstrapV1Capabilities:
    """After #64, the v1 package is no longer loaded transitively. The
    bootstrap in :func:`all_capabilities` must actively import the v1
    lookup module so the planner always sees a registered ``lookup``
    capability. This test catches a regression where the bootstrap
    becomes a no-op (e.g. if someone removes the
    ``importlib.import_module`` call in favor of a ``sys.modules.get``
    short-circuit).
    """

    def test_all_capabilities_re_registers_lookup_after_reset(self) -> None:
        """After ``reset()`` empties the registry, ``all_capabilities()``
        must transparently re-register the V1 ``lookup`` capability.
        This is the contract that golden-artifact tests rely on.

        We test the side effect via the private ``_capabilities`` dict
        rather than via :func:`all_capabilities` (which would itself
        trigger the bootstrap, making the test vacuous).
        """
        from paxman.capabilities import registry as _registry

        # Empty the registry (simulates test isolation).
        reset()
        # Verify the underlying dict is empty (before bootstrap).
        assert len(_registry._capabilities) == 0, (
            f"precondition: registry should be empty after reset(), got {_registry._capabilities!r}"
        )
        # Trigger the bootstrap by calling all_capabilities().
        caps = all_capabilities()
        # The V1 lookup must now be re-registered.
        assert ("lookup", "1.0") in caps, (
            "all_capabilities() should re-register the V1 lookup "
            "capability when the registry is empty"
        )
        # And the underlying dict must now contain it.
        assert ("lookup", "1.0") in _registry._capabilities

    def test_bootstrap_does_not_register_uncalled_capabilities(self) -> None:
        """The bootstrap must only register ``lookup`` (the only V1
        capability that self-registers on import). The other 4 V1
        capabilities (text_extraction, regex_extraction, inference,
        validation) are NOT part of the default registry — they must
        be registered explicitly by the user. This matches the
        original V1 design.
        """
        reset()
        caps = all_capabilities()
        registered = set(caps)
        # ``lookup`` is the only V1 capability that auto-registers.
        assert ("lookup", "1.0") in registered
        # The other V1 capabilities must NOT be auto-registered.
        for other in (
            "text_extraction",
            "regex_extraction",
            "inference",
            "validation",
        ):
            assert (other, "1.0") not in registered, (
                f"{other} must not be auto-registered by the bootstrap"
            )
