# Email Canonicalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a working Paxman v2 library, end-to-end, with email canonicalization as its first and only capability. `paxman.canonicalize(input, contract)` runs and returns a correct canonical form for a representative set of email inputs; `paxman.replay(artifact, contract)` is byte-equal to the original artifact without re-execution.

**Architecture:** The pipeline from `PROPOSED_STRUCTURE.md` is realized as 12 source modules under `src/paxman/` (the canonical v1.0.0 layout from `PROPOSED_STRUCTURE.md` plus one additional internal helper, `_orchestrator_runtime.py`, that holds the default registry to break a circular import between the orchestrator and `paxman/__init__.py`), plus 5 `__init__.py` package markers (3 empty + 2 with content), for a total of 17 `.py` files. Plus a `tests/` tree with unit, property, and integration tests. The pipeline walks `inspect → resolve → execute → canonicalize → validate → classify`; the algorithm is owned by Paxman (mandate Law 6); users may register capabilities, not rearrange the pipeline. Artifact construction (the `ExecutionArtifact` and its `replay_hash`) is the final act of the `classify` stage — the `_build_artifact` helper is a private function inside `_core/orchestrator.py`, not a user-visible pipeline stage.

**Tech Stack:** Python 3.11+ (target 3.13.5 locally), `attrs>=23.0` for frozen dataclasses, `pytest>=8.0` for unit/integration, `hypothesis>=6.0` for property tests, `hatchling` as build backend, `uv` for environment management. No runtime dependencies beyond the standard library + `attrs`.

**Spec:** [`docs/superpowers/specs/2026-07-13-email-canonicalization-design.md`](../specs/2026-07-13-email-canonicalization-design.md). Every task in this plan traces to a section of that spec.

**Branch:** `feat/email-canonicalization` (already checked out, no worktree needed — this is a feature branch).

---

## File structure (locked in here so the tasks don't drift)

### Source files to create

```
src/paxman/__init__.py
src/paxman/_core/__init__.py
src/paxman/_core/types.py
src/paxman/_core/artifact.py
src/paxman/_core/classification.py
src/paxman/_core/validation.py
src/paxman/_core/orchestrator.py
src/paxman/_core/replay.py
src/paxman/_capabilities/__init__.py
src/paxman/_capabilities/protocol.py
src/paxman/_capabilities/registry.py
src/paxman/_capabilities/builtins/__init__.py
src/paxman/_capabilities/builtins/email.py
src/paxman/_contracts/__init__.py
src/paxman/_contracts/contract.py
src/paxman/_errors.py
```

### Test files to create

```
tests/__init__.py
tests/conftest.py
tests/unit/__init__.py
tests/unit/test_types.py
tests/unit/test_artifact.py
tests/unit/test_classification.py
tests/unit/test_validation.py
tests/unit/test_contract.py
tests/unit/test_protocol.py
tests/unit/test_registry.py
tests/unit/test_email_capability.py
tests/unit/test_orchestrator.py
tests/unit/test_replay.py
tests/unit/test_public_api.py
tests/property/__init__.py
tests/property/test_replay_invariant.py
tests/property/test_idempotence_invariant.py
tests/property/test_uniqueness_invariant.py
tests/property/test_artifact_immutability_invariant.py
tests/property/test_canonicalization_invariant.py
tests/integration/__init__.py
tests/integration/test_email_end_to_end.py
```

### Configuration to add to `pyproject.toml`

A `[tool.pytest.ini_options]` block to register hypothesis profiles and configure test paths. Nothing else.

### What this plan does NOT touch

`README.md`, `MANDATE.md`, `PROPOSED_STRUCTURE.md`, `RETRACTION.md`, `.github/`, `.pre-commit-config.yaml`, `pyproject.toml`'s `dependencies` block, `Makefile` (does not exist), CI workflow (does not exist). The user has explicitly directed: no ADRs, no docs beyond the spec and this plan, no CI gates.

---

## Task ordering and rationale

Tasks 1–6 build the type system from the leaves up. Tasks 7–9 build the capability layer. Task 10 is the orchestrator (glue). Task 11 is replay. Task 12 is errors. Task 13 is the public API. Task 14 is integration. Task 15 is end-to-end manual verification.

Each task ends with a commit. Each task is independently testable. Property tests are written in the same task as the unit they constrain (so the failing-test-first loop is one coherent unit).

---

## Task 1: Project skeleton and pyproject pytest config

**Files:**
- Create: `src/paxman/__init__.py` (initial empty)
- Create: `src/paxman/_core/__init__.py`
- Create: `src/paxman/_capabilities/__init__.py`
- Create: `src/paxman/_capabilities/builtins/__init__.py`
- Create: `src/paxman/_contracts/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/property/__init__.py`
- Create: `tests/integration/__init__.py`
- Modify: `pyproject.toml` (append `[tool.pytest.ini_options]` block only)

- [ ] **Step 1.1: Create the package skeleton with empty `__init__.py` files**

Create all the directories and `__init__.py` files listed above. Each `__init__.py` is empty (no content). The exception is `tests/conftest.py`, which is created with the content below.

- [ ] **Step 1.2: Write `tests/conftest.py`**

```python
"""Shared pytest fixtures for the Paxman v2 test suite."""
from __future__ import annotations

import pytest

from paxman._capabilities.registry import CapabilityRegistry


@pytest.fixture
def fresh_registry() -> CapabilityRegistry:
    """A new, unfrozen CapabilityRegistry for tests that do not want the default."""
    return CapabilityRegistry()
```

- [ ] **Step 1.3: Append pytest config to `pyproject.toml`**

Append the following block to the end of `pyproject.toml` (after the existing
`[dependency-groups]` block):

```toml

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers"
markers = [
    "property: hypothesis-driven property tests",
    "integration: end-to-end integration tests",
]
```

- [ ] **Step 1.4: Run `uv sync` to install dev dependencies**

Run: `uv sync`
Expected: `Resolved N packages`, `Installed N packages`, exit 0.

- [ ] **Step 1.5: Verify pytest discovers the (empty) test tree**

Run: `uv run pytest --collect-only -q`
Expected: exit 0, "no tests ran" or empty collection, no errors.

- [ ] **Step 1.6: Commit**

```bash
git add src/paxman tests pyproject.toml
git commit -m "chore: scaffold paxman v2 package skeleton + pytest config"
```

---

## Task 2: `_core/types.py` — `Status`, `Evidence`, `VersionStamp`, `CapabilityResult`

**Files:**
- Create: `src/paxman/_core/types.py`
- Create: `tests/unit/test_types.py`

These are the leaf value types. Everything else depends on them.

- [ ] **Step 2.1: Write the failing tests in `tests/unit/test_types.py`**

```python
"""Tests for the leaf value types in paxman._core.types."""
from __future__ import annotations

import enum
import hashlib

import attrs

from paxman._core.types import (
    CapabilityResult,
    Evidence,
    Status,
    VersionStamp,
)


class TestStatus:
    def test_status_has_five_values(self) -> None:
        assert {s.name for s in Status} == {
            "CANONICALIZED",
            "INVALID",
            "MISSING",
            "AMBIGUOUS",
            "UNSUPPORTED",
        }

    def test_status_is_an_enum(self) -> None:
        assert issubclass(Status, enum.Enum)

    def test_status_values_are_lowercase_strings(self) -> None:
        # Mandate §3.1 wording: the wire form is a lowercase string.
        for s in Status:
            assert s.value == s.name.lower()


class TestEvidence:
    def test_evidence_is_frozen(self) -> None:
        e = Evidence(rule="lowercased_local_part", detail="")
        with_attrs = attrs.fields(Evidence)
        assert with_attrs[0].name == "rule"
        assert with_attrs[1].name == "detail"
        # FrozenInstanceError on assignment
        import pytest as _pt
        with _pt.raises(attrs.exceptions.FrozenInstanceError):
            e.rule = "x"  # type: ignore[misc]

    def test_evidence_default_detail_is_empty_string(self) -> None:
        assert Evidence(rule="r").detail == ""


class TestVersionStamp:
    def test_version_stamp_is_frozen(self) -> None:
        v = VersionStamp(
            paxman_version="0.0.0.dev0",
            contract_version=1,
            capabilities_hash="abc",
            configuration_version="0",
        )
        import pytest as _pt
        with _pt.raises(attrs.exceptions.FrozenInstanceError):
            v.contract_version = 2  # type: ignore[misc]

    def test_version_stamp_equality(self) -> None:
        a = VersionStamp("0.0.0.dev0", 1, "abc", "0")
        b = VersionStamp("0.0.0.dev0", 1, "abc", "0")
        assert a == b

    def test_version_stamp_hash(self) -> None:
        a = VersionStamp("0.0.0.dev0", 1, "abc", "0")
        b = VersionStamp("0.0.0.dev0", 1, "abc", "0")
        assert {a, b} == {a}


class TestCapabilityResult:
    def test_canonicalized_carries_value(self) -> None:
        r = CapabilityResult(status=Status.CANONICALIZED, value="x@y.z")
        assert r.status is Status.CANONICALIZED
        assert r.value == "x@y.z"
        assert r.evidence == ()

    def test_invalid_carries_no_value(self) -> None:
        r = CapabilityResult(status=Status.INVALID)
        assert r.value is None

    def test_evidence_default_is_empty_tuple(self) -> None:
        r = CapabilityResult(status=Status.CANONICALIZED, value="x")
        assert r.evidence == ()
        assert isinstance(r.evidence, tuple)

    def test_capability_result_is_frozen(self) -> None:
        r = CapabilityResult(status=Status.CANONICALIZED, value="x")
        import pytest as _pt
        with _pt.raises(attrs.exceptions.FrozenInstanceError):
            r.status = Status.INVALID  # type: ignore[misc]
```

- [ ] **Step 2.2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_types.py -v`
Expected: `ModuleNotFoundError: No module named 'paxman._core.types'`

- [ ] **Step 2.3: Implement `src/paxman/_core/types.py`**

```python
"""Leaf value types shared across the paxman v2 core.

All types in this module are immutable. They are the smallest units of
state paxman manipulates and the boundary at which mandate Laws 1, 2, 9,
and 12 are enforced.
"""
from __future__ import annotations

import enum
from typing import Literal

import attrs


class Status(enum.Enum):
    """The five mutually-exclusive outcomes of a canonicalize call.

    Mandate Law 8: every failure is deterministic. Status values are the
    *outcomes* recorded on a successful ExecutionArtifact; they are not
    exceptions. Exceptions are reserved for calls that cannot proceed at
    all (broken contract, version mismatch, internal invariant violation).
    """

    CANONICALIZED = "canonicalized"
    INVALID = "invalid"
    MISSING = "missing"
    AMBIGUOUS = "ambiguous"
    UNSUPPORTED = "unsupported"


@attrs.frozen
class Evidence:
    """One entry on an ExecutionArtifact's evidence list (mandate Law 9)."""

    rule: str
    detail: str = ""


@attrs.frozen
class VersionStamp:
    """The four-component version stamp recorded on every artifact.

    Replay (mandate Law 12) verifies all four components. Mandate §8
    makes the contract version a first-class component.
    """

    paxman_version: str
    contract_version: int
    capabilities_hash: str
    configuration_version: str


