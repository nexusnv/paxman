# Email Canonicalization — First Capability of Paxman v2

**Status:** Design spec — 1 of 1 (per user direction).
**Authority:** [`MANDATE.md`](../../../MANDATE.md) is the constitutional boundary for every design decision below. Questions not answered by `MANDATE.md` are candidate drift and are not answered here.
**Date:** 2026-07-13.
**Branch:** `feat/email-canonicalization`.

---

## 0. Scope

Deliver a working Paxman v2 library, end-to-end, with email canonicalization as
its first and only capability. The exit criteria are:

1. `paxman.canonicalize(input, contract) -> ExecutionArtifact` runs and returns
   a correct canonical form for a representative set of email inputs.
2. `paxman.replay(artifact, contract) -> ExecutionArtifact` is byte-equal to
   the original artifact, without re-execution.
3. The thirteen laws in `MANDATE.md` are mechanically enforced (or
   demonstrably upheld) by the implementation.
4. Three invariants are tested as Hypothesis properties: replay byte-equality,
   idempotence, and unique-resolution-or-`Ambiguous`.

Out of scope (explicitly): ADRs, CI workflow changes, pre-commit config,
Makefile, additional capabilities, IDN/unicode email handling, DNS
deliverability checks, Pydantic/JSON Schema/OpenAPI contract adapters, any
documentation beyond this spec and the plan.

---

## 1. The email capability, by mandate

### 1.1 What "canonical email" means here (Law 4)

`MANDATE.md` §1.1 defines canonicalization as "selecting exactly one
representation from a set of semantically equivalent representations," and
Law 4 distinguishes it from interpretation. The example given — `"RM100"`
→ `"MYR 100"` — is *rewriting a known value from one form to another*. It
is not classification, scoring, or guessing.

Email canonicalization is the same kind of operation:

- `"  John.Doe@Example.COM  "` and `"john.doe@example.com"` are two
  representations of the same address. The first is rewritten to the second.
- `"john.doe+spam@gmail.com"` and `"john.doe@gmail.com"` are the *same
  inbox* under Gmail's well-documented plus-alias and dot-ignoring rules,
  but they are not the same representation unless the contract explicitly
  declares the Gmail policy. The contract is what authorizes the rewrite
  (Law 5 — Contract is Truth).
