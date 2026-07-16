"""Tests for builtin_capabilities() and CapabilityRegistry.load_builtins().

Spec §2.4: builtin_capabilities() lists the built-in capabilities
shipped with this version. load_builtins() is idempotent, no-op on a
frozen registry, preserves user capabilities of the same name, and
never raises on duplicates. The orchestrator calls load_builtins()
BEFORE freeze() on the first canonicalize (Law 8a — no import-time
hidden state).
"""

from __future__ import annotations

from paxman._capabilities.date import DateCapability
from paxman._capabilities.discovery import builtin_capabilities
from paxman._capabilities.email import EmailCapability
from paxman._capabilities.email.contract import CanonicalEmailContract
from paxman._capabilities.phone import PhoneCapability
from paxman._capabilities.uuid import UUIDCapability
from paxman._registry.capability_registry import CapabilityRegistry


class TestBuiltinCapabilities:
    def test_returns_list_of_email_and_uuid_capabilities(self) -> None:
        result = builtin_capabilities()
        assert isinstance(result, list)
        assert len(result) == 4
        names = {c.name for c in result}
        assert names == {
            "email_canonicalization",
            "uuid_canonicalization",
            "date_canonicalization",
            "phone_canonicalization",
        }
        assert any(isinstance(c, EmailCapability) for c in result)
        assert any(isinstance(c, UUIDCapability) for c in result)
        assert any(isinstance(c, DateCapability) for c in result)
        assert any(isinstance(c, PhoneCapability) for c in result)

    def test_returns_fresh_instances_on_each_call(self) -> None:
        # No shared mutable state across calls (Law 1, Law 8a).
        a = builtin_capabilities()
        b = builtin_capabilities()
        assert a is not b
        assert [c.name for c in a] == [c.name for c in b]
        assert [c.name for c in a] == [
            "email_canonicalization",
            "uuid_canonicalization",
            "date_canonicalization",
            "phone_canonicalization",
        ]


class TestLoadBuiltins:
    def test_registers_email_capability_in_empty_registry(self) -> None:
        registry = CapabilityRegistry()
        registry.load_builtins(builtin_capabilities())
        # The capability is now registered under its name. The registry
        # is not frozen — we can resolve.
        claimants = registry.resolve_all(
            CanonicalEmailContract(),
            "a@b.c",
        )
        assert len(claimants) == 1
        assert claimants[0].name == "email_canonicalization"

    def test_idempotent_on_repeat_call(self) -> None:
        registry = CapabilityRegistry()
        builtins = builtin_capabilities()
        registry.load_builtins(builtins)
        # Second call with the same list: no duplicate registration,
        # no raise. The set of registered names is the same.
        registry.load_builtins(builtins)
        claimants = registry.resolve_all(
            CanonicalEmailContract(),
            "a@b.c",
        )
        assert len(claimants) == 1

    def test_preserves_user_capability_of_same_name(self) -> None:
        # A user who registers a custom email capability BEFORE the
        # first canonicalize is exercising Law 6 (teaching Paxman new
        # knowledge). load_builtins must NOT overwrite their
        # capability (§5.3 litmus: the user's knowledge wins).
        #
        # The cleanest, registry-internal-state-free way to assert this
        # is via capabilities_hash: the user-only registry and the
        # (user-then-load_builtins) registry must produce the same hash,
        # proving the built-in was NOT silently added alongside the
        # user's same-name capability.
        class MyEmailCap:
            name = "email_canonicalization"

            def can_handle(self, contract: object, value: object) -> bool:
                return False

            def canonicalize(self, value: object, contract: object) -> object:
                raise NotImplementedError

        # Registry A: user registers their cap, then load_builtins is
        # called (the orchestrator's path). The built-in must be
        # skipped because the name is already taken.
        registry_a = CapabilityRegistry()
        registry_a.register(MyEmailCap())
        registry_a.load_builtins(builtin_capabilities())
        registry_a.freeze()

        registry_b = CapabilityRegistry()
        registry_b.register(MyEmailCap())
        registry_b.register(UUIDCapability())
        registry_b.register(DateCapability())
        registry_b.register(PhoneCapability())
        registry_b.freeze()

        assert registry_a.capabilities_hash() == registry_b.capabilities_hash()

    def test_no_op_on_frozen_registry(self) -> None:
        registry = CapabilityRegistry()
        registry.freeze()
        # load_builtins on a frozen registry is a no-op, not a raise.
        registry.load_builtins(builtin_capabilities())
        # Nothing was registered.
        claimants = registry.resolve_all(
            CanonicalEmailContract(),
            "a@b.c",
        )
        assert claimants == []

    def test_capabilities_hash_after_load_builtins_matches_register(self) -> None:
        # Determinism: the capabilities_hash after load_builtins must
        # equal the capabilities_hash after explicit register of the
        # same built-in. This is what makes replay work — replay
        # recomputes capabilities_hash from default_registry.
        via_load = CapabilityRegistry()
        via_load.load_builtins(builtin_capabilities())
        via_load.freeze()

        via_register = CapabilityRegistry()
        via_register.register(EmailCapability())
        via_register.register(UUIDCapability())
        via_register.register(DateCapability())
        via_register.register(PhoneCapability())
        via_register.freeze()

        assert via_load.capabilities_hash() == via_register.capabilities_hash()