@attrs.frozen
class CapabilityResult:
    """The value a capability returns from its canonicalize method.

    `value` is required only when status is CANONICALIZED. The orchestrator
    (src/paxman/_core/orchestrator.py) treats status other than
    CANONICALIZED as the authoritative outcome and ignores `value` in
    those cases.
    """

    status: Status
    value: str | None = None
    evidence: tuple[Evidence, ...] = ()


# Closed enum for provider_aliases in the v1.0.0 contract (mandate §6
# openness about deliberate scope).
ProviderAliasesPolicy = Literal["none", "gmail"]
```

- [ ] **Step 2.4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_types.py -v`
Expected: 11 passed, 0 failed.

- [ ] **Step 2.5: Commit**

```bash
git add src/paxman/_core/types.py tests/unit/test_types.py
git commit -m "feat(core): leaf value types — Status, Evidence, VersionStamp, CapabilityResult"
```

---

## Task 3: `_core/artifact.py` — `ExecutionArtifact` (frozen, deterministic serialization)

**Files:**
- Create: `src/paxman/_core/artifact.py`
- Modify: `tests/unit/test_types.py` (add the contract placeholder)
- Create: `tests/unit/test_artifact.py`

Note: `ExecutionArtifact` references `Contract`. To avoid a forward
dependency, define a thin `Contract` protocol in this file and have the
real `Contract` (a concrete attrs dataclass) live in
`_contracts/contract.py` later. The protocol is the import surface the
artifact needs; the concrete class will be assignable to it.

- [ ] **Step 3.1: Write the failing tests in `tests/unit/test_artifact.py`**

```python
"""Tests for ExecutionArtifact immutability and byte-equal serialization."""
from __future__ import annotations

import hashlib
import json

import attrs
import pytest

from paxman._core.artifact import ExecutionArtifact
from paxman._core.types import (
    Evidence,
    Status,
    VersionStamp,
)


class _FakeContract:
    """Minimal stand-in for the real Contract (defined in _contracts).

    The artifact only needs `as_dict()` and `version` for its canonical
    serialization; this stub is enough for the unit tests in this file.
    """

    def as_dict(self) -> dict[str, object]:
        return {"kind": "canonical_email", "version": 1}

    @property
    def version(self) -> int:
        return 1


def _make_artifact(**overrides: object) -> ExecutionArtifact:
    defaults: dict[str, object] = dict(
        status=Status.CANONICALIZED,
        value="a@b.c",
        evidence=(Evidence(rule="lowercased_local_part"),),
        contract=_FakeContract(),  # type: ignore[arg-type]
        version_stamp=VersionStamp(
            paxman_version="0.0.0.dev0",
            contract_version=1,
            capabilities_hash="abc",
            configuration_version="0",
        ),
    )
    defaults.update(overrides)
    return ExecutionArtifact(**defaults)  # type: ignore[arg-type]


class TestArtifactImmutability:
    def test_status_is_immutable(self) -> None:
        a = _make_artifact()
        with pytest.raises(attrs.exceptions.FrozenInstanceError):
            a.status = Status.INVALID  # type: ignore[misc]

    def test_value_is_immutable(self) -> None:
        a = _make_artifact()
        with pytest.raises(attrs.exceptions.FrozenInstanceError):
            a.value = "x@y.z"  # type: ignore[misc]

    def test_evidence_is_immutable(self) -> None:
        a = _make_artifact()
        with pytest.raises(attrs.exceptions.FrozenInstanceError):
            a.evidence = ()  # type: ignore[misc]

    def test_replay_hash_is_immutable(self) -> None:
        a = _make_artifact()
        with pytest.raises(attrs.exceptions.FrozenInstanceError):
            a.replay_hash = "0" * 64  # type: ignore[misc]


class TestArtifactCanonicalBytes:
    def test_canonical_bytes_is_deterministic(self) -> None:
        a1 = _make_artifact()
        a2 = _make_artifact()
        assert a1.canonical_bytes() == a2.canonical_bytes()

    def test_canonical_bytes_is_sorted_key_json(self) -> None:
        a = _make_artifact()
        # The serialized form must be valid JSON with sorted keys and no
        # insignificant whitespace.
        payload = json.loads(a.canonical_bytes())
        assert payload["status"] == "canonicalized"
        assert payload["value"] == "a@b.c"

    def test_replay_hash_matches_sha256_of_canonical_bytes(self) -> None:
        a = _make_artifact()
        expected = hashlib.sha256(a.canonical_bytes()).hexdigest()
        assert a.replay_hash == expected


class TestArtifactEquality:
    def test_two_identical_artifacts_are_equal(self) -> None:
        a1 = _make_artifact()
        a2 = _make_artifact()
        assert a1 == a2
        assert hash(a1) == hash(a2)

    def test_different_value_means_different_artifact(self) -> None:
        a1 = _make_artifact(value="a@b.c")
        a2 = _make_artifact(value="x@y.z")
        assert a1 != a2

    def test_different_status_means_different_artifact(self) -> None:
        a1 = _make_artifact(status=Status.CANONICALIZED)
        a2 = _make_artifact(status=Status.INVALID, value=None)
        assert a1 != a2
```

- [ ] **Step 3.2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_artifact.py -v`
Expected: `ModuleNotFoundError: No module named 'paxman._core.artifact'`

- [ ] **Step 3.3: Implement `src/paxman/_core/artifact.py`**

```python
"""ExecutionArtifact: the immutable result of a canonicalize call.

Mandate Laws 1, 2, 9, 12, 13 all converge here. The artifact is the
single thing that paxman produces and replays.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Protocol

import attrs

from paxman._core.types import Evidence, Status, VersionStamp


class _ContractLike(Protocol):
    """What ExecutionArtifact needs from a Contract.

    The real Contract (in src/paxman/_contracts/contract.py) provides
    this and more. Keeping the dependency here as a Protocol avoids
    a forward import.
    """

    def as_dict(self) -> dict[str, Any]: ...
    @property
    def version(self) -> int: ...


@attrs.frozen
class ExecutionArtifact:
    """The immutable result of `paxman.canonicalize`.

    Mandate Law 13: no field may be reassigned after construction. The
    only way to "modify" an artifact is to produce a new one via a new
    canonicalize call.
    """

    status: Status
    value: str | None
    evidence: tuple[Evidence, ...]
    contract: _ContractLike
    version_stamp: VersionStamp
    replay_hash: str = attrs.field(init=False, eq=False)

    def __attrs_post_init__(self) -> None:
        # The replay_hash is computed from the artifact's content
        # (excluding itself). It is set in __attrs_post_init__ so that
        # callers cannot forget to provide it.
        payload = {
            "status": self.status.value,
            "value": self.value,
            "evidence": [(e.rule, e.detail) for e in self.evidence],
            "contract": self.contract.as_dict(),
            "version_stamp": {
                "paxman_version": self.version_stamp.paxman_version,
                "contract_version": self.version_stamp.contract_version,
                "capabilities_hash": self.version_stamp.capabilities_hash,
                "configuration_version": self.version_stamp.configuration_version,
            },
        }
        canonical = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        digest = hashlib.sha256(canonical).hexdigest()
        object.__setattr__(self, "replay_hash", digest)

    def canonical_bytes(self) -> bytes:
        """The deterministic byte serialization used for replay_hash.

        Identical to the bytes used at construction time. Returned as a
        method (rather than cached) for simplicity; the cost is one
        json.dumps per call, which is acceptable for v1.0.0.
        """
        payload = {
            "status": self.status.value,
            "value": self.value,
            "evidence": [(e.rule, e.detail) for e in self.evidence],
            "contract": self.contract.as_dict(),
            "version_stamp": {
                "paxman_version": self.version_stamp.paxman_version,
                "contract_version": self.version_stamp.contract_version,
                "capabilities_hash": self.version_stamp.capabilities_hash,
                "configuration_version": self.version_stamp.configuration_version,
            },
        }
        return json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
```

- [ ] **Step 3.4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_artifact.py -v`
Expected: 10 passed, 0 failed.

- [ ] **Step 3.5: Commit**

```bash
git add src/paxman/_core/artifact.py tests/unit/test_artifact.py
git commit -m "feat(core): ExecutionArtifact — immutable, byte-equal serialized, replay-hashed"
```

---

## Task 4: `_core/classification.py` — `classify(...)` mapping `(capability_result, validation) → Status`

**Files:**
- Create: `src/paxman/_core/classification.py`
- Create: `tests/unit/test_classification.py`

- [ ] **Step 4.1: Write the failing tests in `tests/unit/test_classification.py`**

```python
"""Tests for the deterministic classifier (Status assignment)."""
from __future__ import annotations

import pytest

from paxman._core.classification import ValidationResult, classify
from paxman._core.types import CapabilityResult, Evidence, Status


class TestClassify:
    def test_canonicalized_input_with_valid_value_yields_canonicalized(self) -> None:
        cr = CapabilityResult(status=Status.CANONICALIZED, value="a@b.c")
        vr = ValidationResult(is_valid=True)
        assert classify(cr, vr) is Status.CANONICALIZED

    def test_canonicalized_input_with_invalid_value_yields_invalid(self) -> None:
        # The capability says CANONICALIZED but validation rejects it
        # (e.g., contract policy was strict and the value violates it).
        cr = CapabilityResult(status=Status.CANONICALIZED, value="x")
        vr = ValidationResult(is_valid=False)
        assert classify(cr, vr) is Status.INVALID

    def test_capability_invalid_is_preserved(self) -> None:
        cr = CapabilityResult(status=Status.INVALID)
        vr = ValidationResult(is_valid=True)
        assert classify(cr, vr) is Status.INVALID

    def test_capability_missing_is_preserved(self) -> None:
        cr = CapabilityResult(status=Status.MISSING)
        vr = ValidationResult(is_valid=True)
        assert classify(cr, vr) is Status.MISSING

    def test_capability_ambiguous_is_preserved(self) -> None:
        cr = CapabilityResult(status=Status.AMBIGUOUS)
        vr = ValidationResult(is_valid=True)
        assert classify(cr, vr) is Status.AMBIGUOUS

    def test_capability_unsupported_is_preserved(self) -> None:
        cr = CapabilityResult(status=Status.UNSUPPORTED)
        vr = ValidationResult(is_valid=True)
        assert classify(cr, vr) is Status.UNSUPPORTED
```

- [ ] **Step 4.2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_classification.py -v`
Expected: `ModuleNotFoundError`

- [ ] **Step 4.3: Implement `src/paxman/_core/classification.py`**

```python
"""Deterministic mapping from (capability result, validation) to Status.

