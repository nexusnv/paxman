# Architecture

> **Status:** Architecture. This document records the architectural shape of
> Paxman — the folder structure, the pipeline, the SPI, and the test layout
> that the code conforms to. It is descriptive, not deliberative: a
> contributor who needs a decision to be made does not find it here.
>
> **Authority:** [`MANDATE.md`](./MANDATE.md) is the constitutional boundary.
> This document records the folder shape that serves that boundary. Where
> this document conflicts with the mandate, the mandate wins. Where this
> document is silent, the fourteen laws apply.

## The principle

The legacy tree confused *infrastructure* with *implementation*. There were
seven subsystems, four contract adapters, five capabilities, ten ADRs, eight
design specs, and a four-level test-data model — all to deliver a function
that returned `{}` for every realistic input. Paxman inverts this: the code
is what it is, and the structure follows.

The only constraint Paxman places on itself, by design, is **determinism**
(Law 1 of the mandate). The only extension point Paxman exposes is the
**capability SPI** (§5 of the mandate). Every directory, file, and module
exists to support one of those two things, or it does not exist.

### The three invariants, mirrored here

Per mandate §1.2, Paxman rests on three invariants. The folder structure
makes each one mechanically enforceable.

| Invariant | Enforced by |
|---|---|
| **Identity** — only canonicalize; never interpret, infer, or orchestrate. | `_capabilities/protocol.py` forbids control-flow verbs; the orchestrator is one module, not a graph; no `_planner/`, `_executor/`, `_reconciler/` directories exist. |
| **Determinism** — same `input`, `contract`, `capabilities`, `configuration`, `version` → same artifact. | `_core/orchestrator.py` is pure; `_capabilities/registry.py` freezes the capability set on the first `canonicalize` call so the set is fixed before the first execution. |
| **Replay** — `replay(artifact, contract) == artifact` byte-for-byte, without re-execution. | `_core/replay.py` is its own module, given first-class architectural weight (see below); `_core/artifact.py` is immutable (Law 13); `_core/types.py` carries the leaf value objects and the `VersionStamp`. |

A contributor who proposes a directory that does not serve one of these
three invariants must explain, in their PR description, which invariant it
serves. Otherwise the directory is rejected.

---

## The pipeline Paxman owns

Per mandate §4.2, Paxman owns the pipeline. Users plug capabilities into one
stage of it; they may not rearrange the rest.

```text
Input
  │
  ▼
Contract inspection          ← _contracts/contract.py
  │
  ▼
Capability discovery         ← _capabilities/registry.py (resolver, not planner)
  │
  ▼
Capability execution         ← _capabilities/protocol.py (the SPI)
  │                            (the capability itself performs canonicalization)
  ▼
Validation                   ← _core/validation.py (post-capability policy gate)
  │
  ▼
Classification               ← _core/classification.py (deterministic mapping
  │                            to Status, which lives in _core/types.py)
  │   ├── CANONICALIZED
  │   ├── INVALID
  │   ├── AMBIGUOUS
  │   ├── MISSING
  │   └── UNSUPPORTED
  ▼
ExecutionArtifact            ← _core/artifact.py (immutable, per Law 13)
```

The orchestrator that walks this pipeline lives in `_core/orchestrator.py`.
The pipeline is split into separate modules for maintainability, *not* for
extensibility: every `_core/` module remains internal (leading underscore),
is not exported, and cannot be swapped by the user. Splitting the pipeline
into modules does not create extension points — it creates review-able
units. Law 6 of the mandate (Paxman Owns the Algorithm) still holds: the user
may extend capabilities, not the pipeline shape.

---

## The library, end to end

### Public surface

`paxman.__init__` exports the public vocabulary of the library. Users
import from it; the orchestrator and core modules stay private. As of this
writing, the public surface is:

```python
from paxman import (
    # the three user-facing verbs
    canonicalize, replay, register_capability,
    # the contract vocabulary
    Email, CanonicalEmailContract, Contract, parse_contract,
    # the type vocabulary
    Capability, CapabilityRegistry, ExecutionArtifact,
    CapabilityResult, Evidence, Status, ValidationResult, VersionStamp,
    # the error vocabulary
    CanonicalizationError, ConfigurationError, ContractError,
    FrozenRegistryError, PaxmanError, UnsupportedContractError,
    VersionMismatchError,
    # the version string
    __version__,
)
```

`paxman.normalize` deliberately does not exist: the module's
`__getattr__` raises an `AttributeError` that teaches the right function
(mandate §1.1 — Paxman canonicalizes, it does not normalize).

### The library's directory shape

```text
src/paxman/
├── __init__.py                 # the public surface above
├── _orchestrator_runtime.py    # the module-level default registry holder
├── _errors.py                  # the exception hierarchy
│
├── _core/                      # the algorithm Paxman owns (Law 6)
│   ├── __init__.py             # package marker (empty)
│   ├── orchestrator.py         # the pipeline: inspect → resolve → execute
│   │                           #   → canonicalize → validate → classify
│   ├── validation.py           # post-capability policy gate
│   ├── classification.py       # the classify() function + ValidationResult
│   ├── artifact.py             # ExecutionArtifact (immutable, Law 13)
│   ├── replay.py               # byte-equal rehydration (first-class module)
│   └── types.py                # Status, Evidence, VersionStamp,
│                               # CapabilityResult, ProviderAliasesPolicy
│
├── _capabilities/              # the SPI — the only extension point
│   ├── __init__.py             # package marker (empty)
│   ├── protocol.py             # Capability Protocol (Law 8a: pure)
│   ├── registry.py             # CapabilityRegistry — the resolver/dispatcher
│   └── builtins/               # built-in capabilities
│       ├── __init__.py         #   namespace marker (deliberately empty)
│       ├── discovery.py        #   builtin_capabilities() — the source of truth
│       └── email.py            #   EmailCapability (the shipped built-in)
│
└── _contracts/                 # contract adapters (kept minimal)
    ├── __init__.py             #   re-exports for the contract vocabulary
    └── contract.py             #   CanonicalEmailContract, Email(),
                                #   parse_contract()
```

**Total: 18 Python source files (16 with content, 2 empty package markers).**

### The test layout

```text
tests/
├── conftest.py                 # shared pytest configuration
├── unit/                       # fast, pure-function tests (one file per source file)
├── property/                   # Hypothesis property tests for the four invariants
└── integration/                # the README quickstart, end-to-end
```

| Directory | Role |
|---|---|
| `tests/unit/` | Fast, pure-function tests. One test file per source file. No I/O, no time, no network. |
| `tests/property/` | Hypothesis property tests. The four properties that must hold: (1) **replay invariant** — for any `(input, contract, registered capabilities, configuration, Paxman version)`, `replay(canonicalize(input, contract), contract) == canonicalize(input, contract)` byte-for-byte (mandate Law 12); (2) **idempotence invariant** — `canonicalize(canonicalize(x)) == canonicalize(x)` (mandate Law 2); (3) **uniqueness invariant** — for any input that admits more than one canonical reading, `canonicalize` returns an artifact with `Status.AMBIGUOUS` (mandate Law 4 and §5.4); (4) **immutability invariant** — every field on `ExecutionArtifact` raises on assignment after construction (mandate Law 13). |
| `tests/integration/` | The end-to-end tests that exercise the public API: the README quickstart, the `EmailCapability` end-to-end path, the 5-Minute Promise regressions, the `CapabilityRegistry` autoload-on-first-canonicalize path, and the isolation between the README's "Extending Paxman" section and the rest of the document. |

There is no `tests/fixtures/`, no `tests/benchmark/`, no `tests/public_api/`.
The 5-layer test-data model is gone. Paxman has one test per behavioral
claim, plus a hypothesis property per invariant.

---

## What each file is for

### `__init__.py` — the public surface

The module re-exports the public vocabulary listed above. The `__getattr__`
at the bottom makes `paxman.normalize` raise a teaching `AttributeError`
(mandate §1.1 — Paxman canonicalizes, it does not normalize). The
`AttributeError` is the mechanism, not an inconvenience: the absence of a
`normalize` attribute is a load-bearing part of the identity boundary.

