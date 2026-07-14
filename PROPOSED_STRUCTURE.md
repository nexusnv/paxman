# Proposed v2 folder structure

> **Status:** Proposal. The v1.x tree is gone; this is the empty foundation
> the v2 code will grow into. Anything not listed here is intentionally
> absent — the v1.x project had 47 directories and 1,081 tracked files for a
> library that did not work. v2 starts with what is necessary and adds only
> what the code demands.
>
> **Authority:** [`MANDATE.md`](./MANDATE.md) is the constitutional boundary.
> This document is the folder shape that serves that boundary. Where this
> proposal conflicts with the mandate, the mandate wins. Where this proposal
> is silent, the thirteen laws apply.

## The principle

The v1.x project confused *infrastructure* with *implementation*. There were
seven subsystems, four contract adapters, five capabilities, ten ADRs, eight
design specs, and a four-level test-data model — all to deliver a function
that returned `{}` for every realistic input. v2 inverts this: the code is
what it is, and the structure follows.

The only constraint v2 places on itself, by design, is **determinism**
(Law 1 of the mandate). The only extension point v2 exposes is the
**capability SPI** (§5 of the mandate). Every directory, file, and module
exists to support one of those two things, or it does not exist.

### The three invariants, mirrored here

Per mandate §1.2, Paxman rests on three invariants. The folder structure
makes each one mechanically enforceable.

| Invariant | Enforced by |
|---|---|
| **Identity** — only canonicalize; never interpret, infer, or orchestrate. | `_capabilities/protocol.py` forbids control-flow verbs; the orchestrator is one module, not a graph; no `_planner/`, `_executor/`, `_reconciler/` directories exist. |
| **Determinism** — same `input`, `contract`, `capabilities`, `configuration`, `version` → same artifact. | `_core/orchestrator.py` is pure; `_capabilities/registry.py` exposes `freeze()` (see below) so the capability set is fixed before the first canonicalize call. |
| **Replay** — `replay(artifact, contract) == artifact` byte-for-byte, without re-execution. | `_core/replay.py` is its own module, given first-class architectural weight (see below); `_core/artifact.py` is immutable (Law 13); `_core/types.py` carries immutable value objects only. |

A contributor who proposes a directory that does not serve one of these
three invariants must explain, in their PR description, which invariant it
serves. Otherwise the directory is rejected.

---

## The pipeline v2 owns

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
  │
  ▼
Validation                   ← _core/validation.py (private)
  │
  ▼
Canonicalization             ← _core/orchestrator.py (private helpers)
  │
  ▼
Classification               ← _core/classification.py (Status enum + classifier)
  │   ├── Canonicalized
  │   ├── Invalid
  │   ├── Ambiguous
  │   ├── Missing
  │   └── Unsupported
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

## The working tree (committed files)

```text
paxman/
├── README.md                          # what the library is, what it is not
├── MANDATE.md                          # the 13 constitutional laws; mandate
├── RETRACTION.md                       # permanent record of the v1.x failure
├── LICENSE                             # MIT
│
├── pyproject.toml                      # project metadata, dependencies
├── .gitignore                          # universal Python + toolchain patterns
├── .coderabbit.yaml                    # code-review assistant config
│
├── .github/                            # CI + issue templates + CODEOWNERS
│   ├── workflows/
│   │   └── ci.yml                      # v2.0.0 CI: 5 jobs (test-unit, lint, typecheck, test-property, test-integration)
│   ├── ISSUE_TEMPLATE/
│   │   └── bug_report.md
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── dependabot.yml
│
├── .agents/
│   ├── PAXMAN-BRUTAL-HONESTY-POSTMORTEM.md
│   │                                   # the v1.x audit; permanent record
│   └── skills/                         # agent skills (gitignored, dev-only)
│
├── src/
│   └── paxman/                         # the library
│       ├── __init__.py                 # public API: canonicalize, replay,
│       │                              #   register_capability
│       │
│       ├── _core/                     # the algorithm Paxman owns (Law 6)
│       │   ├── orchestrator.py         #   the pipeline: inspect → resolve →
│       │   │                          #   execute → canonicalize
│       │   ├── validation.py           #   validate canonical values against
│       │   │                          #   the contract
│       │   ├── classification.py       #   Status enum + classifier
│       │   ├── artifact.py             #   ExecutionArtifact (immutable,
│       │   │                          #   Law 13)
│       │   ├── replay.py              #   byte-equal rehydration (first-class
│       │   │                          #   module — see below)
│       │   └── types.py               #   pure immutable value objects shared
│       │                              #   across _core/ (Contract view,
│       │                              #   CapabilityResult, CanonicalValue,
│       │                              #   Evidence)
│       │
│       ├── _capabilities/              # the SPI — the only extension point
│       │   ├── protocol.py             #   Capability Protocol (Law 8a: pure)
│       │   ├── registry.py            #   CapabilityRegistry — the resolver
│       │   │                          #   /dispatcher (NOT a planner, NOT a
│       │   │                          #   confidence ranker; see mandate §6)
│       │   └── builtins/              #   built-in capabilities; ships empty
│       │       └── __init__.py        #   and grows on demand
│       │
│       ├── _contracts/                 # contract adapters (kept minimal)
│       │   ├── contract.py            #   the v2 starter format (one file,
│       │   │                          #   named for the concept, not the
│       │   │                          #   in-memory shape; see below)
│       │   └── __init__.py
│       │
│       └── _errors.py                 # error hierarchy + Status values
│
└── tests/                              # the test suite
    ├── unit/                          # fast, pure-function tests
    ├── property/                      # hypothesis: determinism + idempotence
    │                                  #   invariants
    └── integration/                   # the README quickstart, end-to-end
```