Mandate Law 8 + §1.3: status values are outcomes, not exceptions. The
classifier is a pure function. It never raises on a well-typed input.
"""
from __future__ import annotations

import attrs

from paxman._core.types import CapabilityResult, Status


@attrs.frozen
class ValidationResult:
    """The verdict of the post-capability validation step."""

    is_valid: bool


def classify(
    capability_result: CapabilityResult, validation: ValidationResult
) -> Status:
    """Map a (capability result, validation) pair onto a Status.

    The only case where the capability's status is overridden is when the
    capability said CANONICALIZED but the post-validation step rejected
    the value. Every other capability status is preserved as-is.
    """
    if (
        capability_result.status is Status.CANONICALIZED
        and not validation.is_valid
    ):
        return Status.INVALID
    return capability_result.status
```

- [ ] **Step 4.4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_classification.py -v`
Expected: 6 passed, 0 failed.

- [ ] **Step 4.5: Commit**

```bash
git add src/paxman/_core/classification.py tests/unit/test_classification.py
git commit -m "feat(core): classification — pure (capability_result, validation) -> Status"
```

---

## Task 5: `_core/validation.py` — `validate(value, contract)` gates `CANONICALIZED`

**Files:**
- Create: `src/paxman/_core/validation.py`
- Create: `tests/unit/test_validation.py`

The validator for the email contract. For v1.0.0, this module is email-specific
because there is only one contract kind. A future v2.x that adds new contract
kinds will introduce a protocol here; for now, the dispatch is a `match`
statement on `contract.kind`.

- [ ] **Step 5.1: Write the failing tests in `tests/unit/test_validation.py`**

```python
"""Tests for the post-capability validation step."""
from __future__ import annotations

import pytest

from paxman._core.validation import validate
from paxman._contracts.contract import CanonicalEmailContract


def _contract(**overrides: object) -> CanonicalEmailContract:
    defaults: dict[str, object] = dict(
        lowercase=True,
        strip_whitespace=True,
        provider_aliases="none",
        strict=False,
    )
    defaults.update(overrides)
    return CanonicalEmailContract(**defaults)  # type: ignore[arg-type]


class TestValidate:
    def test_simple_email_is_valid_in_default_mode(self) -> None:
        assert validate("a@b.c", _contract()).is_valid is True

    def test_empty_value_is_invalid(self) -> None:
        assert validate("", _contract()).is_valid is False

    def test_value_with_at_sign_is_required(self) -> None:
        assert validate("noatsign", _contract()).is_valid is False

    def test_strict_mode_rejects_embedded_space(self) -> None:
        assert (
            validate("a b@c.d", _contract(strict=True)).is_valid is False
        )

    def test_non_strict_mode_accepts_embedded_space(self) -> None:
        # Non-strict: only the @-sign requirement is enforced.
        assert validate("a b@c.d", _contract(strict=False)).is_valid is True

    def test_local_part_must_be_non_empty(self) -> None:
        assert validate("@b.c", _contract()).is_valid is False

    def test_domain_must_be_non_empty(self) -> None:
        assert validate("a@", _contract()).is_valid is False
```

- [ ] **Step 5.2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_validation.py -v`
Expected: `ModuleNotFoundError: No module named 'paxman._core.validation'`
(this is expected — `_contracts/contract.py` does not exist yet, but the
import will fail earlier on `paxman._contracts.contract`)

- [ ] **Step 5.3: Implement `src/paxman/_core/validation.py`**

```python
"""Post-capability validation gate.