- An arbitrary string `"Apple"` is **not** rewritten to a canonical email.
  It is invalid for the email contract. The capability returns
  `Status.Invalid`. It does **not** classify `"Apple"` as a "non-email" or
  invent some other canonical form (Law 4 — Canonicalize, Don't Interpret).

### 1.2 The contract declares *what*, not *how* (Law 5)

The email contract declares the policy. The capability does not infer
policies from the input. The Dict DSL form for the v2 starter is:

```python
{
  "kind": "canonical_email",
  "lowercase": True,              # default True
  "strip_whitespace": True,       # default True
  "provider_aliases": "none",     # default "none" | "gmail"
  "strict": False                 # default False; True rejects non-RFC-5321 grammar
}
```

Every field is a *policy declaration* (Law 7 — Explicit Over Clever). There
is no `auto_detect=True` knob. There is no `infer_provider=True` knob. The
caller declares the policy; the capability applies it.

### 1.3 Default canonical form (Law 1, Law 2)

With the default contract above, the canonical form is:

1. Strip leading and trailing ASCII whitespace.
2. Lower-case the local part.
3. Lower-case the domain.
4. The `+tag` (plus-suffix) is **preserved** by default, because the
   policy is `provider_aliases="none"`. The capability is not authorised
   to strip a `+tag` it cannot identify with a known provider.

This operation is:

- **Deterministic** (Law 1): no randomness, no time, no I/O, no
  environment-dependent branches.
- **Idempotent** (Law 2): `canonicalize(canonicalize(x)) == canonicalize(x)`.
  Lower-casing twice is the same as lower-casing once. Stripping
  whitespace twice is the same as stripping it once.
- **Total on supported inputs** (mandate §2): every string either
  canonicalizes to a string or is classified as `Invalid` / `Missing` /
  `Ambiguous` / `Unsupported`. There is no input that throws an
  unclassified exception.

### 1.4 Gmail alias canonicalization (Law 5, Law 7)

When the contract sets `provider_aliases="gmail"` and the domain is
`gmail.com` or `googlemail.com` (case-insensitive — `GMAIL.COM` and
`Gmail.Com` match the rule), the capability applies the documented
Gmail rules:

- The local part has all ASCII dots removed.
- The `+tag` (plus-suffix) is removed.
- The domain is normalized to `gmail.com` (`googlemail.com` is a
  synonym; the case of the input domain is normalized to lowercase).

When the contract sets `provider_aliases="gmail"` but the domain is **not**
a Gmail domain, the `+tag` and the dots are **preserved** (we have no rule
authorising rewrite for unknown providers). The operation is still
deterministic; the rule is explicit.

This is "explicit over clever" in action (Law 7): the caller declares
`provider_aliases="gmail"` to opt into Gmail rules; Paxman does not
"detect" the provider from the input.

### 1.5 Strict mode (Law 4, Law 7)

When `strict=True`, the capability rejects any input that contains
embedded whitespace (space, tab, newline) or any non-ASCII characters
in the local or domain part. It returns `Status.INVALID`. This is a
*policy declaration*, not a matching rule; the caller has explicitly
asked for the stricter input.

> **v2.0.0 scope.** The strict-mode check is intentionally narrow:
> whitespace rejection and ASCII-only enforcement. Strict mode does
> NOT invoke a dot-atom grammar check. The dot-atom surface-grammar
> gate (RFC 5322 §3.2.3 + RFC 5321 §3.4 + RFC 1035 §2.3.1) is a
> separate Law 14 requirement and runs unconditionally for every
> input, regardless of `strict`. Quoted-string local parts
> (`RFC 5322 §3.2.4`) and bracketed domain literals
> (`RFC 5321 §3.4.1` / `§3.4.2`) are out of v2.0.0 scope and fail
> the gate with `grammar_rejected` in both strict and non-strict
> modes; an explicit v2.x may extend the gate to admit them. Recording
> the v2.0.0 strict-mode scope here makes the gap explicit so a
> future reader does not infer broader validation than the code
> performs.

### 1.6 What the capability does NOT do (Law 4, Law 8a)

- It does not perform DNS lookups, MX checks, or "is this address
  deliverable" calls (Law 8a — those would be un-versioned state, and
  they are interpretation, not canonicalization).
