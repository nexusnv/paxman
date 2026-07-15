"""End-to-end integration test for email canonicalization."""

from __future__ import annotations

import attrs
import pytest

import paxman
from paxman._capabilities.email import EmailCapability
from paxman._core.status import Status
from paxman._registry.capability_registry import CapabilityRegistry


@pytest.fixture(autouse=True)
def _isolated_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    from paxman import _orchestrator_runtime

    r = CapabilityRegistry()
    r.register(EmailCapability())
    r.freeze()
    monkeypatch.setattr(_orchestrator_runtime, "default_registry", r)


@pytest.mark.integration
class TestEndToEnd:
    def test_basic_canonicalization(self) -> None:
        art = paxman.canonicalize("John.Doe@Example.COM", {"kind": "canonical_email"})
        assert art.status is Status.CANONICALIZED
        assert art.value == "john.doe@example.com"

    def test_strip_whitespace(self) -> None:
        art = paxman.canonicalize("  a@b.c\n", {"kind": "canonical_email"})
        assert art.value == "a@b.c"

    def test_replay_byte_equal(self) -> None:
        art = paxman.canonicalize("a@b.c", {"kind": "canonical_email"})
        rehydrated = paxman.replay(art, {"kind": "canonical_email"})
        assert rehydrated == art
        assert rehydrated.canonical_bytes() == art.canonical_bytes()

    def test_idempotence(self) -> None:
        once = paxman.canonicalize("A@B.C", {"kind": "canonical_email"})
        twice = paxman.canonicalize(once.value, {"kind": "canonical_email"})
        assert twice.value == once.value

    def test_invalid_email(self) -> None:
        art = paxman.canonicalize("not-an-email", {"kind": "canonical_email"})
        assert art.status is Status.INVALID

    def test_unknown_contract_kind(self) -> None:
        art = paxman.canonicalize("a@b.c", {"kind": "unknown"})
        assert art.status is Status.UNSUPPORTED

    def test_artifact_is_immutable(self) -> None:
        art = paxman.canonicalize("a@b.c", {"kind": "canonical_email"})
        for field in attrs.fields(art.__class__):
            with pytest.raises(attrs.exceptions.FrozenInstanceError):
                setattr(art, field.name, "x")

    def test_gmail_alias(self) -> None:
        art = paxman.canonicalize(
            "u.s.e.r+tag@gmail.com",
            {"kind": "canonical_email", "provider_aliases": "gmail"},
        )
        assert art.value == "user@gmail.com"

    def test_evidence_present_on_canonicalization(self) -> None:
        art = paxman.canonicalize("USER@EXAMPLE.COM", {"kind": "canonical_email"})
        rule_names = {e.rule for e in art.evidence}
        assert "lowercased_local_part" in rule_names
        assert "lowercased_domain" in rule_names

    def test_strict_mode_rejects_embedded_space(self) -> None:
        art = paxman.canonicalize("a b@c.d", {"kind": "canonical_email", "strict": True})
        assert art.status is Status.INVALID

    def test_ws_padded_canonicalization(self) -> None:
        art = paxman.canonicalize("azahari @ gmail.com", {"kind": "canonical_email"})
        assert art.status is Status.CANONICALIZED
        assert art.value == "azahari@gmail.com"

    def test_verbal_at_dot_canonicalization(self) -> None:
        art = paxman.canonicalize("azahari at gmail dot com", {"kind": "canonical_email"})
        assert art.status is Status.CANONICALIZED
        assert art.value == "azahari@gmail.com"

    def test_ambiguous_gmail_surfaces_candidates(self) -> None:
        art = paxman.canonicalize(
            "john.doe@gmail.com",
            {"kind": "canonical_email", "provider_aliases": "none"},
        )
        assert art.status is Status.AMBIGUOUS
        assert art.candidates is not None
        assert set(art.candidates) == {"john.doe@gmail.com", "johndoe@gmail.com"}