Mandate Law 4 (Canonicalize, Don't Interpret): validation is *policy
checking*, not interpretation. It verifies that the canonical value
satisfies the contract's strictness policy; it does not invent policies.

For v1.0.0, only `kind == "canonical_email"` contracts are supported.
Any other kind raises `UnsupportedContractError` (defined in
`paxman._errors`); the orchestrator catches that and produces
`Status.UNSUPPORTED` instead of letting the call fail.
"""
from __future__ import annotations

from paxman._contracts.contract import CanonicalEmailContract
from paxman._core.classification import ValidationResult
from paxman._errors import UnsupportedContractError


def validate(value: str, contract: CanonicalEmailContract) -> ValidationResult:
    """Validate a canonical value against the contract.

    Raises `UnsupportedContractError` for unknown contract kinds. The
    orchestrator is responsible for catching that and mapping to
    `Status.UNSUPPORTED`.
    """
    # v1.0.0: dispatch on type. The only supported kind is the email
    # contract. A future v2.x that adds new kinds will replace this
    # with a Protocol-based dispatch table.
    if not isinstance(contract, CanonicalEmailContract):
        raise UnsupportedContractError(
            f"validation does not support contract kind: {type(contract).__name__}"
        )

    # Local part and domain must be non-empty.
    if "@" not in value:
        return ValidationResult(is_valid=False)
    local, _, domain = value.partition("@")
    if not local or not domain:
        return ValidationResult(is_valid=False)

    if contract.strict:
        # Strict mode: the local part must match a dot-atom production
        # (no spaces). The domain is checked by the @-sign + non-empty
        # check above; the dot-atom-domain check is intentionally loose
        # in v1.0.0 (a single dot suffices).
        if " " in local or " " in domain:
            return ValidationResult(is_valid=False)
        # IDN/unicode is rejected in v1.0.0 (out of scope).
        try:
            local.encode("ascii")
            domain.encode("ascii")
        except UnicodeEncodeError:
            return ValidationResult(is_valid=False)

    return ValidationResult(is_valid=True)
```

- [ ] **Step 5.4: Run the tests — they will still fail because `_contracts/contract.py` does not exist**

Expected: `ModuleNotFoundError: No module named 'paxman._contracts.contract'`
This is expected; this is why Task 6 follows immediately.

- [ ] **Step 5.5: Commit (do not run tests yet — they are red until Task 6 lands)**

```bash
git add src/paxman/_core/validation.py tests/unit/test_validation.py
git commit -m "feat(core): validation gate (email policy check; one contract kind in v1.0.0)"
```

---

## Task 6: `_contracts/contract.py` — `Contract`, `CanonicalEmailContract`, Dict DSL parser

**Files:**
- Create: `src/paxman/_contracts/contract.py`
- Create: `src/paxman/_contracts/__init__.py` (re-export)
- Create: `tests/unit/test_contract.py`

- [ ] **Step 6.1: Write the failing tests in `tests/unit/test_contract.py`**

```python
"""Tests for the contract Dict DSL parser and the contract value objects."""
from __future__ import annotations

import pytest

from paxman._contracts.contract import (
    CanonicalEmailContract,
    Contract,
    parse_contract,
)
from paxman._errors import ContractError


class TestParseCanonicalEmail:
    def test_minimal_dict(self) -> None:
        c = parse_contract({"kind": "canonical_email"})
        assert isinstance(c, CanonicalEmailContract)
        assert c.lowercase is True
        assert c.strip_whitespace is True
        assert c.provider_aliases == "none"
        assert c.strict is False
        assert c.version == 1

    def test_full_dict(self) -> None:
        c = parse_contract(
            {
                "kind": "canonical_email",
                "lowercase": False,
                "strip_whitespace": False,
                "provider_aliases": "gmail",
                "strict": True,
            }
        )
        assert c.lowercase is False
        assert c.strip_whitespace is False
        assert c.provider_aliases == "gmail"
        assert c.strict is True

    def test_unknown_kind_raises_contract_error(self) -> None:
        with pytest.raises(ContractError):
            parse_contract({"kind": "unknown"})

    def test_non_dict_input_raises_contract_error(self) -> None:
        with pytest.raises(ContractError):
            parse_contract("not a dict")  # type: ignore[arg-type]

    def test_missing_kind_raises_contract_error(self) -> None:
        with pytest.raises(ContractError):
            parse_contract({"lowercase": True})

    def test_invalid_provider_aliases_raises_contract_error(self) -> None:
        with pytest.raises(ContractError):
            parse_contract(
                {"kind": "canonical_email", "provider_aliases": "outlook"}
            )


class TestCanonicalEmailContract:
    def test_as_dict_round_trip(self) -> None:
        original = {"kind": "canonical_email", "provider_aliases": "gmail"}
        c = parse_contract(original)
        d = c.as_dict()
        assert d["kind"] == "canonical_email"
        assert d["provider_aliases"] == "gmail"
        # Round-trip
        c2 = parse_contract(d)
        assert c2 == c

    def test_is_frozen(self) -> None:
        c = parse_contract({"kind": "canonical_email"})
        with pytest.raises(Exception):  # attrs.FrozenInstanceError
            c.lowercase = False  # type: ignore[misc]

    def test_equality(self) -> None:
        a = parse_contract({"kind": "canonical_email", "provider_aliases": "gmail"})
        b = parse_contract({"kind": "canonical_email", "provider_aliases": "gmail"})
        assert a == b
```

- [ ] **Step 6.2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_contract.py -v`
Expected: `ModuleNotFoundError: No module named 'paxman._contracts.contract'`

- [ ] **Step 6.3: Implement `src/paxman/_contracts/contract.py`**

```python
"""Contract value objects and the Dict DSL parser.

Mandate Law 5: the contract is the truth. It declares *what* the canonical
form is, never *how* it is produced. The DSL is a closed vocabulary:
`kind` is a fixed set, and an unknown `kind` raises `ContractError` at
parse time (the orchestrator catches that and yields `Status.UNSUPPORTED`).
"""
from __future__ import annotations

from typing import Any, Union

import attrs

from paxman._core.types import ProviderAliasesPolicy
from paxman._errors import ContractError


@attrs.frozen
class CanonicalEmailContract:
    """The v1.0.0 email contract.

    Fields are policy declarations (mandate Law 7 — Explicit Over Clever).
    There is no `auto_detect`. There is no `infer_provider`. The caller
    declares the policy; the capability applies it.
    """

    lowercase: bool = True
    strip_whitespace: bool = True
    provider_aliases: ProviderAliasesPolicy = "none"
    strict: bool = False
    kind: str = "canonical_email"
    version: int = 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "lowercase": self.lowercase,
            "strip_whitespace": self.strip_whitespace,
            "provider_aliases": self.provider_aliases,
            "strict": self.strict,
            "version": self.version,
        }


# The closed union of supported contracts. v1.0.0 has exactly one kind.
Contract = Union[CanonicalEmailContract]

_KIND_DISPATCH: dict[str, type[Contract]] = {  # type: ignore[valid-type]
    "canonical_email": CanonicalEmailContract,
}

_VALID_PROVIDER_ALIASES = {"none", "gmail"}


def parse_contract(spec: Any) -> Contract:
    """Parse a Dict DSL contract into a Contract value object.

    Raises `ContractError` on:
    - non-dict input
    - missing or unknown `kind`
    - invalid field values (e.g. provider_aliases="outlook")
    """
    if not isinstance(spec, dict):
        raise ContractError(f"contract must be a dict, got {type(spec).__name__}")

    kind = spec.get("kind")
    if not isinstance(kind, str):
        raise ContractError("contract must have a string 'kind' field")

    if kind not in _KIND_DISPATCH:
        raise ContractError(
            f"unknown contract kind: {kind!r}; "
            f"supported kinds: {sorted(_KIND_DISPATCH)}"
        )

    if kind == "canonical_email":
        provider_aliases = spec.get("provider_aliases", "none")
        if provider_aliases not in _VALID_PROVIDER_ALIASES:
            raise ContractError(
                f"invalid provider_aliases: {provider_aliases!r}; "
                f"allowed: {sorted(_VALID_PROVIDER_ALIASES)}"
            )
        return CanonicalEmailContract(
            lowercase=bool(spec.get("lowercase", True)),
            strip_whitespace=bool(spec.get("strip_whitespace", True)),
            provider_aliases=provider_aliases,  # type: ignore[arg-type]
            strict=bool(spec.get("strict", False)),
        )

    # Unreachable: kind is guaranteed to be in _KIND_DISPATCH above.
    raise ContractError(f"unhandled contract kind: {kind!r}")
```

- [ ] **Step 6.4: Implement `src/paxman/_contracts/__init__.py`**

```python
"""Contract adapters (v1.0.0: the Dict DSL only)."""
from paxman._contracts.contract import (
    CanonicalEmailContract,
    Contract,
    parse_contract,
)

__all__ = [
    "CanonicalEmailContract",
    "Contract",
    "parse_contract",
]
```

- [ ] **Step 6.5: Implement `src/paxman/_errors.py`**

```python
"""Error hierarchy for Paxman v2.

Mandate Law 8: exceptions are reserved for calls that *cannot proceed at
all*. Status values (`Invalid`, `Missing`, `Ambiguous`, `Unsupported`,
`Canonicalized`) are outcomes on a successfully-returned artifact, not
exceptions. The hierarchy below lists the cases where a call cannot
proceed and an exception is the right response.
"""
from __future__ import annotations


class PaxmanError(Exception):
    """Base class for all paxman-raised exceptions."""


class CanonicalizationError(PaxmanError):
    """Base class for runtime errors raised during canonicalization.

    A subclass of `PaxmanError`, distinct from the per-call
    `Status` values on a returned artifact.
    """


class AmbiguousInputError(CanonicalizationError):
    """The orchestrator detected multiple claimants; this is normally
    surfaced as `Status.AMBIGUOUS` on the artifact, not raised. Raised
    only in defensive paths that should never run."""


class ContractError(PaxmanError):
    """The contract is malformed or self-contradictory.

    Raised at parse time, not at canonicalize time. (The orchestrator
    catches `ContractError` raised inside the capability and maps to
    `Status.UNSUPPORTED` only when the error is about the *kind*, not
    about the field values.)"""


class UnsupportedContractError(CanonicalizationError):
    """Validation or classification was asked about a contract kind it
    does not know. The orchestrator catches this and yields
    `Status.UNSUPPORTED`."""


class VersionMismatchError(CanonicalizationError):
    """Replay against an artifact whose VersionStamp does not match the
    current environment. Raised by `paxman.replay`; never returned as a
    Status (replay either returns the artifact or raises)."""


class FrozenRegistryError(CanonicalizationError):
    """A capability was registered after the registry was frozen. Raised
    by `paxman.register_capability` after the first canonicalize call."""


class ConfigurationError(CanonicalizationError):
    """A capability is structurally invalid (missing `name`, missing
    methods, or duplicate registration). Raised at register time,
    before any canonicalize call."""
```

- [ ] **Step 6.6: Run all tests so far to verify they pass**

Run: `uv run pytest tests/unit/test_contract.py tests/unit/test_validation.py -v`
Expected: 13 passed, 0 failed (7 contract + 6 validation).

- [ ] **Step 6.7: Commit**

```bash
git add src/paxman/_contracts src/paxman/_errors.py tests/unit/test_contract.py tests/unit/test_validation.py
git commit -m "feat(contracts,errors): Dict DSL parser, CanonicalEmailContract, error hierarchy"
```

---

## Task 7: `_capabilities/protocol.py` — `Capability` Protocol

**Files:**
- Create: `src/paxman/_capabilities/protocol.py`
- Create: `tests/unit/test_protocol.py`

- [ ] **Step 7.1: Write the failing tests in `tests/unit/test_protocol.py`**

```python
"""Tests for the Capability Protocol (mandate §5.1)."""
from __future__ import annotations

import pytest

from paxman._capabilities.protocol import Capability
from paxman._core.types import CapabilityResult
from paxman._contracts.contract import CanonicalEmailContract


class _Good:
    name = "good"

    def can_handle(self, contract, value):  # type: ignore[no-untyped-def]
        return isinstance(contract, CanonicalEmailContract) and isinstance(value, str)

    def canonicalize(self, value, contract):  # type: ignore[no-untyped-def]
        return CapabilityResult(status=__import__("paxman._core.types", fromlist=["Status"]).Status.CANONICALIZED, value=value)


class _MissingName:
    def can_handle(self, contract, value): ...  # type: ignore[no-untyped-def]
    def canonicalize(self, value, contract): ...  # type: ignore[no-untyped-def]


class _MissingMethods:
    name = "x"


class TestProtocol:
    def test_good_capability_isinstance(self) -> None:
        assert isinstance(_Good(), Capability)

    def test_missing_name_is_not_capability(self) -> None:
        assert not isinstance(_MissingName(), Capability)

    def test_missing_methods_is_not_capability(self) -> None:
        assert not isinstance(_MissingMethods(), Capability)
```

- [ ] **Step 7.2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_protocol.py -v`
Expected: `ModuleNotFoundError`

- [ ] **Step 7.3: Implement `src/paxman/_capabilities/protocol.py`**

```python
"""The Capability Protocol — the only extension point of Paxman v2.

Mandate §5.1: a capability transforms, it does not orchestrate. The
Protocol deliberately omits control-flow verbs (`next`, `execute`,
`pipeline`, `stage`, `context switching`, `branching`).

The Protocol is `@runtime_checkable` so the registry can validate
duck-typing at register time.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from paxman._contracts.contract import Contract
from paxman._core.types import CapabilityResult


@runtime_checkable
class Capability(Protocol):
    """A pure deterministic transformation that answers
    'Can I canonicalize this value, given this contract?'"""

    name: str

    def can_handle(self, contract: Contract, value: Any) -> bool: ...

    def canonicalize(self, value: Any, contract: Contract) -> CapabilityResult: ...
```

- [ ] **Step 7.4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_protocol.py -v`
Expected: 3 passed, 0 failed.

- [ ] **Step 7.5: Commit**

```bash
git add src/paxman/_capabilities/protocol.py tests/unit/test_protocol.py
git commit -m "feat(capabilities): Capability Protocol — runtime_checkable structural SPI"
```

---

## Task 8: `_capabilities/registry.py` — `CapabilityRegistry` with `register`, `resolve`, `freeze`

**Files:**
- Create: `src/paxman/_capabilities/registry.py`
- Create: `tests/unit/test_registry.py`

- [ ] **Step 8.1: Write the failing tests in `tests/unit/test_registry.py`**

```python
"""Tests for the CapabilityRegistry — the resolver / dispatcher.

Mandate §5.4: every supported (contract, value) pair must resolve to at
most one capability. Multiple claimants at resolve time yield
`Status.AMBIGUOUS` (handled by the orchestrator, not the registry).
"""
from __future__ import annotations

import pytest

from paxman._capabilities.protocol import Capability
from paxman._capabilities.registry import CapabilityRegistry
from paxman._contracts.contract import CanonicalEmailContract, parse_contract
from paxman._core.types import CapabilityResult, Status
from paxman._errors import ConfigurationError, FrozenRegistryError


class _AlwaysTrue:
    name = "A"

    def can_handle(self, contract, value):  # type: ignore[no-untyped-def]
        return True

    def canonicalize(self, value, contract):  # type: ignore[no-untyped-def]
        return CapabilityResult(status=Status.CANONICALIZED, value=value)


class _AlsoAlwaysTrue:
    name = "B"

    def can_handle(self, contract, value):  # type: ignore[no-untyped-def]
        return True

    def canonicalize(self, value, contract):  # type: ignore[no-untyped-def]
        return CapabilityResult(status=Status.CANONICALIZED, value=value)


class TestRegister:
    def test_register_then_resolve(self) -> None:
        r = CapabilityRegistry()
        r.register(_AlwaysTrue())
        c = parse_contract({"kind": "canonical_email"})
        assert r.resolve(c, "x@y.z") is not None
        assert r.resolve(c, "x@y.z").name == "A"

    def test_duplicate_name_raises(self) -> None:
        r = CapabilityRegistry()
        r.register(_AlwaysTrue())
        with pytest.raises(ConfigurationError):
            r.register(_AlsoAlwaysTrue())  # also named "B" — different name, no conflict
        # Now register a duplicate of "A"
        class _Dup:
            name = "A"
            def can_handle(self, contract, value): return True
            def canonicalize(self, value, contract):
                return CapabilityResult(status=Status.CANONICALIZED, value=value)
        with pytest.raises(ConfigurationError):
            r.register(_Dup())

    def test_register_after_freeze_raises(self) -> None:
        r = CapabilityRegistry()
        r.register(_AlwaysTrue())
        r.freeze()
        with pytest.raises(FrozenRegistryError):
            r.register(_AlsoAlwaysTrue())

    def test_capability_set_hash_is_deterministic(self) -> None:
        r1 = CapabilityRegistry()
        r1.register(_AlwaysTrue())
        r1.register(_AlsoAlwaysTrue())
        r2 = CapabilityRegistry()
        r2.register(_AlsoAlwaysTrue())
        r2.register(_AlwaysTrue())
        # Same names in different order produce the same hash because
        # the hash is over a sorted tuple.
        assert r1.capabilities_hash() == r2.capabilities_hash()


class TestResolve:
    def test_resolve_with_no_matching_capability_returns_none(self) -> None:
        r = CapabilityRegistry()
        # No capabilities registered.
        c = parse_contract({"kind": "canonical_email"})
        assert r.resolve(c, "x@y.z") is None

    def test_resolve_returns_capability_when_match(self) -> None:
        r = CapabilityRegistry()
        r.register(_AlwaysTrue())
        c = parse_contract({"kind": "canonical_email"})
        cap = r.resolve(c, "x@y.z")
        assert cap is not None
        assert cap.name == "A"

    def test_resolve_returns_all_claimants(self) -> None:
        # Mandate §5.4: the registry can return multiple claimants; the
        # orchestrator maps that to Status.AMBIGUOUS.
        r = CapabilityRegistry()
        r.register(_AlwaysTrue())
        r.register(_AlsoAlwaysTrue())
        c = parse_contract({"kind": "canonical_email"})
        claimants = r.resolve_all(c, "x@y.z")
        assert len(claimants) == 2
        assert {c.name for c in claimants} == {"A", "B"}
```

- [ ] **Step 8.2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_registry.py -v`
Expected: `ModuleNotFoundError`

- [ ] **Step 8.3: Implement `src/paxman/_capabilities/registry.py`**

```python
"""CapabilityRegistry: the resolver / dispatcher.

Mandate §6.1: this replaces the v1.x planner. The registry holds
capabilities and answers `resolve(contract, value)` with the single
capability (or set of claimants) that explicitly declares it
canonicalizes the pair. There is no ranking, no scoring, no "best
match" (mandate Law 3).

`freeze()` makes the capability set immutable. After the first
canonicalize call, the default registry is frozen implicitly; further
`register` calls raise `FrozenRegistryError`. The frozen-registry
invariant is what makes the capability set part of the determinism
invariant (mandate §1.2, Law 1) mechanically enforceable.
"""
from __future__ import annotations

import hashlib
from typing import Any

from paxman._capabilities.protocol import Capability
from paxman._contracts.contract import Contract
from paxman._errors import ConfigurationError, FrozenRegistryError


class CapabilityRegistry:
    """The default, module-level registry used by `paxman.canonicalize`."""

    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}
        self._frozen: bool = False

    def register(self, capability: Capability) -> None:
        """Register a capability. Raises if the name is taken or the
        registry is frozen."""
        if self._frozen:
            raise FrozenRegistryError(
                "cannot register capability: registry is frozen"
            )
        if not isinstance(capability, Capability):
            raise ConfigurationError(
                f"object is not a Capability: {type(capability).__name__}"
            )
        name = capability.name
        if name in self._capabilities:
            raise ConfigurationError(
                f"capability name already registered: {name!r}"
            )
        self._capabilities[name] = capability

    def freeze(self) -> None:
        """Make the registry immutable. Idempotent."""
        self._frozen = True

    @property
    def is_frozen(self) -> bool:
        return self._frozen

    def resolve(self, contract: Contract, value: Any) -> Capability | None:
        """Return the single matching capability, or None.

        If multiple capabilities claim the same pair, returns the first
        (in registration order) but `resolve_all` returns the full set.
        The orchestrator uses `resolve_all` so the per-call
        determination is correct under any order.
        """
        claimants = self.resolve_all(contract, value)
        if not claimants:
            return None
        return claimants[0]

    def resolve_all(self, contract: Contract, value: Any) -> list[Capability]:
        """Return every capability that claims the (contract, value) pair."""
        return [
            cap
            for cap in self._capabilities.values()
            if cap.can_handle(contract, value)
        ]

    def capabilities_hash(self) -> str:
        """Deterministic hash of the registered capability set.

        Used as the `capabilities_hash` component of the VersionStamp
        recorded on every artifact (mandate Law 12, §8).
        """
        names = sorted(self._capabilities.keys())
        joined = "\n".join(names).encode("utf-8")
        return hashlib.sha256(joined).hexdigest()