**Total: 12 Python source files, 3 test directories, 13 top-level entries.**

Compare to the v1.x tree, which had:
- 7 subsystems × ~10 files each
- 4 contract adapters × ~5 files each
- 10 V1 capabilities × ~3 files each
- 11 ADRs, 4 design specs, 6 how-tos, 9 reference docs
- 1,081 tracked files

v2 starts with **~12 source files and 13 top-level entries**.

---

## What each file is for

### `__init__.py` — the public API

Three exports, nothing else:

```python
paxman.canonicalize(input_data, contract) -> ExecutionArtifact
paxman.replay(artifact, contract) -> ExecutionArtifact
paxman.register_capability(capability) -> None
```

`register_capability` is the user-facing face of the SPI. It hands the
capability to the default `CapabilityRegistry`. Users do not call the
pipeline stages directly (Law 6); they register capabilities and let Paxman
resolve them.

### `_core/orchestrator.py` — the pipeline (Paxman owns it)

One orchestrator. It walks the stages in §"The pipeline v2 owns" and returns
an `ExecutionArtifact`. It is pure (Law 1): same input, contract, registered
capabilities, configuration, and Paxman version → same artifact.

Private helper functions inside this file handle the canonicalization step
itself (the rewrite from one representation to the canonical form). They are
not exported; they are not a public stage graph; they cannot be swapped by
the user. The pipeline's shape is part of the deterministic contract.

The orchestrator is intentionally split from `validation.py`,
`classification.py`, and `artifact.py`. Each module has one responsibility;
none is exported. Splitting improves review-ability *without* opening
extension points.

### `_core/validation.py` — validate canonical values against contracts

After a capability produces a canonical value, the orchestrator asks this
module: does the value actually satisfy the contract? Validation is the
gate between capability execution and a `Status.Canonicalized` outcome. If
validation fails, classification yields `Status.Invalid`.

### `_core/classification.py` — `Status` enum + classifier

The `Status` enum (mandate §1.3 — `Canonicalized`, `Invalid`, `Missing`,
`Ambiguous`, `Unsupported`) and the deterministic function that maps a
capability result + validation result onto a `Status` value. The classifier
never picks between candidates: if more than one capability claimed the
pair and they disagree, it yields `Ambiguous` (Law 4; §5.4 of the mandate).

### `_core/artifact.py` — `ExecutionArtifact` (immutable, Law 13)

The artifact is the result. There is one canonical artifact schema. The
`Status` field carries the five classification outcomes per Law 8 of the
mandate.

The artifact is **immutable** (mandate Law 13). Every field — canonical
value, `Status`, evidence list, `replay_hash`, version stamps — is set at
construction and cannot be reassigned. Mutation would break the replay
invariant: a caller that does `artifact.status = SUCCESS` after the fact
would produce an artifact whose `replay_hash` no longer matches its content.
The artifact type is a frozen `dataclass` (or equivalent); there is no
setter API.

The artifact also carries the **evidence** of how the value was canonicalized
(Law 9): which capability matched, which rule fired, which checksum passed,
and on `Ambiguous` outcomes, which capabilities claimed the pair. It does
**not** carry a confidence score.

### `_core/replay.py` — byte-equal rehydration (first-class module)

Given an artifact and a contract, return the same artifact without
re-execution. The `replay_hash` on the artifact is the deterministic
signature (Law 1). This module is given its own file — and architectural
weight equal to `orchestrator.py` — because replay is one of the three
invariants of Paxman (mandate §1.2), not a convenience feature.

Replay's design constraints:

- **Pure.** No capability re-execution; no I/O; no time-dependent branches.
- **Total on valid artifacts.** Returns the same artifact, byte-equal, or
  raises `VersionMismatchError`.
- **Verifiable.** The `replay_hash` is recomputed from the stored artifact
  content and compared against the stored value; mismatch is a fatal error,
  not a silent drift.

Crossing a contract version or Paxman version boundary in `replay` is the
open design decision recorded in §"Decisions left to make."

### `_core/types.py` — shared immutable value objects

Pure immutable value objects tend to accumulate: `Contract` (the in-memory
view of a contract after parsing), `CapabilityResult`, `CanonicalValue`,
`Evidence`, the version stamps (Paxman version, contract version,
capability set version). Putting them inside `artifact.py` would eventually
make `artifact.py` the file that holds everything. Instead they live in
`_core/types.py`:

- `Contract` — the parsed, validated, in-memory representation of a contract.
- `CapabilityResult` — the value a capability returns from its `canonicalize`
  method (canonical value or a non-`Canonicalized` `Status`).
- `CanonicalValue` — the type of the canonical value carried on a
  `Canonicalized` artifact.
- `Evidence` — one entry on the artifact's evidence list (which capability,
  which rule, which checksum).
- `VersionStamp` — the (Paxman version, contract version, capability set
  version, configuration version) tuple recorded on every artifact.

All are frozen `dataclass` or equivalent. None is exported from
`paxman.__init__`; they are internal types shared across `_core/` modules.

### `_capabilities/protocol.py` — the SPI (mandate Law 8a)

The Capability Protocol is, in its narrowest form:

```python
class Capability(Protocol):
    name: str
    def can_handle(self, contract, value) -> bool: ...
    def canonicalize(self, value, contract) -> CapabilityResult: ...
```

The Protocol deliberately omits control-flow verbs: no `next()`,
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

This is the replacement for the v1.x "planner." The registry holds
capabilities; on each canonicalization call, the orchestrator asks the
registry *"which capability explicitly declares that it canonicalizes this
contract for this value?"* That is a deterministic lookup, not a guess
(mandate §6.2).

The registry exposes:

- `register(capability)` — add a capability.
- `resolve(contract, value) -> Capability | None` — find the matching
  capability, or return `None` (orchestrator then classifies as
  `Unsupported`).
- `freeze() -> None` — after `freeze()`, the registry rejects further
  `register` calls. `freeze` is called implicitly by the first
  `canonicalize` call (or explicitly by the user) so that the capability set
  is fixed before the first canonicalization. A frozen registry guarantees
  that capability ordering cannot change accidentally during a run. This
  reinforces determinism (Law 1): the capability set is part of the
  determinism invariant, and `freeze` makes that part mechanically enforced.

The registry does **not** rank, score, or pick a "best" capability. If more
than one capability claims the same `(contract, value)` pair, the orchestrator
classifies the outcome as `Status.Ambiguous` (mandate Law 4 and §5.4) rather
than choosing one. If zero capabilities claim it, the orchestrator
classifies as `Unsupported`.

### `_capabilities/builtins/` — built-in capabilities

Ships empty. Built-in capabilities (`DateCapability`, `MoneyCapability`,
etc.) grow here on demand, each as one module per capability. The directory
exists so the import path is stable from day one; its contents are
intentionally absent until the v2 code earns them.

Empty sends a message: *do not add features until they are needed.*

### `_contracts/contract.py` — the one contract format

The v2 starter contract format lives in one file. The file is named
`contract.py` — not `dict_dsl.py` — *for the concept, not the in-memory
shape*. Today the contract is expressed as a dict; tomorrow it might be an
object. The filename should not encode the implementation, or every future
evolution of the format becomes a rename and a broken import path.

Dict DSL is sufficient as the starter: the caller describes the canonical
shape as a dict, Paxman enforces it. Pydantic / JSON Schema / OpenAPI
adapters are v2.x concerns and will not be added until there is a concrete
use case. Law 5 of the mandate (Contract is Truth): without a contract,
Paxman has no work to do.

### `_errors.py` — error hierarchy

`CanonicalizationError` (base), with subclasses:

- `AmbiguousInputError` — mandate Law 4: multiple canonical readings, refuse
  to pick.