### `_orchestrator_runtime.py` — the default registry holder

A 15-line module that owns the module-level `default_registry: CapabilityRegistry`
instance. It exists in its own module so `paxman.canonicalize` and
`paxman.register_capability` can both refer to the same registry without a
circular import between `paxman/__init__.py` and `_core/orchestrator.py`.

### `_core/orchestrator.py` — the pipeline (Paxman owns it)

One orchestrator. It walks the stages in §"The pipeline Paxman owns" and
returns an `ExecutionArtifact`. It is pure (Law 1): same input, contract,
registered capabilities, configuration, and Paxman version → same artifact.

The orchestrator loads the built-in capabilities lazily, on the first
`canonicalize` call, *before* it freezes the registry — so the capability
set is fixed at resolve time (Law 1: the capability set is part of the
determinism invariant). The lazy import keeps `import paxman`
side-effect-free and avoids a circular import between the built-ins and the
contract module (mandate Law 8a).

The orchestrator is intentionally split from `validation.py`,
`classification.py`, `artifact.py`, and `replay.py`. Each module has one
responsibility; none is exported. Splitting improves review-ability
*without* opening extension points.

### `_core/validation.py` — validate canonical values against contracts

After a capability produces a canonical value, the orchestrator asks this
module: does the value actually satisfy the contract's strictness policy?
Validation is the gate between capability execution and a
`Status.CANONICALIZED` outcome. If validation fails, classification yields
`Status.INVALID`. Validation is *policy checking*, not interpretation
(mandate Law 4).

For the v2.0.0 email contract, validation enforces: non-empty local part
and domain, an `@` between them, and (when the contract's `strict` flag is
on) the absence of embedded whitespace and non-ASCII characters. It does
not enforce the full RFC 5321 dot-atom grammar — that is owned by the
`EmailCapability` surface-grammar check (mandate Law 14).

### `_core/classification.py` — the `classify()` function

The deterministic function that maps `(capability_result, validation)` to a
`Status`. The classifier never picks between candidates: if more than one
capability claimed the pair and they disagree, the orchestrator yields
`Status.AMBIGUOUS` (mandate Law 4 and §5.4) *before* the classifier runs.

The `Status` enum itself lives in `_core/types.py`, not here. This module
also carries the `ValidationResult` value object (the verdict of the
validation step).

### `_core/artifact.py` — `ExecutionArtifact` (immutable, Law 13)

The artifact is the result. There is one canonical artifact schema. The
`Status` field carries the five classification outcomes per Law 8 of the
mandate.

The artifact is **immutable** (mandate Law 13). Every field — canonical
value, `Status`, evidence list, `replay_hash`, version stamps — is set at
construction and cannot be reassigned. Mutation would break the replay
invariant: a caller that does `artifact.status = SUCCESS` after the fact
would produce an artifact whose `replay_hash` no longer matches its content.
The artifact is a frozen `attrs` dataclass; there is no setter API.

The `replay_hash` is computed in `__attrs_post_init__` from the artifact's
canonical bytes — the same bytes the orchestrator and `replay.py` later
recompute independently. A forged artifact with mismatched fields is
detected at replay time, not just trusted because the field is frozen.

The artifact also carries the **evidence** of how the value was canonicalized
(mandate Law 9): which capability matched, which rule fired, which
checksum passed, and on `AMBIGUOUS` outcomes, which capabilities claimed
the pair. Each evidence entry also carries a `provenance` citation
(mandate Law 14). It does **not** carry a confidence score.

### `_core/replay.py` — byte-equal rehydration (first-class module)

Given an artifact and a contract, return the same artifact without
re-execution. The `replay_hash` on the artifact is the deterministic
signature (mandate Law 1). This module is given its own file — and
architectural weight equal to `orchestrator.py` — because replay is one of
the three invariants of Paxman (mandate §1.2), not a convenience feature.

Replay's contract:

- **Pure.** No capability re-execution; no I/O; no time-dependent branches.
- **Total on valid artifacts.** Returns the same artifact, byte-equal, or
  raises `VersionMismatchError` / `CanonicalizationError`. Replay is the
  one place where `CanonicalizationError` is raised for a content-level
  mismatch (`replay_hash` mismatch); everywhere else, `Status` is the
  outcome.
- **Verifiable.** The `replay_hash` is recomputed from the artifact's
  `canonical_bytes()` and compared against the stored value; mismatch is a
  fatal error, not a silent drift.

The `VersionStamp` check is exhaustive: `paxman_version`,
`contract_version`, and `capabilities_hash` must all match. Any mismatch
raises `VersionMismatchError`. The conservative default is to raise on any
mismatch; a future permissive variant (allow replay if the relevant
version-stamp component is byte-identical) is not yet implemented.

### `_core/types.py` — leaf value objects

The smallest units of state Paxman manipulates, and the boundary at which
mandate Laws 1, 2, 9, 12, and 14 are enforced. All are frozen `attrs`
dataclasses or `enum.Enum`. They are re-exported from `paxman.__init__` as
type vocabulary, but most end users will not instantiate them directly —
the orchestrator and the capability interface produce them.

The module carries:

- `Status` — the five mutually-exclusive outcomes (`CANONICALIZED`,
  `INVALID`, `MISSING`, `AMBIGUOUS`, `UNSUPPORTED`).
- `Evidence` — one entry on the artifact's evidence list. Carries `rule`,
  `detail`, and `provenance` (mandate Law 14). The `provenance` field is a
  human-readable citation to one of the three Law 14 sources: an
  authoritative spec, a documented platform behavior, or a declared Paxman
  policy.
- `VersionStamp` — the four-component version stamp recorded on every
  artifact: `(paxman_version, contract_version, capabilities_hash,
  configuration_version)`. Replay (mandate Law 12) verifies every component.
- `CapabilityResult` — the value a capability returns from its
  `canonicalize` method. `value` is required only when `status` is
  `CANONICALIZED`.
- `ProviderAliasesPolicy` — the closed string-enum of allowed
  `provider_aliases` values for the email contract (`"none"` and `"gmail"`
  in v2.0.0).

### `_capabilities/protocol.py` — the SPI (mandate Law 8a)

The Capability Protocol is, in its narrowest form:

```python
@runtime_checkable
class Capability(Protocol):
    name: str
    def can_handle(self, contract, value) -> bool: ...
    def canonicalize(self, value, contract) -> CapabilityResult: ...
```

`@runtime_checkable` lets the registry validate duck-typing at register
time. The Protocol deliberately omits control-flow verbs: no `next()`,
`execute()`, `pipeline`, `stage`, `context switching`, or `branching`
(mandate §5.1). A capability transforms; it does not orchestrate.

Law 8a of the mandate (Capabilities Depend Only On Replayable Inputs) is
enforced by the Protocol's contract: a capability takes `(value, contract)`
and returns a `CapabilityResult`. There is no slot for HTTP, database,
randomness, filesystem, time, or environment. If a capability depends on a
versioned, immutable dataset that is recorded on the artifact's evidence
then it is *not* a network call — it is a lookup whose version is part of
the artifact. That is allowed; the un-versioned network call is not.

### `_capabilities/registry.py` — the resolver / dispatcher

This is the replacement for the legacy "planner." The registry holds
capabilities; on each canonicalization call, the orchestrator asks the
registry *"which capability explicitly declares that it canonicalizes this
contract for this value?"* — and the registry returns the *full set* of
claimants, sorted by capability name. Sorting guarantees that two
registries with the same capability set registered in different orders
yield the same claimant order, the same `AMBIGUOUS` evidence string, and
the same `replay_hash`. That is a deterministic lookup, not a guess
(mandate §6.2).

The registry exposes:

- `register(capability)` — add a capability. Raises `FrozenRegistryError`
  if the registry is frozen, `ConfigurationError` on a duplicate name or a
  non-`Capability` argument.