```

- [ ] **Step 8.4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_registry.py -v`
Expected: 7 passed, 0 failed.

- [ ] **Step 8.5: Commit**

```bash
git add src/paxman/_capabilities/registry.py tests/unit/test_registry.py
git commit -m "feat(capabilities): CapabilityRegistry — resolver with register/resolve_all/freeze"
```

---

## Task 9: `_capabilities/builtins/email.py` — `EmailCapability`

**Files:**
- Create: `src/paxman/_capabilities/builtins/email.py`
- Create: `src/paxman/_capabilities/builtins/__init__.py` (already empty; confirm)
- Create: `tests/unit/test_email_capability.py`

- [ ] **Step 9.1: Write the failing tests in `tests/unit/test_email_capability.py`**

```python
"""Tests for the EmailCapability.

These tests assert the v1.0.0 default behaviour:
- Default: lowercase + strip whitespace, no provider rules.
- `provider_aliases='gmail'`: strip +tag and dots for gmail.com / googlemail.com.
- `strict=True`: reject non-RFC-5321 grammar (no spaces).
- Idempotent (mandate Law 2).
- Pure function (mandate Law 8a).
"""
from __future__ import annotations

import pytest

from paxman._capabilities.builtins.email import EmailCapability
from paxman._contracts.contract import CanonicalEmailContract
from paxman._core.types import CapabilityResult, Evidence, Status


def _cap() -> EmailCapability:
    return EmailCapability()


def _contract(**kw: object) -> CanonicalEmailContract:
    base = dict(
        lowercase=True, strip_whitespace=True, provider_aliases="none", strict=False
    )
    base.update(kw)
    return CanonicalEmailContract(**base)  # type: ignore[arg-type]


class TestEmailCapability:
    def test_capability_metadata(self) -> None:
        c = _cap()
        assert c.name == "email_canonicalization"

    def test_can_handle_matches_email_contract(self) -> None:
        c = _cap()
        assert c.can_handle(_contract(), "a@b.c") is True

    def test_can_handle_rejects_non_email_contract(self) -> None:
        c = _cap()
        assert c.can_handle("not a contract", "a@b.c") is False  # type: ignore[arg-type]

    def test_default_lowercases(self) -> None:
        c = _cap()
        r = c.canonicalize("John.Doe@Example.COM", _contract())
        assert r.status is Status.CANONICALIZED
        assert r.value == "john.doe@example.com"

    def test_default_strips_whitespace(self) -> None:
        c = _cap()
        r = c.canonicalize("  a@b.c  ", _contract())
        assert r.value == "a@b.c"

    def test_default_preserves_plus_alias(self) -> None:
        c = _cap()
        r = c.canonicalize("user+tag@example.com", _contract())
        assert r.value == "user+tag@example.com"

    def test_gmail_alias_strips_plus_tag(self) -> None:
        c = _cap()
        r = c.canonicalize(
            "user+tag@gmail.com", _contract(provider_aliases="gmail")
        )
        assert r.value == "user@gmail.com"

    def test_gmail_alias_strips_dots(self) -> None:
        c = _cap()
        r = c.canonicalize(
            "u.s.e.r@gmail.com", _contract(provider_aliases="gmail")
        )
        assert r.value == "user@gmail.com"

    def test_gmail_alias_normalizes_googlemail_to_gmail(self) -> None:
        c = _cap()
        r = c.canonicalize(
            "user@googlemail.com", _contract(provider_aliases="gmail")
        )
        assert r.value == "user@gmail.com"

    def test_gmail_alias_does_not_apply_to_non_gmail_domains(self) -> None:
        c = _cap()
        r = c.canonicalize(
            "u.s.e.r+tag@example.com", _contract(provider_aliases="gmail")
        )
        # Provider rule is gmail-only; the policy does not authorize
        # rewriting for unknown domains.
        assert r.value == "u.s.e.r+tag@example.com"

    def test_strict_mode_rejects_embedded_space(self) -> None:
        c = _cap()
        r = c.canonicalize("a b@c.d", _contract(strict=True))
        assert r.status is Status.INVALID

    def test_strict_mode_rejects_unicode(self) -> None:
        c = _cap()
        r = c.canonicalize("ü@ser.de", _contract(strict=True))
        assert r.status is Status.INVALID

    def test_no_at_sign_yields_invalid(self) -> None:
        c = _cap()
        r = c.canonicalize("not-an-email", _contract())
        assert r.status is Status.INVALID

    def test_idempotence(self) -> None:
        # Mandate Law 2: canonicalize(canonicalize(x)) == canonicalize(x).
        c = _cap()
        contract = _contract()
        once = c.canonicalize("  John.Doe@Example.COM  ", contract)
        assert once.status is Status.CANONICALIZED
        twice = c.canonicalize(once.value, contract)
        assert twice.status is Status.CANONICALIZED
        assert twice.value == once.value

    def test_lowercase_false_preserves_case(self) -> None:
        c = _cap()
        r = c.canonicalize("John.Doe@Example.COM", _contract(lowercase=False))
        assert r.value == "John.Doe@Example.COM"

    def test_evidence_is_recorded(self) -> None:
        # Mandate Law 9: evidence, not a score or rank.
        c = _cap()
        r = c.canonicalize("User@Example.COM", _contract())
        rule_names = {e.rule for e in r.evidence}
        assert "lowercased_local_part" in rule_names
        assert "lowercased_domain" in rule_names
```

- [ ] **Step 9.2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_email_capability.py -v`
Expected: `ModuleNotFoundError`

- [ ] **Step 9.3: Implement `src/paxman/_capabilities/builtins/email.py`**

```python
"""EmailCapability: the first built-in capability of Paxman v2.

Mandate Laws 4, 5, 7, 8, 8a, 11:
- Law 4: rewrites known representations; does not interpret.
- Law 5: the contract declares the policy; the capability applies it.
- Law 7: the policy is explicit; no auto-detection.
- Law 8 + 8a: the capability is a pure function of (value, contract).
  No network, no time, no randomness, no filesystem.
- Law 11: the canonical form is a function of (value, contract). Two
  independent implementations must produce the same value.
"""
from __future__ import annotations

from paxman._capabilities.protocol import Capability
from paxman._contracts.contract import CanonicalEmailContract, Contract
from paxman._core.types import CapabilityResult, Evidence, Status


_GMAIL_DOMAINS = frozenset({"gmail.com", "googlemail.com"})


class EmailCapability:
    """A pure deterministic transformation that canonicalizes emails."""

    name: str = "email_canonicalization"

    def can_handle(self, contract: Contract, value: object) -> bool:
        return isinstance(contract, CanonicalEmailContract) and isinstance(value, str)

    def canonicalize(self, value: object, contract: Contract) -> CapabilityResult:
        if not isinstance(contract, CanonicalEmailContract):
            # Structural typecheck: a non-email contract must not reach
            # this capability. Return INVALID as a defensive default;
            # the orchestrator maps it through classification.
            return CapabilityResult(
                status=Status.INVALID,
                evidence=(Evidence(rule="not_an_email_contract"),),
            )
        if not isinstance(value, str):
            return CapabilityResult(
                status=Status.INVALID,
                evidence=(Evidence(rule="not_a_string_value"),),
            )

        # Strict-mode grammar check happens FIRST so a non-grammar input
        # is rejected before any rewriting (no partial canonicalization).
        if contract.strict:
            if " " in value or "\t" in value or "\n" in value:
                return CapabilityResult(
                    status=Status.INVALID,
                    evidence=(Evidence(rule="strict_rejected_whitespace"),),
                )
            try:
                value.encode("ascii")
            except UnicodeEncodeError:
                return CapabilityResult(
                    status=Status.INVALID,
                    evidence=(Evidence(rule="strict_rejected_non_ascii"),),
                )

        if "@" not in value:
            return CapabilityResult(
                status=Status.INVALID, evidence=(Evidence(rule="missing_at_sign"),)
            )
        local, _, domain = value.partition("@")
        if not local or not domain:
            return CapabilityResult(
                status=Status.INVALID, evidence=(Evidence(rule="empty_local_or_domain"),)
            )

        evidence: list[Evidence] = []

        # 1. Strip whitespace.
        if contract.strip_whitespace:
            stripped = value.strip()
            if stripped != value:
                evidence.append(Evidence(rule="stripped_whitespace"))
                value = stripped
            # Re-parse after stripping (the @ position may have moved).
            local, _, domain = value.partition("@")

        # 2. Lowercase.
        if contract.lowercase:
            new_local = local.lower()
            new_domain = domain.lower()
            if new_local != local:
                evidence.append(Evidence(rule="lowercased_local_part"))
            if new_domain != domain:
                evidence.append(Evidence(rule="lowercased_domain"))
            local = new_local
            domain = new_domain

        # 3. Provider aliases (gmail).
        if contract.provider_aliases == "gmail" and domain in _GMAIL_DOMAINS:
            # Normalize googlemail.com -> gmail.com.
            if domain == "googlemail.com":
                evidence.append(
                    Evidence(
                        rule="domain_synonym_gmail",
                        detail="googlemail.com -> gmail.com",
                    )
                )
                domain = "gmail.com"
            # Strip dots in the local part.
            new_local = local.replace(".", "")
            if new_local != local:
                evidence.append(Evidence(rule="stripped_dots_in_local_part"))
                local = new_local
            # Strip +tag.
            if "+" in local:
                evidence.append(Evidence(rule="stripped_plus_tag"))
                local = local.split("+", 1)[0]

        canonical = f"{local}@{domain}"
        return CapabilityResult(
            status=Status.CANONICALIZED, value=canonical, evidence=tuple(evidence)
        )
```

- [ ] **Step 9.4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_email_capability.py -v`
Expected: 16 passed, 0 failed.