- `ContractError` — the contract is malformed or self-contradictory.
- `UnresolvedError` — no registered capability canonicalizes the input.
- `VersionMismatchError` — replay against an artifact from a different
  Paxman version, a different contract version (see §"Decisions left to
  make"), or a different frozen capability set.
- `FrozenRegistryError` — `register` was called after `freeze`.

The classification `Status` values `Invalid`, `Missing`, `Ambiguous`,
`Unsupported` are **not** exceptions raised by the orchestrator. They are
`Status` values on a successfully-returned `ExecutionArtifact` (mandate
Law 8 — every failure is deterministic too). The exceptions above are raised
only when *the call itself* cannot proceed (broken contract, version
mismatch, attempting to mutate a frozen registry, internal invariant
violation).

---

## What is gone, and why

The v1.x tree was removed because it encoded decisions the v1.x project was
wrong about. Removing it is not cleanup; it is refusal to re-inherit the v1.x
architecture. The mandate adds two further refusals.

| v1.x artifact | Why it is gone |
|---|---|
| `src/paxman/api/` (normalize, replay, registry) | v2 has three public functions, not a 7-stage orchestration. The API is `canonicalize`, `replay`, `register_capability`. |
| `src/paxman/planner/` (heuristics, field_plan, input_profile) | The 7-step planner was the v1.x core failure (mandate §6.1). v2 has a resolver/dispatcher with `freeze()`, not a planner. |
| `src/paxman/reconciler/` (reconciler, confidence, conflict, merge) | The "reconciler picks between multiple candidates" model is gone (mandate Law 4). If there is ambiguity, v2 returns `Status.Ambiguous`, not a chosen candidate. |
| `src/paxman/capabilities/v1/inference.py` (the stub) | The LLM stub is deleted. v2 does not pretend to have inference (mandate Law 3). |
| `src/paxman/providers/` (the v1.2.0 SPI work) | v2 has no provider model. The SPI is for an LLM; v2 has no LLM. The v2 SPI is for *capabilities*, not for *inference providers*. |
| `src/paxman/executor/` (executor, field_runner, budget_tracker) | There is nothing to execute beyond the pipeline. The canonicalization step is one function call owned by `_core/orchestrator.py`. |
| `src/paxman/budget.py`, `src/paxman/policy.py` | There is no budget. There is no policy. Determinism is unconditional (mandate Law 1). |
| `src/paxman/artifact/` (artifact, replay, _hash, statistics) | The artifact is the result. There is one canonical artifact schema, in `_core/artifact.py`, and it is immutable (mandate Law 13). |
| `tests/integration/`, `tests/property/`, `tests/unit/`, `tests/fixtures/`, `tests/public_api/`, `tests/benchmark/` | Tests are tests. The v1.x 5-layer test-data model is gone. v2 has three directories. |
| `examples/` (3 mini-packages) | v1.x examples demonstrated broken behavior. v2 has no examples; the README is the example. |
| `playground/` (Docker, Jupyter, notebooks) | v1.x notebooks demonstrated broken behavior. v2 has no playground. |
| `docs/adr/` (11 ADRs) | The ADRs describe a v1.x architecture that does not exist in v2. New ADRs, when warranted, must be evaluated against the 13 laws (mandate §10.3). |
| `docs/concepts/`, `docs/reference/`, `docs/howto/`, `docs/specs/`, `docs/guides/`, `docs/contributing/`, `docs/security/`, `docs/operations/`, `docs/initiatives/`, `docs/superpowers/` | Diátaxis is a documentation framework for projects that have something to document. v2 has not earned documentation yet. |
| `docs/index.md` (the RTD landing page) | v2 has no RTD site. |
| `mkdocs.yml`, `.readthedocs.yaml` | v2 has no docs site. |
| `scripts/` (golden bootstrap, coverage check, fetch_test_data, benchmark_import_time) | Scripts that are tied to v1.x subsystems. v2 has no scripts. |
| `Makefile` (236 lines, 47 targets) | v2 has no Makefile. `uv run` is enough. |
| `CHANGELOG.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `AGENTS.md` | Stub files that referenced the v1.x project structure. v2 has no equivalent stubs. When `CONTRIBUTING.md` returns, its first sentence must be the closing mandate of the mandate: *"Paxman would rather reject a value than silently canonicalize it incorrectly"* (mandate §10.4). |
| `pyrightconfig.json`, `pyrightconfig-strict.json` | v1.x had a "pyright strict mode" initiative (closed in v1.1.0). v2 has one pyright config when it is needed. |

---

## What stays, and why

| Path | Why |
|---|---|
| `README.md` | The library needs a README. v2's README states what the library is and is not, with no marketing copy. |
| `MANDATE.md` | The 13 constitutional laws. Authoritative for v2 and all subsequent releases. |
| `RETRACTION.md` | Permanent record of the v1.x retraction. Future contributors (including the v2 author) need to read it before making decisions. |
| `LICENSE` | MIT. Unchanged. |
| `.gitignore` | Universal Python + uv + toolchain patterns. No project-specific exclusions. |
| `.pre-commit-config.yaml` | ruff + mypy are non-negotiable. |
| `.coderabbit.yaml` | Code review assistant config (v1.x had it; harmless to keep). |
| `.github/` | CI workflow, issue templates, dependabot, CODEOWNERS. The CI workflow is the one v1.x workflow that v2 keeps. |
| `.agents/PAXMAN-BRUTAL-HONESTY-POSTMORTEM.md` | The audit. v1.x failed in a specific way; v2 needs to know that failure to avoid it. |
| `.agents/skills/` | Agent skills (development-only, gitignored). Not part of the library. |

---

## The v2 test suite (what is in `tests/`)

Three directories, each with one role.

| Directory | Role |
|---|---|
| `tests/unit/` | Fast, pure-function tests. One test file per source file. No I/O, no time, no network. |
| `tests/property/` | Hypothesis property tests. The four properties that must hold: (1) **replay invariant** — for any `(input, contract, registered capabilities, configuration, Paxman version)`, `replay(canonicalize(input, contract), contract) == canonicalize(input, contract)` byte-for-byte (mandate Law 12); (2) **idempotence invariant** — `canonicalize(canonicalize(x)) == canonicalize(x)` (mandate Law 2); (3) **uniqueness invariant** — for any input that admits more than one canonical reading, `canonicalize` returns an artifact with `Status.Ambiguous` (mandate Law 4 and §5.4); (4) **immutability invariant** — every field on `ExecutionArtifact` raises on assignment after construction (mandate Law 13). |
| `tests/integration/` | The end-to-end test that runs the README example. If the README example ever returns `{}` or `Status.Unsupported` for a valid input again, the test fails and the build is red. A second integration test asserts that `CapabilityRegistry.freeze()` followed by `register(...)` raises `FrozenRegistryError`. |

There is no `tests/fixtures/`, no `tests/benchmark/`, no `tests/public_api/`.
The v1.x 5-layer test-data model and 2,754-test suite verified plumbing. v2
has one test per behavioral claim, plus a hypothesis property per invariant.

---

## Decisions left to make

The folder structure is the easy part. The hard decisions are the ones the
folder structure defers to the code. The v2 author will need to make these
decisions before the first `paxman.canonicalize` call can be written:

1. **What is a "canonical form"?** Is it a JSON object with sorted keys? A
   specific byte sequence? A typed Python value? The mandate §2 defines the
   *properties* (deterministic, total on supported inputs, idempotent,
   totality-preserving on rejection); the v2 code decides the *representation*.
2. **How does the contract express canonicality?** `_contracts/contract.py`
   is the starter, but today's dict form cannot express "the only valid
   canonical form is the sorted-key JSON of this dict" without more
   machinery. The v2 `_contracts/contract.py` module decides.
3. **What does `paxman.replay` do when the artifact is from a different Paxman
   version, a different contract version, or a different frozen capability
   set?** v1.x raised `VersionMismatchError` for Paxman version alone. v2
   adds contract version and frozen capability	set version to the
   `VersionStamp` on every artifact (mandate §8). The conservative default is
   to raise `VersionMismatchError` on any mismatch. A permissive future
   variant: allow replay if the relevant version-stamp component is
   byte-identical. The v2 `_core/replay.py` module decides.
4. **When two registered capabilities both claim the same `(contract, value)`
   pair, does the orchestrator immediately classify as `Ambiguous`, or does
   it attempt each in registration order and only classify `Ambiguous` if
   they disagree?** Mandate Law 4 mandates the *outcome* (no silent pick);
   the *algorithm* is a v2 design decision and must be recorded as an ADR.
5. **Can a capability declare priority via declarative metadata (e.g. an
   integer `priority` field) without violating mandate Law 3?** The litmus
   test (mandate §5.2) is the rule: if two capabilities can produce
   different outputs for the same input while both claiming priority, the
   abstraction is too vague and priority is forbidden. The v2 SPI decides
   and records the reasoning in an ADR.
6. **What is the byte-equal serialization format for `ExecutionArtifact`
   that the `replay_hash` is computed over?** Law 12 mandates byte-equal
   replay; the hash is only meaningful if the serialization is itself
   deterministic. The v2 `_core/artifact.py` and `_core/replay.py` modules
   decide, probably with `__slots__` + a frozen dict ordering or a
   canonical-JSON form.

These are not folder-structure decisions. They are design decisions, and the
folder structure does not constrain them. The folder structure exists to keep
the design decisions visible — small, honest, scoped — and to keep the 13
laws enforceable on every pull request (mandate Law 11).