- It does not classify the address as personal / business / role-based
  (Law 4 — that's interpretation, not canonicalization).
- It does not invent policies based on the input (Law 5).
- It does not learn from prior inputs (Law 1 — no mutable state).
- It does not return a number, score, rank, or hint between the five
  `Status` outcomes (Law 3 — Never Guess). It returns one of the five
  values; there is no number between them.

---

## 2. The architecture (from `PROPOSED_STRUCTURE.md`, instantiated)

The 12-file layout from `PROPOSED_STRUCTURE.md` is realized with the
following files (12 source modules + 5 `__init__.py` package markers
of which 3 are empty and 2 carry public re-exports + 1 internal helper
to break a circular import). The empty `__init__.py` files exist for
import-path stability and carry no runtime code; the two non-empty
ones (`src/paxman/__init__.py` and `src/paxman/_contracts/__init__.py`)
carry the public API surface and contract re-exports respectively. The
helper `_orchestrator_runtime.py` is also internal (no leading
underscore on the module because the import-cycle workaround
requires a clean `paxman._orchestrator_runtime` import target). The
full file list is:

| File | Responsibility |
|---|---|
| `src/paxman/__init__.py` | Public API: `canonicalize`, `replay`, `register_capability`. |
| `src/paxman/_core/__init__.py` | Empty. Marks `_core/` as a package. |
| `src/paxman/_core/types.py` | `CapabilityResult`, `Evidence`, `VersionStamp`, `Status` enum, `ProviderAliasesPolicy` alias. |
| `src/paxman/_core/artifact.py` | `ExecutionArtifact` (`@attrs.frozen`; Law 13). |
| `src/paxman/_core/classification.py` | `classify(...)` — maps `(capability_result, validation)` → `Status`. |
| `src/paxman/_core/validation.py` | `validate(value, contract)` — gates a `Canonicalized` outcome. |
| `src/paxman/_core/orchestrator.py` | The pipeline. Walks the six stages. |
| `src/paxman/_core/replay.py` | Byte-equal rehydration. |
| `src/paxman/_capabilities/__init__.py` | Empty. Marks `_capabilities/` as a package. |
| `src/paxman/_capabilities/protocol.py` | `Capability` Protocol. |
| `src/paxman/_capabilities/registry.py` | `CapabilityRegistry` with `register`, `freeze`, `resolve_all`. |
| `src/paxman/_capabilities/builtins/__init__.py` | Empty. Built-ins grow on demand. |
| `src/paxman/_capabilities/builtins/email.py` | `EmailCapability`. |
| `src/paxman/_contracts/__init__.py` | Re-export `Contract`, `parse_contract`. |
| `src/paxman/_contracts/contract.py` | Dict DSL → `Contract` (currently `CanonicalEmailContract` only). |
| `src/paxman/_orchestrator_runtime.py` | Holds `default_registry` (a `CapabilityRegistry`) to break the circular import between the orchestrator and `__init__.py`. |
| `src/paxman/_errors.py` | `PaxmanError` and the 6 concrete exception classes. |

**Total source modules: 12** (of which 1 is the internal
`_orchestrator_runtime.py` helper that exists only to break the
circular import between `_core/orchestrator.py` and `paxman/__init__.py`;
the other 11 are the v2.0.0 source modules from `PROPOSED_STRUCTURE.md`).
Plus 5 `__init__.py` package markers (3 empty, 2 with content —
`paxman/__init__.py` carries the public API; `_contracts/__init__.py`
carries contract re-exports). Total `.py` files under `src/paxman/`:
17.

`Status` is defined in `_core/types.py` (with the other value types) and
re-exported from `_core/classification.py` for convenience; the canonical
home is `types.py`.

### 2.1 The pipeline

```text
Input (str)
  ↓ inspect:         contract.parse(contract_dict)   (from _contracts/contract.py)
Contract (or _StubContract on parse failure)
  ↓ resolve:         registry.resolve_all(contract, value)
list[Capability]   (empty list → Status.UNSUPPORTED;
                     length > 1 → Status.AMBIGUOUS)
  ↓ execute:         capability.canonicalize(value, contract)   (one capability)
CapabilityResult
  ↓ validate:        validation.validate(result.value, contract)
ValidationResult
  ↓ classify + build: classification.classify(capability_result, validation)
                     + _build_artifact(...)
ExecutionArtifact
```

If the contract is unknown to the registry, `registry.resolve_all`
returns an empty list and the orchestrator produces an
`ExecutionArtifact` with `Status.UNSUPPORTED` and an `Evidence`
entry that names the contract kind. If two capabilities claim the
same pair, `resolve_all` returns both; the orchestrator classifies
`Status.AMBIGUOUS` and records all claimants in evidence (mandate
§5.4). The `_build_artifact` step is private to
`_core/orchestrator.py` and is the final act of the `classify`
stage.

### 2.2 Capability resolution uniqueness (mandate §5.4)

The `CapabilityRegistry` is keyed on `(capability.name,)`. A name
collision raises `ConfigurationError` (a subclass of
`CanonicalizationError`) at `register` time, before any
`canonicalize` call. The first call to `canonicalize` calls
`registry.freeze()` implicitly; `register` after that raises
`FrozenRegistryError`. Together, these ensure that "the capability set
is part of the determinism invariant" is mechanically true.

### 2.3 ExecutionArtifact is immutable (Law 13)

`ExecutionArtifact` is a `frozen=True` `attrs` dataclass. Every field
is set at construction. There are no setters. The integration test
`test_artifact_immutable` assigns to every field and asserts that each
assignment raises `FrozenInstanceError`. The property test
`test_artifact_immutability_invariant` does the same at scale.

### 2.4 Replay byte-equality (Law 12)

`replay(artifact, contract)`:

1. Re-parses the contract from its stored DSL form (the contract is
   stored on the artifact, in addition to the parsed view, so replay
   does not need the caller's original dict).
2. Verifies the `VersionStamp` matches the current Paxman version, the
   frozen capability set, and the contract version. Mismatch raises
   `VersionMismatchError`.
3. Recomputes the `replay_hash` over the artifact's content and
   compares to the stored value. Mismatch raises
   `CanonicalizationError` (a fatal invariant violation).
4. Returns the artifact, byte-equal.

The replay property is verified by `test_replay_byte_equal_invariant`
in `tests/property/`.

### 2.5 Idempotence (Law 2)

`canonicalize` produces a canonical value such that
`canonicalize(canonicalize(x), contract) == canonicalize(x, contract)`.
The capability is implemented so that lower-casing and whitespace
stripping are fixed points of themselves. The property test
`test_idempotence_invariant` checks this for a Hypothesis-generated
stream of inputs.

### 2.6 The three invariants, mechanized

| Invariant | Mechanism |
|---|---|
| **Identity** (only canonicalize) | The capability cannot orchestrate — it has no `classify` method, no `next`, no `execute`. The post-capability steps are `validation` (policy-driven check) and `classify` (deterministic mapping from `(capability_result, validation)` to `Status` + artifact construction). All three are owned by Paxman. |
| **Determinism** (same inputs → same artifact) | `registry.freeze()` makes the capability set fixed before the first call. The `VersionStamp` is recorded on every artifact. The capability is a pure function of `(value, contract)`. |
| **Replay** (`replay(a) == a` byte-equal) | `replay.py` rehydrates from the artifact's stored content; `replay_hash` is independently recomputed from `canonical_bytes()`; the artifact is `@attrs.frozen`. |

---

## 3. Data model (mandate §1.3, §2)

### 3.1 `Status` enum

```python
class Status(enum.Enum):
    CANONICALIZED = "canonicalized"
    INVALID = "invalid"
    MISSING = "missing"
    AMBIGUOUS = "ambiguous"
    UNSUPPORTED = "unsupported"
```

All five values from the mandate, no more, no less.

### 3.2 `Contract` value object

The parsed, validated, in-memory representation of a contract. The Dict
DSL is a *serialization*; the `Contract` is the value object the
orchestrator and capabilities see. For the first capability:

```python
@attrs.frozen
class CanonicalEmailContract:
    lowercase: bool
    strip_whitespace: bool
    provider_aliases: Literal["none", "gmail"]
    strict: bool
    kind: Literal["canonical_email"] = "canonical_email"
    version: int = 1
```

`version` is the contract version (mandate §8). v1 is the only
version. A future breaking change to the policy shape bumps it to v2.

### 3.3 `Evidence`

```python
@attrs.frozen
class Evidence:
    rule: str       # e.g., "lowercased_local_part", "stripped_plus_tag", "domain_synonym_gmail"
    detail: str = ""  # e.g., "googlemail.com -> gmail.com"
```

A list of `Evidence` is recorded on every `ExecutionArtifact`. This is
Law 9 (Evidence Over Score) — the artifact records *what matched and
why*, never a number, score, rank, or probability.

### 3.4 `VersionStamp`

```python
@attrs.frozen
class VersionStamp:
    paxman_version: str            # e.g., "0.0.0.dev0"
    contract_version: int          # e.g., 1
    capabilities_hash: str         # sha256 of the sorted capability names
    configuration_version: str     # constant "0" for v1; placeholder for future
```

Recorded on every `ExecutionArtifact`. Replay verifies all four
components. This is mandate §8 (versioned contracts) and mandate
Law 12 (replayability).

### 3.5 `CapabilityResult`

```python
@attrs.frozen
class CapabilityResult:
    status: Status                  # one of the five
    value: str | None = None        # the canonical value, if status is CANONICALIZED
    evidence: tuple[Evidence, ...] = ()
```

A capability returns a `CapabilityResult` from its `canonicalize`
method. The orchestrator then validates and classifies.

### 3.6 `ExecutionArtifact`

```python
@attrs.frozen
class ExecutionArtifact:
    status: Status
    value: str | None
    evidence: tuple[Evidence, ...]
    contract: _ContractLike             # structural Protocol
    version_stamp: VersionStamp
    replay_hash: str                    # sha256 of the canonical serialization

    def canonical_bytes(self) -> bytes: ...
```

The `contract` field is typed as a structural Protocol
(`_ContractLike`, defined in `src/paxman/_core/artifact.py`) that
exposes `as_dict() -> dict[str, Any]` and `version: int`. Both
`CanonicalEmailContract` (the parsed real contract) and the
orchestrator's internal `_StubContract` (used for unparseable
inputs) satisfy this Protocol structurally. This is what lets the
artifact carry a serializable contract view without forcing a
forward import from `_contracts/contract.py`.

`canonical_bytes()` produces a deterministic byte serialization (sorted
keys, no insignificant whitespace, `ensure_ascii=False`) used for
`replay_hash` computation. This is the answer to `PROPOSED_STRUCTURE.md`
Decision #6 (byte-equal serialization for `replay_hash`).

> **Equality and hashing.** `ExecutionArtifact` is `@attrs.frozen`; the
> attrs-generated `__eq__` and `__hash__` operate on the field values,
> excluding `replay_hash` (`eq=False`). For two artifacts produced by
> Paxman from the same `(input, contract, registry)`, field equality
> and `canonical_bytes()` equality agree, so the two views of
> "byte-equal" are observationally equivalent. They diverge only in
> edge cases the determinism invariant already excludes (forged
> artifacts, mutated `replay_hash`); the `replay_hash` is the
> authoritative proof, `__eq__` is the ergonomic shortcut.

### 3.7 `Capability` Protocol

```python
@runtime_checkable
class Capability(Protocol):
    name: str

    def can_handle(self, contract: Contract, value: object) -> bool: ...
    def canonicalize(self, value: object, contract: Contract) -> CapabilityResult: ...
```

The Protocol is structural (no inheritance required). A user-defined
capability is `runtime_checkable`; the registry validates duck-typing
on `register`. The Protocol deliberately omits control-flow verbs
(mandate §5.1).

---

## 4. The public API (mandate §1.3, `PROPOSED_STRUCTURE.md` §`__init__.py`)

The v2.0.0 public API surface is the exact set below. The set is
enforced by `test_no_unexpected_public_symbols` in
`tests/unit/test_public_api.py` (exact-set comparison, not
presence-only). Adding or removing a public symbol requires a spec +
plan change; the test will fail until both the surface and the
allowlist agree.

Public surface (24 entries on `dir(paxman)` after filtering
underscore-prefixed names; `__version__` is also present as the
module's dunder but the `dir()` filter excludes it):

- **Functions** (3): `canonicalize`, `replay`, `register_capability`.
- **Value types** (6): `Status`, `Evidence`, `VersionStamp`,
  `CapabilityResult`, `ValidationResult`, `ExecutionArtifact`.
- **Contracts** (3): `Contract`, `CanonicalEmailContract`,
  `parse_contract`.
- **Capability SPI** (3): `Capability`, `CapabilityRegistry`,
  `Email` (the email capability shim — value-object / factory form
  that returns a `CanonicalEmailContract`).
- **Errors** (7): `PaxmanError`, `CanonicalizationError`,
  `ContractError`, `ConfigurationError`, `FrozenRegistryError`,
  `UnsupportedContractError`, `VersionMismatchError`.
- **PEP 562 leak** (2): `Any` (typing primitive leaked by the
  `__getattr__` return type), `annotations` (`__future__` artifact).
  These are documented as accepted trade-offs in the v2.0.0 plan and
  are pinned in the test allowlist.

`__version__` (e.g. `"0.0.0.dev0"`) is the Paxman package version
recorded on every `VersionStamp`; it is exposed as a dunder and is
excluded from the `dir()` allowlist filter (which skips names
starting with `_`).

The 24-entry set is the surface a user sees on `dir(paxman)`. Internal
modules under `paxman._core/`, `paxman._capabilities/`,
`paxman._contracts/`, `paxman._errors.py`, and
`paxman._orchestrator_runtime.py` are implementation detail and must
not be reached for from user code (the leading underscore is the
convention; the public surface is the only path the test enforces).

`canonicalize` calls `registry.freeze()` on the first invocation if it
has not been called explicitly. The user may call `register_capability`
*before* the first `canonicalize`; calling it after the first
`canonicalize` raises `FrozenRegistryError`.

> **Built-ins are NOT auto-registered.** Importing
> `paxman._capabilities.builtins.email` has no side effect. The user
> must explicitly call `paxman.register_capability(EmailCapability())`
> to enable email canonicalization. This is mandated by Law 6 (Paxman
> owns the algorithm) and Law 8a (no hidden state on import).

A future v2.0.x release may add a convenience helper for built-in
registration (e.g. `paxman.enable_builtin("email")`); v2.0.0 ships the
explicit `register_capability` path only.

---

## 5. Test plan (mandate §10.1, §10.2)

### 5.1 Unit tests (`tests/unit/`)

| Test file | Coverage |
|---|---|
| `test_types.py` | `Status`, `CapabilityResult`, `Evidence`, `VersionStamp` value-object invariants. |
| `test_artifact.py` | `ExecutionArtifact` is `@attrs.frozen`; all five `Status` values produce a valid artifact; `canonical_bytes()` is deterministic and order-independent; `replay_hash` matches `sha256(canonical_bytes())`. |
| `test_classification.py` | `classify(...)` maps `(capability_result, validation)` → `Status` per the rules in §2.1. |
| `test_validation.py` | `validate(value, contract)` accepts canonical email forms; rejects strict-mode violations. |
| `test_orchestrator.py` | End-to-end pipeline against an in-test capability that records what it was called with. |
| `test_replay.py` | `replay` returns the same artifact byte-equal; raises `VersionMismatchError` on Paxman-version mismatch, contract-version mismatch, or capabilities-hash mismatch; raises `VersionMismatchError` on a malformed contract spec; raises `CanonicalizationError` on `replay_hash` mismatch. |
| `test_protocol.py` | `Capability` Protocol structural checks; objects missing `name`, `can_handle`, or `canonicalize` are not instances. |
| `test_registry.py` | `register`, `freeze`, `resolve_all`; double-register raises `ConfigurationError`; post-freeze register raises `FrozenRegistryError`; `resolve_all` returns every claimant. |
| `test_email_capability.py` | The email capability: all six cases from §1.3–§1.5, plus the case-insensitive Gmail domain case and the post-rewrite revalidation case. |
| `test_contract.py` | Dict DSL parsing: defaults, validation, `version` field, bool-field validation rejecting non-bool inputs. |
| `test_public_api.py` | `paxman.canonicalize`, `paxman.replay`, `paxman.register_capability` and the documented type re-exports are the public surface; the exact set is asserted with `==`. |

### 5.2 Property tests (`tests/property/`)

| Test file | Property |
|---|---|
| `test_replay_invariant.py` | For any `(input, contract)` and any frozen registry, `replay(canonicalize(input, contract), contract) == canonicalize(input, contract)` byte-for-byte. (Law 12.) |
| `test_idempotence_invariant.py` | For any `input`, `canonicalize(canonicalize(input, contract), contract) == canonicalize(input, contract)`. (Law 2.) |
| `test_uniqueness_invariant.py` | If two registered capabilities both return `can_handle() == True` for the same `(contract, value)`, the artifact has `Status.Ambiguous` and the evidence lists both claimants. (Mandate §5.4, Law 4.) |
| `test_artifact_immutability_invariant.py` | For any field on any `ExecutionArtifact`, assignment raises `FrozenInstanceError`. (Law 13.) |
| `test_canonicalization_invariant.py` | For any `input`, `canonicalize(input, contract)` returns an `ExecutionArtifact` whose `replay_hash` equals `sha256(artifact.canonical_bytes())`. (Law 1.) |

### 5.3 Integration test (`tests/integration/`)

`test_email_end_to_end.py`:

1. `from paxman import canonicalize, replay, register_capability`
2. `from paxman._capabilities.builtins.email import EmailCapability`
3. `register_capability(EmailCapability())`
4. Run the six scenarios from §1.3–§1.5 end-to-end, asserting on
   `result.status`, `result.value`, and `result.evidence`.
5. Run `replay(...)` and assert `rehydrated == result`.
6. Assert `test_artifact_immutability` for every field.
7. Assert `paxman.canonicalize("not-an-email", {"kind": "canonical_email"})`
   has `Status.INVALID` and an evidence entry naming the rejection rule.
8. Assert `paxman.canonicalize("user@example.com", {"kind": "unknown_kind"})`
   has `Status.UNSUPPORTED` and an evidence entry naming the contract kind.

---

## 6. Open decisions and the v2.0.0 answer (per `PROPOSED_STRUCTURE.md` "Decisions left to make")

The user said *"Forget about ADR first."* — so each decision below is
resolved to a v2.0.0 default, recorded here for posterity. A future
ADR process may revisit any of them; doing so must pass the
mandate §10.3 law-by-law test.

| Decision | v2.0.0 default | Rationale |
|---|---|---|
| What is the canonical form? (Decision 1) | A lower-cased, whitespace-stripped ASCII string with optional Gmail rules per `provider_aliases` policy. | The mandate §2 formal definition constrains the properties (deterministic, total, idempotent, totality-preserving); the v2.0.0 representation is the simplest string that satisfies them. |
| Contract DSL shape (Decision 2) | Dict DSL with `kind` discriminator and policy fields. `kind` is a closed enum; an unknown `kind` produces `Status.UNSUPPORTED`. | The mandate Law 5 says the contract is the truth. A closed enum makes "what contracts are supported" answerable as a one-line lookup. |
| Replay across versions (Decision 3) | `VersionMismatchError` is raised when the Paxman version, the contract version, or the capabilities hash on the artifact does not match the current environment. | Mandate §8 and Law 12. Conservative default; a permissive future option is recorded as a v2.x candidate. |
| Multiple capabilities claim a pair (Decision 4) | `Status.AMBIGUOUS` is returned immediately, with an evidence entry listing all claimants. | Mandate §5.4. The orchestrator never silently picks. |
| Capability priority (Decision 5) | Not supported. The Protocol has no priority field. | Mandate §5.2 litmus test. Two implementations disagreeing on priority would break Law 11. |
| Byte-equal serialization for `replay_hash` (Decision 6) | `attrs.asdict(artifact, recurse=True)` with `dict(sorted=True)`, serialized as compact JSON with `sort_keys=True`, encoded as UTF-8. | The only requirement is determinism and byte-equality across runs. Compact JSON over a frozen dataclass meets it with the smallest surface area. |

---

## 7. Law 14 — Canonical Form Provenance

[Law 14](../../../MANDATE.md#law-14--canonical-forms-have-provenance)
requires that every rule emitted by a capability carries a
`provenance: str` citation naming one of three authoritative sources:
a published specification, documented platform behavior, or a
declared Paxman policy. This section is the canonical record of the
EmailCapability's Law 14 audit.

### 7.1 Evidence schema

`Evidence` carries a `provenance` field:

```python
@attrs.frozen
class Evidence:
    rule: str
    detail: str = ""
    provenance: str = ""
```

`replay_hash` serialization is updated to include `provenance`
(breaking change to the byte layout; v2 has no pre-Law 14
artifacts in production, so no migration is needed).

### 7.2 Rule-by-rule audit of `EmailCapability`

| Rule | Law 14 category | Citation |
|---|---|---|
| `not_an_email_contract` | runtime invariant | n/a (Law 14 §3.6 allow-list) |
| `not_a_string_value` | runtime invariant | n/a (Law 14 §3.6 allow-list) |
| `strict_rejected_whitespace` | declared Paxman policy | `paxman spec/email §1.5` |
| `strict_rejected_non_ascii` | declared Paxman policy | `paxman spec/email §1.5` |
| `missing_at_sign` | authoritative spec | RFC 5322 §3.6 |
| `empty_local_or_domain` | authoritative spec | RFC 5322 §3.6 |
| `grammar_rejected` | authoritative spec | RFC 5322 §3.2.3 + RFC 5321 §3.4 + RFC 1035 §2.3.1 |
| `stripped_whitespace` | authoritative spec | RFC 5322 §2.1 + §3.6.3 (CFWS) |
| `lowercased_local_part` | declared Paxman policy | `paxman spec/email §1.3` (diverges from RFC 5321 §2.4) |
| `lowercased_domain` | authoritative spec | RFC 5321 §2.4 |
| `domain_synonym_gmail` | documented platform behavior | Google Help: "Use aliases on your Account" |
| `stripped_dots_in_local_part` | documented platform behavior | Google Help: dots don't matter in Gmail |
| `stripped_plus_tag` | documented platform behavior | Google Help: Gmail +alias addressing |

The provenance manifest lives at `_RULE_PROVENANCE` in
`src/paxman/_capabilities/builtins/email.py`; every `Evidence(...)`
construction pulls its `provenance` from it by rule name via the
`_evidence` helper. A rule with no manifest entry raises `KeyError`
at the construction site, surfacing a missing citation.

### 7.3 Surface-grammar gate

The local part is accepted iff it matches RFC 5322 §3.2.3 `dot-atom`:

```text
atext = ALPHA / DIGIT / "!" / "#" / "$" / "%" / "&" / "'" / "*" /
        "+" / "-" / "/" / "=" / "?" / "^" / "_" / "`" / "{" /
        "|" / "}" / "~"
dot-atom = atext *("." atext)
```

The domain is accepted iff it matches RFC 5321 §3.4 dot-atom form:

```text
sub-domain = Let-dig *Ldh-str
Ldh-str = Let-dig | "-"
Let-dig = ALPHA / DIGIT
dot-atom-domain = sub-domain *("." sub-domain)
```

Each label is ≤ 63 chars (RFC 1035 §2.3.1); total ≤ 253 (RFC 1035
§2.3.4). Quoted-string local parts and bracketed domain literals
are out of v2.0.0 scope and fail with `grammar_rejected`. The gate
runs AFTER the rewrite pass (strip / lowercase / gmail dot-strip /
+tag-strip) so an input like `..@gmail.com` is rewritten to an
empty local part, which the gate rejects, rather than the input
being rejected before rewrite would have produced a canonical form.
Idempotence is preserved: a canonical dot-atom email passes the
gate trivially on re-canonicalize.

### 7.4 Out-of-scope follow-ups (deferred)

1. Quoted-string local parts (`RFC 5322 §3.2.4`) — currently
   `grammar_rejected`; a v2.x capability extension.
2. Bracketed domain literals (`RFC 5321 §3.4.1` / `§3.4.2`) — same.
3. Internationalized email (`RFC 6530` / `6531`) — non-ASCII in
   local part or domain continues to be `grammar_rejected`. Tied
   to SMTPUTF8 support design.
4. README "Status Reference" + "Email defaults" + "no batch API"
   docs gaps surfaced by the user-experiment report — explicitly
   deferred per user direction.
5. `canonicalize_many` batch API — explicitly deferred and not
   shipped in v2.0.0, per user direction. A future major-version
   bump would re-open the design question.

---

## 8. Exit verification

Before the design is considered "delivered" the following must all be
true:

1. `uv sync` succeeds; `uv run python -c "import paxman"` succeeds.
2. `uv run pytest -q` exits 0 with all unit, property, and integration
   tests passing.
3. The integration test in §5.3 passes end-to-end.
4. A manual `uv run python -c '...'` invocation of the README-style
   example returns the expected canonical form.
5. A grep for the retired vocabulary in `MANDATE.md` §6.3 (the
   matched-line grep pattern is in `.coderabbit.yaml`; it is a
   fixed-string alternation of the five words, not a regex of the
   words appearing in code) in `src/paxman/**.py` returns zero
   matches. The five words are listed in `MANDATE.md` §6.3; the
   intent of this gate is to ensure the *adopted* vocabulary is
   used in code, not the retired one.
6. The thirteen laws are each backed by at least one test (Law 11 has
   the SPI litmus test; Law 12 has the replay property test; Law 13
   has the immutability property test, etc.).
7. Law 14: every `Evidence` entry from `EmailCapability.canonicalize`
   carries a non-empty `provenance` (except the two allow-listed
   dispatch invariants, `not_an_email_contract` and
   `not_a_string_value`). The `test_no_empty_provenance_in_email_capability`
   unit test enforces this.

If any item fails, the work is not complete.