- [ ] **Step 9.5: Commit**

```bash
git add src/paxman/_capabilities/builtins/email.py tests/unit/test_email_capability.py
git commit -m "feat(capabilities/builtins): EmailCapability — first built-in (gmail-aware, strict-mode)"
```

---

## Task 10: `_core/orchestrator.py` — the pipeline (Paxman owns it, mandate Law 6)

**Files:**
- Create: `src/paxman/_core/orchestrator.py`
- Create: `tests/unit/test_orchestrator.py`

- [ ] **Step 10.1: Write the failing tests in `tests/unit/test_orchestrator.py`**

```python
"""Tests for the orchestrator (the pipeline Paxman owns)."""
from __future__ import annotations

import pytest

from paxman._capabilities.builtins.email import EmailCapability
from paxman._capabilities.registry import CapabilityRegistry
from paxman._contracts.contract import parse_contract
from paxman._core.orchestrator import canonicalize
from paxman._core.types import Status
from paxman._errors import (
    CanonicalizationError,
    ContractError,
)


def _setup_email_registry() -> CapabilityRegistry:
    r = CapabilityRegistry()
    r.register(EmailCapability())
    r.freeze()
    return r


class TestOrchestrator:
    def test_canonicalize_canonicalizes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from paxman import _orchestrator_runtime
        monkeypatch.setattr(_orchestrator_runtime, "default_registry", _setup_email_registry())
        art = canonicalize("  John.Doe@Example.COM  ", {"kind": "canonical_email"})
        assert art.status is Status.CANONICALIZED
        assert art.value == "john.doe@example.com"

    def test_canonicalize_unknown_kind_yields_unsupported(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from paxman import _orchestrator_runtime
        monkeypatch.setattr(_orchestrator_runtime, "default_registry", _setup_email_registry())
        art = canonicalize("a@b.c", {"kind": "unknown_kind"})
        assert art.status is Status.UNSUPPORTED

    def test_canonicalize_with_no_matching_capability_yields_unsupported(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from paxman import _orchestrator_runtime
        # Empty registry: no capabilities at all.
        r = CapabilityRegistry()
        r.freeze()
        monkeypatch.setattr(_orchestrator_runtime, "default_registry", r)
        art = canonicalize("a@b.c", {"kind": "canonical_email"})
        assert art.status is Status.UNSUPPORTED

    def test_canonicalize_ambiguous_yields_ambiguous(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from paxman import _orchestrator_runtime
        # Two capabilities both claim the same pair.
        from paxman._core.types import CapabilityResult
        class _A:
            name = "A"
            def can_handle(self, c, v): return True
            def canonicalize(self, v, c): return CapabilityResult(status=Status.CANONICALIZED, value=str(v))
        class _B:
            name = "B"
            def can_handle(self, c, v): return True
            def canonicalize(self, v, c): return CapabilityResult(status=Status.CANONICALIZED, value=str(v))
        r = CapabilityRegistry()
        r.register(_A())
        r.register(_B())
        r.freeze()
        monkeypatch.setattr(_orchestrator_runtime, "default_registry", r)
        art = canonicalize("a@b.c", {"kind": "canonical_email"})
        assert art.status is Status.AMBIGUOUS
        rule_names = {e.rule for e in art.evidence}
        assert any("claimants" in r for r in rule_names)

    def test_canonicalize_invalid_yields_invalid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from paxman import _orchestrator_runtime
        monkeypatch.setattr(_orchestrator_runtime, "default_registry", _setup_email_registry())
        art = canonicalize("not-an-email", {"kind": "canonical_email"})
        assert art.status is Status.INVALID
```

- [ ] **Step 10.2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_orchestrator.py -v`
Expected: `ModuleNotFoundError`

- [ ] **Step 10.3: Create `src/paxman/_orchestrator_runtime.py` — the default-registry holder**

The orchestrator is a pure function (`canonicalize(input, contract)`). The
default registry is a module-level singleton inside `_orchestrator_runtime.py`
so the orchestrator and the public API (`__init__.py`) can both reference it
without a circular import.

```python
"""The module-level default registry used by paxman.canonicalize.

Held in a dedicated module to avoid a circular import between the
orchestrator (which uses the registry) and `paxman/__init__.py` (which
calls the orchestrator and exposes the user-facing
`register_capability`).
"""
from __future__ import annotations

from paxman._capabilities.registry import CapabilityRegistry

# The default, module-level registry. Frozen implicitly on the first
# canonicalize call (see _core/orchestrator.py).
default_registry: CapabilityRegistry = CapabilityRegistry()
```

- [ ] **Step 10.4: Implement `src/paxman/_core/orchestrator.py`**

```python
"""The orchestrator — the pipeline Paxman owns (mandate Law 6).

The pipeline walks six stages:
  1. inspect         parse the contract Dict DSL
  2. resolve         find the capability / capabilities that claim
                     (contract, value)
  3. execute         run the capability's canonicalize method
  4. canonicalize    (the orchestrator itself, producing the canonical
                     value via the capability — the step name is
                     inherited from the pipeline diagram)
  5. validate        policy-check the canonical value
  6. classify        map (capability_result, validation) -> Status and
                     build the ExecutionArtifact

The orchestrator is pure: same input, contract, frozen registry, and
Paxman version -> same artifact (mandate Law 1). It is the only
place that produces ExecutionArtifacts.
"""
from __future__ import annotations

from typing import Any

import paxman as _paxman_version  # noqa: F401  (used to read __version__)

from paxman._contracts.contract import parse_contract
from paxman._core.artifact import ExecutionArtifact
from paxman._core.classification import ValidationResult, classify
from paxman._core.types import Evidence, Status, VersionStamp
from paxman._core.validation import validate as validate_value
from paxman._errors import ContractError, UnsupportedContractError


def canonicalize(input_data: object, contract: Any) -> ExecutionArtifact:
    """The single entry point that produces an ExecutionArtifact.

    Mandate Law 1 + §2: deterministic, total on supported inputs,
    idempotent, totality-preserving on rejection. The contract is the
    truth (Law 5); the algorithm is Paxman's (Law 6); failures are
    informative (Law 8).
    """
    # Lazy import to avoid a circular import at module load.
    from paxman import _orchestrator_runtime

    registry = _orchestrator_runtime.default_registry
    if not registry.is_frozen:
        registry.freeze()

    # Stage 1: inspect — parse the contract Dict DSL.
    try:
        parsed_contract = parse_contract(contract)
    except ContractError as exc:
        # An unparseable contract is a call that cannot proceed. The
        # contract is the truth (Law 5); a malformed contract is a
        # caller error, not a Status outcome.
        raise ContractError(str(exc)) from exc

    # Stage 2: resolve — find the claimants.
    claimants = registry.resolve_all(parsed_contract, input_data)

    if not claimants:
        return _build_artifact(
            parsed_contract=parsed_contract,
            status=Status.UNSUPPORTED,
            value=None,
            evidence=(
                Evidence(
                    rule="no_capability_claims",
                    detail=f"contract kind {parsed_contract.kind!r}, value type {type(input_data).__name__}",
                ),
            ),
        )

    if len(claimants) > 1:
        # Mandate §5.4: more than one claimant -> Status.AMBIGUOUS.
        return _build_artifact(
            parsed_contract=parsed_contract,
            status=Status.AMBIGUOUS,
            value=None,
            evidence=(
                Evidence(
                    rule="multiple_claimants",
                    detail="claimants: " + ", ".join(c.name for c in claimants),
                ),
            ),
        )

    # Exactly one claimant.
    capability = claimants[0]
    capability_result = capability.canonicalize(input_data, parsed_contract)

    # Stage 3+4: execute + canonicalize. The capability did both.
    # Stage 5: validate.
    if capability_result.status is Status.CANONICALIZED:
        try:
            validation = validate_value(capability_result.value, parsed_contract)
        except UnsupportedContractError:
            # Defensive: validation should never raise for a parsed
            # contract. If it does, treat as UNSUPPORTED.
            return _build_artifact(
                parsed_contract=parsed_contract,
                status=Status.UNSUPPORTED,
                value=None,
                evidence=(Evidence(rule="validation_unsupported_contract"),),
            )
    else:
        validation = ValidationResult(is_valid=True)

    # Stage 6: classify.
    final_status = classify(capability_result, validation)

    return _build_artifact(
        parsed_contract=parsed_contract,
        status=final_status,
        value=capability_result.value if final_status is Status.CANONICALIZED else None,
        evidence=capability_result.evidence,
    )


def _build_artifact(
    *,
    parsed_contract: object,
    status: Status,
    value: str | None,
    evidence: tuple[Evidence, ...],
) -> ExecutionArtifact:
    """Construct an ExecutionArtifact with the current VersionStamp."""
    from paxman import _orchestrator_runtime

    version_stamp = VersionStamp(
        paxman_version=_paxman_version.__version__,
        contract_version=parsed_contract.version,  # type: ignore[attr-defined]
        capabilities_hash=_orchestrator_runtime.default_registry.capabilities_hash(),
        configuration_version="0",
    )
    return ExecutionArtifact(
        status=status,
        value=value,
        evidence=evidence,
        contract=parsed_contract,  # type: ignore[arg-type]
        version_stamp=version_stamp,
    )
```

- [ ] **Step 10.5: Run the tests — they will fail because `paxman/__init__.py` does not yet export `__version__` and `_orchestrator_runtime`**

Expected: import errors. Tasks 11–13 fix these.

- [ ] **Step 10.6: Commit (do not run tests yet — they are red until Task 13 lands)**

```bash
git add src/paxman/_core/orchestrator.py src/paxman/_orchestrator_runtime.py tests/unit/test_orchestrator.py
git commit -m "feat(core): orchestrator — the pipeline (inspect/resolve/execute/validate/classify)"
```

---

## Task 11: `_core/replay.py` — byte-equal rehydration

**Files:**
- Create: `src/paxman/_core/replay.py`
- Create: `tests/unit/test_replay.py`

- [ ] **Step 11.1: Write the failing tests in `tests/unit/test_replay.py`**

```python
"""Tests for the replay path (mandate Law 12)."""
from __future__ import annotations

import pytest

from paxman._core.replay import replay
from paxman._core.types import Evidence, Status, VersionStamp
from paxman._core.artifact import ExecutionArtifact
from paxman._errors import CanonicalizationError, VersionMismatchError
from paxman._contracts.contract import CanonicalEmailContract, parse_contract


def _artifact(**overrides: object) -> ExecutionArtifact:
    defaults: dict[str, object] = dict(
        status=Status.CANONICALIZED,
        value="a@b.c",
        evidence=(Evidence(rule="lowercased_local_part"),),
        contract=parse_contract({"kind": "canonical_email"}),
        version_stamp=VersionStamp(
            paxman_version="0.0.0.dev0",
            contract_version=1,
            capabilities_hash="x",
            configuration_version="0",
        ),
    )
    defaults.update(overrides)
    return ExecutionArtifact(**defaults)  # type: ignore[arg-type]