- `resolve_all(contract, value) -> list[Capability]` — return every
  capability that claims the pair, sorted by `name`. The orchestrator
  classifies `Status.AMBIGUOUS` when the list has more than one entry
  (mandate Law 4 and §5.4). Callers must not silently pick a single
  entry.
- `load_builtins(builtins)` — register the built-in capabilities whose
  names are not already present. Idempotent; the user's registrations
  win over Paxman's (mandate §5.3: the user's knowledge wins).
- `freeze()` — make the registry immutable. Idempotent.
- `is_frozen` — read-only flag.
- `capabilities_hash()` — deterministic SHA-256 of the sorted registered
  capability names. Becomes the `capabilities_hash` component of the
  `VersionStamp` on every artifact (mandate §8, Law 12).

The registry does **not** rank, score, or pick a "best" capability. If
more than one capability claims the same `(contract, value)` pair, the
orchestrator classifies the outcome as `Status.AMBIGUOUS` (mandate Law 4
and §5.4) rather than choosing one. If zero capabilities claim it, the
orchestrator classifies as `UNSUPPORTED`.

### `_capabilities/builtins/` — built-in capabilities

Ships one built-in today: `EmailCapability`, in `email.py`. The discovery
helper that lists every built-in lives in `discovery.py`. The package
marker `__init__.py` is intentionally empty so that
`paxman._capabilities.builtins` is a namespace only — there are no
import-time side effects (mandate Law 8a).

`discovery.py` is the single source of truth for "what built-ins does this
version ship?". The orchestrator calls `builtin_capabilities()` and feeds
the result to `registry.load_builtins(...)` lazily, on the first
`canonicalize` call, never at `import paxman` time.

Each future built-in (`DateCapability`, `MoneyCapability`, etc.) grows
here as its own module. The directory's import path is stable from day
one, even when the directory contains only the one built-in the v2.0.0
release ships.

### `_contracts/contract.py` — the one contract format

The v2.0.0 contract vocabulary. Lives in one file, named `contract.py` —
not `dict_dsl.py` — *for the concept, not the in-memory shape*. The
contract can be expressed two equivalent ways (mandate §5):

1. **Dict DSL** — `{"kind": "canonical_email", "lowercase": True, ...}`.
   The `kind` discriminator is the wire form; an unknown `kind` raises
   `ContractError` at parse time, which the orchestrator maps to
   `Status.UNSUPPORTED`.
2. **Value-object / factory form** — `CanonicalEmailContract(...)` or the
   `Email(...)` domain-type factory. `parse_contract` short-circuits on an
   already-parsed `CanonicalEmailContract` (mandate Law 5 — the contract
   is the truth), so calling `parse_contract(Email(...))` is a no-op
   identity.

Both forms resolve to the same `CanonicalEmailContract` value object that
the orchestrator and capabilities consume. Future contract kinds (Money,
Date, etc.) bump the contract `version` and add a new dispatch branch
here.

### `_errors.py` — error hierarchy

`PaxmanError` (base), with two parallel sub-hierarchies:

- `CanonicalizationError(PaxmanError)`:
  - `AmbiguousInputError` — multiple claimants detected; normally surfaced
    as `Status.AMBIGUOUS`, raised only in defensive paths.
  - `UnsupportedContractError` — validation or classification was asked
    about a contract kind it does not know; orchestrator catches and yields
    `Status.UNSUPPORTED`.
  - `VersionMismatchError` — replay against an artifact whose `VersionStamp`
    does not match the current environment. Raised by `paxman.replay`;
    never returned as a `Status`.
  - `FrozenRegistryError` — `register` was called after `freeze`. Raised
    by `paxman.register_capability` and by the registry directly.
  - `ConfigurationError` — a capability is structurally invalid (missing
    `name`, missing methods, or duplicate registration). Raised at
    register time.
- `ContractError(PaxmanError)` — the contract is malformed or
  self-contradictory. Raised at parse time.

The classification `Status` values `INVALID`, `MISSING`, `AMBIGUOUS`, and
`UNSUPPORTED` are **not** exceptions raised by the orchestrator. They are
`Status` values on a successfully-returned `ExecutionArtifact` (mandate
Law 8 — every failure is deterministic too). The exceptions above are
raised only when *the call itself* cannot proceed (broken contract,
version mismatch, attempting to mutate a frozen registry, internal
invariant violation, structural mis-configuration of a capability).