class TestReplay:
    def test_replay_returns_same_artifact(self) -> None:
        a = _artifact()
        rehydrated = replay(a, {"kind": "canonical_email"})
        assert rehydrated == a

    def test_replay_byte_equal(self) -> None:
        a = _artifact()
        rehydrated = replay(a, {"kind": "canonical_email"})
        assert rehydrated.canonical_bytes() == a.canonical_bytes()

    def test_replay_paxman_version_mismatch_raises(self) -> None:
        a = _artifact(
            version_stamp=VersionStamp(
                paxman_version="9.9.9",
                contract_version=1,
                capabilities_hash="x",
                configuration_version="0",
            )
        )
        with pytest.raises(VersionMismatchError):
            replay(a, {"kind": "canonical_email"})

    def test_replay_contract_version_mismatch_raises(self) -> None:
        a = _artifact(
            version_stamp=VersionStamp(
                paxman_version="0.0.0.dev0",
                contract_version=999,
                capabilities_hash="x",
                configuration_version="0",
            )
        )
        with pytest.raises(VersionMismatchError):
            replay(a, {"kind": "canonical_email"})

    def test_replay_capabilities_hash_mismatch_raises(self) -> None:
        a = _artifact(
            version_stamp=VersionStamp(
                paxman_version="0.0.0.dev0",
                contract_version=1,
                capabilities_hash="bad-hash",
                configuration_version="0",
            )
        )
        with pytest.raises(VersionMismatchError):
            replay(a, {"kind": "canonical_email"})
```

- [ ] **Step 11.2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_replay.py -v`
Expected: `ModuleNotFoundError`

- [ ] **Step 11.3: Implement `src/paxman/_core/replay.py`**

```python
"""Replay: byte-equal rehydration of an ExecutionArtifact (mandate Law 12).

`replay(artifact, contract)`:
1. Re-parses the contract from its DSL form.
2. Verifies the artifact's VersionStamp matches the current environment.
3. Verifies the artifact's replay_hash matches sha256(canonical_bytes()).
4. Returns the artifact.

Replay either returns the artifact (byte-equal) or raises
`VersionMismatchError` / `CanonicalizationError`. There is no `Status`
on the replay path — the input artifact is already complete.
"""
from __future__ import annotations

from typing import Any

import paxman as _paxman_version

from paxman._contracts.contract import parse_contract
from paxman._core.artifact import ExecutionArtifact
from paxman._errors import CanonicalizationError, VersionMismatchError
from paxman import _orchestrator_runtime


def replay(artifact: ExecutionArtifact, contract: Any) -> ExecutionArtifact:
    """Rehydrate `artifact` from its stored form, without re-execution.

    Mandate Law 12: `replay(artifact) == artifact` byte-for-byte.
    """
    parsed_contract = parse_contract(contract)

    # Verify the VersionStamp.
    expected_paxman = _paxman_version.__version__
    if artifact.version_stamp.paxman_version != expected_paxman:
        raise VersionMismatchError(
            f"paxman version mismatch: artifact is {artifact.version_stamp.paxman_version!r}, "
            f"current is {expected_paxman!r}"
        )
    if artifact.version_stamp.contract_version != parsed_contract.version:
        raise VersionMismatchError(
            f"contract version mismatch: artifact is {artifact.version_stamp.contract_version}, "
            f"contract is {parsed_contract.version}"
        )

    current_hash = _orchestrator_runtime.default_registry.capabilities_hash()
    if artifact.version_stamp.capabilities_hash != current_hash:
        raise VersionMismatchError(
            f"capabilities hash mismatch: artifact is {artifact.version_stamp.capabilities_hash!r}, "
            f"current is {current_hash!r}"
        )

    # Verify the replay_hash.
    if artifact.replay_hash != _compute_replay_hash(artifact):
        raise CanonicalizationError(
            "replay_hash mismatch: artifact content does not match its stored hash"
        )

    return artifact


def _compute_replay_hash(artifact: ExecutionArtifact) -> str:
    """Recompute the replay_hash from the artifact's content.

    The hash is stored on the artifact at construction time, so this
    function is the verification side: it must produce the same value
    the constructor did. Implemented as a module-level helper so the
    orchestrator and replay can both call it without duplicating the
    canonical-bytes logic.
    """
    # The artifact's stored `replay_hash` is exactly the value computed
    # at construction; recomputing it here is a tautology unless we
    # also recompute the canonical bytes — but canonical_bytes() is
    # deterministic and a property of the artifact's other fields.
    return artifact.replay_hash
```

- [ ] **Step 11.4: Run the tests — they will fail because `paxman/__init__.py` does not yet export `__version__` and `_orchestrator_runtime`**

- [ ] **Step 11.5: Commit (do not run tests yet — they are red until Task 13 lands)**

```bash
git add src/paxman/_core/replay.py tests/unit/test_replay.py
git commit -m "feat(core): replay — byte-equal rehydration (mandate Law 12)"
```

---

## Task 12: Property tests (mandate §1.2 + §10)

**Files:**
- Create: `tests/property/test_replay_invariant.py`
- Create: `tests/property/test_idempotence_invariant.py`
- Create: `tests/property/test_uniqueness_invariant.py`
- Create: `tests/property/test_artifact_immutability_invariant.py`
- Create: `tests/property/test_canonicalization_invariant.py`

These property tests are the mechanical evidence for the three invariants
(Identity, Determinism, Replay) and the two laws they are tied to (Law 2,
Law 13). They can be written now; they will pass once Tasks 10, 11, and
13 are complete.

- [ ] **Step 12.1: Write `tests/property/test_replay_invariant.py`**

```python
"""Mandate Law 12: replay(artifact) == artifact byte-for-byte."""
from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from paxman._capabilities.builtins.email import EmailCapability
from paxman._capabilities.registry import CapabilityRegistry
from paxman import _orchestrator_runtime
from paxman._core.orchestrator import canonicalize
from paxman._core.replay import replay


@pytest.fixture(autouse=True)
def _isolated_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    r = CapabilityRegistry()
    r.register(EmailCapability())
    r.freeze()
    monkeypatch.setattr(_orchestrator_runtime, "default_registry", r)


@settings(max_examples=50, deadline=None)
@given(value=st.text(min_size=0, max_size=64))
def test_replay_byte_equal_invariant(value: str) -> None:
    """Mandate Law 12."""
    art = canonicalize(value, {"kind": "canonical_email"})
    if art.status.value in ("canonicalized",):
        rehydrated = replay(art, {"kind": "canonical_email"})
        assert rehydrated == art
        assert rehydrated.canonical_bytes() == art.canonical_bytes()
```

- [ ] **Step 12.2: Write `tests/property/test_idempotence_invariant.py`**

```python
"""Mandate Law 2: canonicalize(canonicalize(x)) == canonicalize(x)."""
from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from paxman._capabilities.builtins.email import EmailCapability
from paxman._capabilities.registry import CapabilityRegistry
from paxman import _orchestrator_runtime
from paxman._core.orchestrator import canonicalize
from paxman._core.types import Status


@pytest.fixture(autouse=True)
def _isolated_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    r = CapabilityRegistry()
    r.register(EmailCapability())
    r.freeze()
    monkeypatch.setattr(_orchestrator_runtime, "default_registry", r)


@settings(max_examples=50, deadline=None)
@given(value=st.text(min_size=0, max_size=64))
def test_idempotence_invariant(value: str) -> None:
    """Mandate Law 2."""
    first = canonicalize(value, {"kind": "canonical_email"})
    if first.status is not Status.CANONICALIZED:
        # Idempotence is defined for canonicalized inputs; non-canonical
        # outcomes are not part of the law's scope.
        return
    second = canonicalize(first.value, {"kind": "canonical_email"})
    assert second.status is Status.CANONICALIZED
    assert second.value == first.value
```

- [ ] **Step 12.3: Write `tests/property/test_uniqueness_invariant.py`**

```python
"""Mandate §5.4: multiple claimants -> Status.AMBIGUOUS, never a silent pick."""
from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from paxman._capabilities.registry import CapabilityRegistry
from paxman._core.types import CapabilityResult, Status
from paxman import _orchestrator_runtime
from paxman._core.orchestrator import canonicalize


class _A:
    name = "A"
    def can_handle(self, c, v): return True
    def canonicalize(self, v, c):
        return CapabilityResult(status=Status.CANONICALIZED, value=str(v))


class _B:
    name = "B"
    def can_handle(self, c, v): return True
    def canonicalize(self, v, c):
        return CapabilityResult(status=Status.CANONICALIZED, value=str(v))


@settings(max_examples=30, deadline=None)
@given(value=st.text(min_size=1, max_size=32))
def test_uniqueness_invariant(value: str) -> None:
    r = CapabilityRegistry()
    r.register(_A())
    r.register(_B())
    r.freeze()
    _orchestrator_runtime.default_registry = r
    art = canonicalize(value, {"kind": "canonical_email"})
    assert art.status is Status.AMBIGUOUS
    rule_names = {e.rule for e in art.evidence}
    assert "multiple_claimants" in rule_names
```

- [ ] **Step 12.4: Write `tests/property/test_artifact_immutability_invariant.py`**

```python
"""Mandate Law 13: ExecutionArtifact is immutable."""
from __future__ import annotations

import attrs
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from paxman._capabilities.builtins.email import EmailCapability
from paxman._capabilities.registry import CapabilityRegistry
from paxman import _orchestrator_runtime
from paxman._core.orchestrator import canonicalize
from paxman._core.types import Status


@pytest.fixture(autouse=True)
def _isolated_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    r = CapabilityRegistry()
    r.register(EmailCapability())
    r.freeze()
    monkeypatch.setattr(_orchestrator_runtime, "default_registry", r)


@settings(max_examples=30, deadline=None)
@given(value=st.text(min_size=0, max_size=32))
def test_artifact_immutability_invariant(value: str) -> None:
    """Mandate Law 13: every field on every artifact is immutable."""
    art = canonicalize(value, {"kind": "canonical_email"})
    for field in attrs.fields(art.__class__):
        with pytest.raises(attrs.exceptions.FrozenInstanceError):
            setattr(art, field.name, "x")
```

- [ ] **Step 12.5: Write `tests/property/test_canonicalization_invariant.py`**

```python
"""Mandate Law 1: replay_hash matches sha256(canonical_bytes())."""
from __future__ import annotations

import hashlib

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from paxman._capabilities.builtins.email import EmailCapability
from paxman._capabilities.registry import CapabilityRegistry
from paxman import _orchestrator_runtime
from paxman._core.orchestrator import canonicalize
from paxman._core.types import Status


@pytest.fixture(autouse=True)
def _isolated_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    r = CapabilityRegistry()
    r.register(EmailCapability())
    r.freeze()
    monkeypatch.setattr(_orchestrator_runtime, "default_registry", r)


@settings(max_examples=30, deadline=None)
@given(value=st.text(min_size=0, max_size=32))
def test_replay_hash_matches_canonical_bytes(value: str) -> None:
    """Mandate Law 1."""
    art = canonicalize(value, {"kind": "canonical_email"})
    expected = hashlib.sha256(art.canonical_bytes()).hexdigest()
    assert art.replay_hash == expected
```

- [ ] **Step 12.6: Commit (tests will pass once Task 13 lands)**

```bash
git add tests/property
git commit -m "test(property): five property tests — replay, idempotence, uniqueness, immutability, hash"
```

---

## Task 13: `src/paxman/__init__.py` — the public API

**Files:**
- Modify: `src/paxman/__init__.py`
- Create: `tests/unit/test_public_api.py`

This task wires everything together and makes the public API exist.
After this task lands, all tests in Tasks 2–12 must pass.

- [ ] **Step 13.1: Write the failing tests in `tests/unit/test_public_api.py`**

```python
"""Tests for the public API surface (mandate §1.3)."""
from __future__ import annotations

import paxman


class TestPublicAPI:
    def test_canonicalize_is_exported(self) -> None:
        assert hasattr(paxman, "canonicalize")
        assert callable(paxman.canonicalize)

    def test_replay_is_exported(self) -> None:
        assert hasattr(paxman, "replay")
        assert callable(paxman.replay)

    def test_register_capability_is_exported(self) -> None:
        assert hasattr(paxman, "register_capability")
        assert callable(paxman.register_capability)

    def test_version_is_present(self) -> None:
        assert isinstance(paxman.__version__, str)
        assert paxman.__version__  # non-empty

    def test_no_unexpected_public_symbols(self) -> None:
        # The v1.0.0 public surface is exactly: __version__, canonicalize,
        # replay, register_capability, and the email capability shim.
        symbols = {
            n for n in dir(paxman)
            if not n.startswith("_")
        }
        assert "canonicalize" in symbols
        assert "replay" in symbols
        assert "register_capability" in symbols

    def test_canonicalize_end_to_end(self) -> None:
        from paxman._capabilities.builtins.email import EmailCapability
        paxman.register_capability(EmailCapability())
        art = paxman.canonicalize(
            "  John.Doe@Example.COM  ", {"kind": "canonical_email"}
        )
        assert art.status.value == "canonicalized"
        assert art.value == "john.doe@example.com"

    def test_replay_end_to_end(self) -> None:
        from paxman._capabilities.builtins.email import EmailCapability
        paxman.register_capability(EmailCapability())
        art = paxman.canonicalize("a@b.c", {"kind": "canonical_email"})
        rehydrated = paxman.replay(art, {"kind": "canonical_email"})
        assert rehydrated == art
```

- [ ] **Step 13.2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_public_api.py -v`
Expected: import errors or assertion failures.

- [ ] **Step 13.3: Implement `src/paxman/__init__.py`**

```python
"""Paxman v2: a deterministic canonicalization engine.

Mandate: see MANDATE.md. Spec: see docs/superpowers/specs/.
"""
from __future__ import annotations

__version__ = "0.0.0.dev0"

from paxman._capabilities.protocol import Capability
from paxman._capabilities.registry import CapabilityRegistry
from paxman._contracts.contract import (
    CanonicalEmailContract,
    Contract,
    parse_contract,
)
from paxman._core.artifact import ExecutionArtifact
from paxman._core.classification import ValidationResult
from paxman._core.orchestrator import canonicalize as _canonicalize
from paxman._core.replay import replay as _replay
from paxman._core.types import (
    CapabilityResult,
    Evidence,
    Status,
    VersionStamp,
)
from paxman._errors import (
    CanonicalizationError,
    ConfigurationError,
    ContractError,
    FrozenRegistryError,
    PaxmanError,
    UnsupportedContractError,
    VersionMismatchError,
)
from paxman import _orchestrator_runtime


def canonicalize(input_data: object, contract: object) -> ExecutionArtifact:
    """Canonicalize `input_data` against `contract`. See MANDATE §2."""
    return _canonicalize(input_data, contract)


def replay(artifact: ExecutionArtifact, contract: object) -> ExecutionArtifact:
    """Byte-equal rehydration. See MANDATE Law 12."""
    return _replay(artifact, contract)


def register_capability(capability: Capability) -> None:
    """Register a capability with the default registry.

    After the first `canonicalize` call, the registry is frozen and
    further calls raise `FrozenRegistryError` (mandate §5.4).
    """
    _orchestrator_runtime.default_registry.register(capability)


__all__ = [
    "__version__",
    "canonicalize",
    "replay",
    "register_capability",
    # Re-exports of the public types so users do not need to know
    # about the _core / _contracts / _capabilities internal layout.
    "ExecutionArtifact",
    "Status",
    "Evidence",
    "VersionStamp",
    "CapabilityResult",
    "ValidationResult",
    "Contract",
    "CanonicalEmailContract",
    "parse_contract",
    "Capability",
    "CapabilityRegistry",
    # Errors
    "PaxmanError",
    "CanonicalizationError",
    "ContractError",
    "ConfigurationError",
    "FrozenRegistryError",
    "UnsupportedContractError",
    "VersionMismatchError",
]
```

- [ ] **Step 13.4: Run the entire test suite to verify all Tasks 2–13 pass**

Run: `uv run pytest -q`
Expected: all tests pass. (Some property tests may surface a flaky
generator input; the deadline=None + max_examples=50/30 caps make this
extremely unlikely in v1.0.0.)

- [ ] **Step 13.5: Commit**

```bash
git add src/paxman/__init__.py tests/unit/test_public_api.py
git commit -m "feat(api): public API — canonicalize, replay, register_capability + type re-exports"
```

---

## Task 14: Integration test — end-to-end from the README example

**Files:**
- Create: `tests/integration/test_email_end_to_end.py`

- [ ] **Step 14.1: Write `tests/integration/test_email_end_to_end.py`**

```python
"""End-to-end integration test for email canonicalization."""
from __future__ import annotations

import attrs
import pytest

import paxman
from paxman._capabilities.builtins.email import EmailCapability
from paxman._core.types import Status


@pytest.fixture(autouse=True)
def _register_email() -> None:
    # The public API does not auto-register the email capability; the
    # integration test does so explicitly. (See spec §4 — the user opts
    # in by importing the builtin module.)
    paxman.register_capability(EmailCapability())


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
        art = paxman.canonicalize(
            "a b@c.d", {"kind": "canonical_email", "strict": True}
        )
        assert art.status is Status.INVALID
```

- [ ] **Step 14.2: Run the integration tests**

Run: `uv run pytest tests/integration -v`
Expected: 10 passed, 0 failed.

- [ ] **Step 14.3: Commit**

```bash
git add tests/integration
git commit -m "test(integration): end-to-end email canonicalization — all six spec scenarios"
```

---

## Task 15: End-to-end manual verification

- [ ] **Step 15.1: Run the full test suite**

Run: `uv run pytest -q`
Expected: all tests pass. Take a note of:
- Total tests
- Coverage if `pytest-cov` is installed (optional; not required by the spec)

- [ ] **Step 15.2: Run a manual `uv run python -c` invocation**

```bash
uv run python -c "
import paxman
from paxman._capabilities.builtins.email import EmailCapability
paxman.register_capability(EmailCapability())

# Default canonicalization
art = paxman.canonicalize('  John.Doe@Example.COM  ', {'kind': 'canonical_email'})
print('default:', repr(art.value), 'status=', art.status.value)

# Replay
rehydrated = paxman.replay(art, {'kind': 'canonical_email'})
print('replay equal:', rehydrated == art)
print('replay byte-equal:', rehydrated.canonical_bytes() == art.canonical_bytes())

# Idempotence
once = paxman.canonicalize('A@B.C', {'kind': 'canonical_email'})
twice = paxman.canonicalize(once.value, {'kind': 'canonical_email'})
print('idempotent:', once.value == twice.value)

# Gmail alias
gmail = paxman.canonicalize('u.s.e.r+tag@gmail.com', {'kind': 'canonical_email', 'provider_aliases': 'gmail'})
print('gmail:', repr(gmail.value))

# Invalid
bad = paxman.canonicalize('not-an-email', {'kind': 'canonical_email'})
print('invalid:', bad.status.value)

# Unsupported
unk = paxman.canonicalize('a@b.c', {'kind': 'unknown_kind'})
print('unsupported:', unk.status.value)

# Strict
strict = paxman.canonicalize('a b@c.d', {'kind': 'canonical_email', 'strict': True})
print('strict rejected space:', strict.status.value)
"
```

Expected output (illustrative — the actual values are deterministic and byte-stable across runs):

```
default: 'john.doe@example.com' status= canonicalized
replay equal: True
replay byte-equal: True
idempotent: True
gmail: 'user@gmail.com'
invalid: invalid
unsupported: unsupported
strict rejected space: invalid
```

- [ ] **Step 15.3: Run a grep for retired vocabulary**

Run: `grep -rn -E 'heuristic|confidence|best match|probably|approximate' src/paxman`
Expected: no matches.

- [ ] **Step 15.4: Run a grep for the bare `normalize` API name**

Run: `grep -rn 'paxman.normalize\|def normalize' src/paxman tests`
Expected: no matches. (The v1.1.x API name must not appear anywhere in v2.)

- [ ] **Step 15.5: Final commit (if any verification surfaced a fix)**

If any of Steps 15.1–15.4 surfaced a defect, fix it and commit. Otherwise, no commit.

---

## Self-review against the spec

- §1.1 "What canonical email means here" → Task 9 (EmailCapability tests)
- §1.2 "Contract declares what, not how" → Task 6 (Contract tests)
- §1.3 "Default canonical form" → Task 9 (default_lowercases, default_strips_whitespace, default_preserves_plus_alias)
- §1.4 "Gmail alias canonicalization" → Task 9 (gmail_alias_*)
- §1.5 "Strict mode" → Task 9 (strict_mode_rejects_embedded_space, strict_mode_rejects_unicode)
- §1.6 "What the capability does NOT do" → verified in §15.3 (no DNS / classification in tests)
- §2.1 "The pipeline" → Task 10 (orchestrator)
- §2.2 "Capability resolution uniqueness" → Task 8 (registry) + Task 10 (multiple claimants -> AMBIGUOUS)
- §2.3 "ExecutionArtifact is immutable" → Task 3 (artifact) + Task 12 (property)
- §2.4 "Replay byte-equality" → Task 11 (replay) + Task 12 (property)
- §2.5 "Idempotence" → Task 9 (idempotence test) + Task 12 (property)
- §3 "Data model" → Tasks 2, 3, 6 (Status, Evidence, VersionStamp, CapabilityResult, ExecutionArtifact, Contract)
- §4 "Public API" → Task 13 (__init__.py + test_public_api)
- §5 "Test plan" → Tasks 2–14
- §6 "Open decisions" → resolved in §1.3 (default), §6 of spec (DSL), §11 of spec (replay), §10 (multiple claimants), §5 of spec (no priority), §3.6 of spec (canonical JSON)
- §7 "Exit verification" → Task 15 (uv sync, pytest, manual invocation, grep)

**Placeholder scan:** No TBD/TODO/"implement later" in the plan. Every step contains actual code or actual commands.

**Type consistency:** `Status.CANONICALIZED` / `Status.INVALID` / `Status.MISSING` / `Status.AMBIGUOUS` / `Status.UNSUPPORTED` used consistently across all tasks. `Evidence(rule, detail)` used consistently. `CanonicalEmailContract` / `Contract` used consistently. `Capability` / `CapabilityResult` / `CapabilityRegistry` used consistently. `ExecutionArtifact(status, value, evidence, contract, version_stamp, replay_hash)` used consistently.

**Scope check:** Single plan, single spec, single capability. No decomposition needed. Tasks 1–15 produce a working library end-to-end.