---

## What is gone, and why

The legacy tree was removed because it encoded decisions that the project
was wrong about. Removing it is not cleanup; it is refusal to re-inherit
the legacy architecture. The mandate adds two further refusals.

| Legacy artifact | Why it is gone |
|---|---|
| `src/paxman/api/` (normalize, replay, registry) | Paxman has three public verbs, not a 7-stage orchestration. The public API is `canonicalize`, `replay`, `register_capability`. |
| `src/paxman/planner/` (heuristics, field_plan, input_profile) | The 7-step planner was the core failure (mandate §6.1). Paxman has a resolver/dispatcher, not a planner. |
| `src/paxman/reconciler/` (reconciler, confidence, conflict, merge) | The "reconciler picks between multiple candidates" model is gone (mandate Law 4). If there is ambiguity, Paxman returns `Status.AMBIGUOUS`, not a chosen candidate. |
| `src/paxman/capabilities/inference.py` (the stub) | The LLM stub is deleted. Paxman does not pretend to have inference (mandate Law 3). |
| `src/paxman/providers/` (the provider SPI work) | Paxman has no provider model. The SPI is for an LLM; Paxman has no LLM. The Paxman SPI is for *capabilities*, not for *inference providers*. |
| `src/paxman/executor/` (executor, field_runner, budget_tracker) | There is nothing to execute beyond the pipeline. The canonicalization step is one function call owned by `_core/orchestrator.py`. |
| `src/paxman/budget.py`, `src/paxman/policy.py` | There is no budget. There is no policy. Determinism is unconditional (mandate Law 1). |
| `src/paxman/artifact/` (artifact, replay, _hash, statistics) | The artifact is the result. There is one canonical artifact schema, in `_core/artifact.py`, and it is immutable (mandate Law 13). |
| `tests/integration/`, `tests/property/`, `tests/unit/`, `tests/fixtures/`, `tests/public_api/`, `tests/benchmark/` | Tests are tests. The 5-layer test-data model is gone. Paxman has three directories. |
| `examples/` (3 mini-packages) | Legacy examples demonstrated broken behavior. Paxman has no examples; the README is the example. |
| `playground/` (Docker, Jupyter, notebooks) | Legacy notebooks demonstrated broken behavior. Paxman has no playground. |
| `docs/adr/` (11 ADRs) | The ADRs describe a legacy architecture that does not exist in Paxman. New ADRs, when warranted, must be evaluated against the laws (mandate §10.3). |
| `docs/concepts/`, `docs/reference/`, `docs/howto/`, `docs/specs/`, `docs/guides/`, `docs/contributing/`, `docs/security/`, `docs/operations/`, `docs/initiatives/`, `docs/superpowers/` | Diátaxis is a documentation framework for projects that have something to document. Paxman has not earned documentation yet. |
| `docs/index.md` (the RTD landing page) | Paxman has no RTD site. |
| `mkdocs.yml`, `.readthedocs.yaml` | Paxman has no docs site. |
| `scripts/` (`golden bootstrap`, `coverage check`, `fetch_test_data`, `benchmark_import_time`) | Scripts that are tied to legacy subsystems. The current `scripts/` directory holds only the static-analysis greps that enforce this architecture; the legacy bootstrap / fetch / benchmark scripts are gone. |
| `Makefile` (236 lines, 47 targets) | Paxman has no Makefile. `uv run` is enough. |
| `CHANGELOG.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `AGENTS.md` | Stub files that referenced the legacy project structure. Paxman has no equivalent stubs. When `CONTRIBUTING.md` returns, its first sentence must be the closing mandate of the mandate: *"Paxman would rather reject a value than silently canonicalize it incorrectly"* (mandate §10.4). |
| `pyrightconfig.json`, `pyrightconfig-strict.json` | The legacy project had a "pyright strict mode" initiative. Paxman has one pyright config when it is needed. |
