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

## The Principle

The legacy tree confused *infrastructure* with *implementation*. There were
seven subsystems, four contract adapters, five capabilities, ten ADRs, eight
design specs, and a four-level test-data model — all to deliver a function
that returned `{}` for every realistic input. Paxman inverts this: the code
is what it is, and the structure follows.

The only constraint Paxman places on itself, by design, is **determinism**
(Law 1 of the mandate). The only extension point Paxman exposes is the
**capability SPI** (§5 of the mandate). Every directory, file, and module
exists to support one of those two things, or it does not exist.

### The Three Invariants, Mirrored Here

Per mandate §1.2, Paxman rests on three invariants. The folder structure
makes each one mechanically enforceable.

| Invariant | Enforced by |
|---|---|
| **Identity** — only canonicalize; never interpret, infer, or orchestrate. | `_capabilities/protocol.py` forbids control-flow verbs; the engine is one module (`_core/engine.py`), not a graph; no `_planner/`, `_executor/`, `_reconciler/` directories exist. |
| **Determinism** — same `input`, `contract`, `capabilities`, `configuration`, `version` → same artifact. | `_core/engine.py` is deterministic once the registry is frozen; `_registry/capability_registry.py` freezes the capability set on the first `canonicalize` call so the set is fixed before the first execution (mandate Law 1). |
| **Replay** — `replay(artifact, contract) == artifact` byte-for-byte, without re-execution. | `_core/replay.py` is its own module, given first-class architectural weight (see below); `_core/artifact.py` is immutable (Law 13); the leaf value objects (`Status`, `Evidence`, `VersionStamp`, `CapabilityResult`) live in `_core/status.py`, `_core/provenance.py`, and `_core/result.py`. |

A contributor who proposes a directory that does not serve one of these
three invariants must explain, in their PR description, which invariant it
serves. Otherwise the directory is rejected.

---

## The Pipeline Paxman Owns

Per mandate §4.2, Paxman owns the pipeline. Users plug capabilities into one
stage of it; they may not rearrange the rest.

```text
Input
  │
  ▼
Contract inspection          ← _dsl/parser.py (parse_contract)
  │
  ▼
Capability discovery         ← _registry/capability_registry.py (resolver, not planner)
  │
  ▼
Capability execution         ← _capabilities/protocol.py (the SPI)
  │                            (the capability itself performs canonicalization)
  ▼
Validation                   ← _core/validation.py (post-capability policy gate)
  │
  ▼
Classification               ← _core/classification.py (deterministic mapping
  │                            to Status, which lives in _core/status.py)
  │   ├── CANONICALIZED
  │   ├── INVALID
  │   ├── AMBIGUOUS
  │   ├── MISSING
  │   └── UNSUPPORTED
  ▼
ExecutionArtifact            ← _core/artifact.py (immutable, per Law 13)
```

The engine that walks this pipeline lives in `_core/engine.py`.
The pipeline is split into separate modules for maintainability, *not* for
extensibility: every `_core/` module remains internal (leading underscore),
is not exported, and cannot be swapped by the user. Splitting the pipeline
into modules does not create extension points — it creates review-able
units. Law 6 of the mandate (Paxman Owns the Algorithm) still holds: the user
may extend capabilities, not the pipeline shape.

---

## The Library, End to End

### Public Surface

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

### The Library's Directory Shape

```text
src/paxman/
├── __init__.py                 # the public surface above
├── _orchestrator_runtime.py    # the module-level default registry holder
├── _errors/                    # the exception hierarchy (package)
│   ├── __init__.py             #   re-exports the exception vocabulary
│   └── exceptions.py           #   PaxmanError + sub-hierarchies
├── _core/                      # the algorithm Paxman owns (Law 6)
│   ├── __init__.py             #   package marker (empty)
│   ├── engine.py               #   the pipeline: inspect → resolve → execute
│   │                           #     → canonicalize → validate → classify
│   ├── validation.py           #   post-capability policy gate
│   ├── classification.py       #   the classify() function + ValidationResult
│   ├── artifact.py             #   ExecutionArtifact (immutable, Law 13)
│   ├── replay.py               #   byte-equal rehydration (first-class module)
│   ├── provenance.py           #   Evidence (provenance record); _RULE_PROVENANCE lives in each capability's rules.py
│   ├── result.py               #   CapabilityResult, VersionStamp
│   ├── status.py               #   Status enum (five outcomes)
│   └── contracts.py            #   the structural Contract Protocol
├── _registry/                  # the two registries (resolver + dispatch)
│   ├── __init__.py             #   package marker (empty)
│   ├── capability_registry.py  #   CapabilityRegistry — the resolver/dispatcher
│   └── contract_registry.py    #   kind → builder dispatch for parse_contract
├── _capabilities/              # the SPI — the only extension point
│   ├── __init__.py             #   re-exports domain contract vocabulary
│   ├── protocol.py             #   Capability Protocol (Law 8a: pure)
│   ├── discovery.py            #   builtin_capabilities() — source of truth
│   ├── email/                  #   EmailCapability (shipped built-in)
│   │   ├── __init__.py         #     re-exports CanonicalEmailContract, Email, GRAMMARS, recognize
│   │   ├── contract.py         #     CanonicalEmailContract + Email()
│   │   ├── grammar.py          #     Layer 1 recognition: GRAMMARS + recognize() (raw captures only)
│   │   ├── canonicalizer.py    #     EmailCapability (the SPI implementation)
│   │   ├── parser.py           #     email-specific parsing helpers
│   │   └── rules.py            #     _RULE_PROVENANCE manifest (Law 14) + fired-rule helper
│   ├── uuid/                   #   UUIDCapability (shipped built-in)
│   │   ├── __init__.py         #     re-exports CanonicalUUIDContract, UUID, GRAMMARS, recognize
│   │   ├── contract.py         #     CanonicalUUIDContract + UUID()
│   │   ├── grammar.py          #     Layer 1 recognition: GRAMMARS + recognize() (raw captures only)
│   │   ├── canonicalizer.py    #     UUIDCapability
│   │   ├── parser.py
│   │   └── rules.py            #     _RULE_PROVENANCE manifest (Law 14) + fired-rule helper
│   ├── date/                   #   DateCapability (shipped built-in)
│   │   ├── __init__.py         #     re-exports CanonicalDateContract, Date, GRAMMARS, recognize
│   │   ├── contract.py         #     CanonicalDateContract + Date()
│   │   ├── grammar.py          #     Layer 1 recognition: GRAMMARS + recognize() (raw captures only)
│   │   ├── canonicalizer.py    #     DateCapability
│   │   ├── parser.py
│   │   ├── rules.py            #     _RULE_PROVENANCE manifest (Law 14) + fired-rule helper
│   │   ├── value.py            #     date value objects
│   │   └── calendar.py         #     calendar / locale helpers
│   ├── phone/                  #   PhoneCapability (shipped built-in)
│   │   ├── __init__.py         #     re-exports CanonicalPhoneContract, Phone, GRAMMARS, recognize
│   │   ├── contract.py         #     CanonicalPhoneContract + Phone()
│   │   ├── grammar.py          #     Layer 1 recognition: GRAMMARS + recognize() (raw captures only)
│   │   ├── canonicalizer.py    #     PhoneCapability
│   │   ├── parser.py
│   │   └── rules.py            #     _RULE_PROVENANCE manifest (Law 14) + fired-rule helper
│   └── url/                    #   URLCapability (shipped built-in)
│       ├── __init__.py         #     re-exports CanonicalURLContract, URL, GRAMMARS, recognize
│       ├── contract.py         #     CanonicalURLContract + URL()
│       ├── grammar.py          #     Layer 1 recognition: GRAMMARS + recognize() (raw captures only)
│       ├── canonicalizer.py    #     URLCapability
│       ├── parser.py
│       └── rules.py            #     _RULE_PROVENANCE manifest (Law 14) + fired-rule helper
├── _dsl/                       # the contract DSL (Dict ↔ value object)
│   ├── __init__.py             #   re-exports parse_contract
│   ├── parser.py               #   parse_contract — kind dispatch
│   └── serializer.py           #   contract → Dict DSL (as_dict round-trip)
└── _types/                     # shared leaf types (domain-free)
    ├── __init__.py             #   package marker (empty)
    └── common.py               #   ProviderAliasesPolicy, etc.
```

**Total: 42 Python source files across the packages above.**

This shape is the concrete form of two mandate boundaries. **Mandate §4.4**
(capabilities own domain knowledge): every domain's `contract.py`,
`canonicalizer.py`, `parser.py`, and `rules.py` live under
`paxman._capabilities.<domain>/`, never in core. **Mandate §5.5** (Contract
Protocol vs Domain Contract): the **Paxman Contract Protocol** is
`paxman._core.contracts` (structural only — names no domain; satisfies mandate
Law 5), while the **Domain Contract** is the value object each capability owns
in `paxman._capabilities.<domain>.contract` (`CanonicalEmailContract`,
`CanonicalUUIDContract`, `CanonicalDateContract`). The core knows the
protocol; the capability owns the policy.

### The Test Layout

```text
tests/
├── conftest.py                 # shared pytest configuration
├── unit/                       # fast, pure-function tests (one file per source file)
├── property/                   # Hypothesis property tests for the three invariants
└── integration/                # the README quickstart, end-to-end
```

| Directory | Role |
|---|---|
| `tests/unit/` | Fast, pure-function tests. One test file per source file. No I/O, no time, no network. |
| `tests/property/` | Hypothesis property tests. The three properties that must hold: (1) **replay invariant** — for any `(input, contract, registered capabilities, configuration, Paxman version)`, `replay(canonicalize(input, contract), contract) == canonicalize(input, contract)` byte-for-byte (mandate Law 12); (2) **idempotence invariant** — for any supported input, `canonicalize(canonicalize(input, contract), contract) == canonicalize(input, contract)` (mandate Law 2); (3) **uniqueness invariant** — for any input that admits more than one canonical reading, `canonicalize` returns an artifact with `Status.AMBIGUOUS` (mandate Law 4 and §5.4). The artifact immutability check (mandate Law 13) is enforced at the type level (`@attrs.frozen`) and verified in unit tests. |
| `tests/integration/` | The end-to-end tests that exercise the public API: the README quickstart, the `EmailCapability` end-to-end path, the 5-Minute Promise regressions, the `CapabilityRegistry` autoload-on-first-canonicalize path, and the isolation between the README's "Extending Paxman" section and the rest of the document. |

There is no `tests/fixtures/`, no `tests/benchmark/`, no `tests/public_api/`.
The 5-layer test-data model is gone. Paxman has one test per behavioral
claim, plus a hypothesis property per invariant.

---

## What Each File Is For

### `__init__.py` — The Public Surface

The module re-exports the public vocabulary listed above. The `__getattr__`
at the bottom makes `paxman.normalize` raise a teaching `AttributeError`
(mandate §1.1 — Paxman canonicalizes, it does not normalize). The
`AttributeError` is the mechanism, not an inconvenience: the absence of a
`normalize` attribute is a load-bearing part of the identity boundary.

### `_orchestrator_runtime.py` — The Default Registry Holder

A 15-line module that owns the module-level `default_registry: CapabilityRegistry`
instance. It exists in its own module so `paxman.canonicalize` and
`paxman.register_capability` can both refer to the same registry without a
circular import between `paxman/__init__.py` and `_core/engine.py`.

### `_core/engine.py` — The Pipeline (Paxman Owns It)

One orchestrator. It walks the stages in §"The pipeline Paxman owns" and
returns an `ExecutionArtifact`. It is deterministic (Law 1): once the
registry is frozen, the same input, contract, registered capabilities,
configuration, and Paxman version produce the same artifact.

The orchestrator performs one-time initialization on the first `canonicalize`
call: it loads the built-in capabilities lazily and then freezes the registry,
*before* any execution — so the capability set is fixed at resolve time (Law
1: the capability set is part of the determinism invariant). This
initialization is deterministic and runs exactly once; it is not referential
transparency, but it does not affect the determinism guarantee for any call
after the registry is frozen. The lazy import keeps `import paxman`
side-effect-free and avoids a circular import between the built-ins and the
contract module (mandate Law 8a).

The orchestrator is intentionally split from `validation.py`,
`classification.py`, `artifact.py`, and `replay.py`. Each module has one
responsibility; none is exported. Splitting improves review-ability
*without* opening extension points.

### `_core/validation.py` — Validate Canonical Values Against Contracts

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

### `_core/classification.py` — The `classify()` Function

The deterministic function that maps `(capability_result, validation)` to a
`Status`. The classifier never picks between candidates: if more than one
capability claimed the pair and they disagree, the orchestrator yields
`Status.AMBIGUOUS` (mandate Law 4 and §5.4) *before* the classifier runs.

The `Status` enum itself lives in `_core/status.py`, not here. This module
also carries the `ValidationResult` value object (the verdict of the
validation step).

### `_core/artifact.py` — `ExecutionArtifact` (Immutable, Law 13)

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
(mandate Law 14). It does **not** carry a numeric score.

### `_core/replay.py` — Byte-Equal Rehydration (First-Class Module)

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

### `_core/status.py`, `_core/provenance.py`, `_core/result.py`, `_types/common.py` — Leaf Value Objects

The smallest units of state Paxman manipulates, and the boundary at which
mandate Laws 1, 2, 9, 12, and 14 are enforced. All are frozen `attrs`
dataclasses or `enum.Enum`, split across domain-free modules: `Status` in
`_core/status.py`, `Evidence` and the `_RULE_PROVENANCE` manifest in
`_core/provenance.py`, `CapabilityResult` and `VersionStamp` in
`_core/result.py`, and shared closed enums such as `ProviderAliasesPolicy`
in `_types/common.py`. They are re-exported from `paxman.__init__` as type
vocabulary, but most end users will not instantiate them directly — the
engine and the capability interface produce them.

The modules carry:

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

### `_capabilities/protocol.py` — The SPI (Mandate Law 8a)

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

### `_registry/capability_registry.py` — The Resolver / Dispatcher

This is the replacement for the legacy "planner." (The contract-side
dispatch — mapping each contract `kind` to its builder — lives separately in
`_registry/contract_registry.py` and is used by `_dsl/parser.parse_contract`.)
The registry holds
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

### `_capabilities/{email,uuid,date,phone,url}/` — Built-In Capabilities

Ships five built-ins today: `EmailCapability`, `UUIDCapability`,
`DateCapability`, `PhoneCapability`, and `URLCapability`. Each owns its domain under `paxman._capabilities.<domain>`
(`contract.py`, `grammar.py`, `canonicalizer.py`, `parser.py`, `rules.py`,
plus `value.py` and `calendar.py` for dates). Each capability package
self-registers its contract builder via `register_contract` so
`_dsl/parser.parse_contract` can dispatch on the contract `kind` without the
engine knowing the domain.

Each capability shares the same four-stage shape, split so that recognition
is **separate from** resolution (mandate Law 14 — a rule must derive its
canonical form from a cited source; recognition assigns no meaning):

1. **`grammar.recognize` (Layer 1 — recognition).** Anchored grammars in
   `grammar.py` full-match the raw input and return `RecognizedRep` objects
   carrying only *raw string captures* and a Law-14 `source`. No semantic
   meaning is assigned here. Email has four grammars (addr-spec, whitespace-
   padded, verbal "at"/"dot", quoted-local); date has a bracket-notation
   grammar set; uuid has one canonical-form grammar (RFC 4122 §3).
2. **`generate_interpretations` (resolver).** Assigns meaning to the raw
   captures and enumerates candidate canonical forms, applying the declared
   contract policies (lowercasing, provider-equivalence, etc.).
3. **`resolve_and_validate`.** Validates each candidate against the domain
   grammar; drops those that name no valid value (email: RFC 5322 §3.2.3
   dot-atom; uuid: RFC 4122 §3 form + version-nibble policy).
4. **`classify`.** Maps survivors to a `Status` — `CANONICALIZED`,
   `AMBIGUOUS` (when more than one candidate survives, the ambiguity is
   surfaced, never guessed), or `INVALID` (a recognition miss yields
   `unrecognized_format`; a validation failure yields `grammar_rejected`).

The discovery helper `builtin_capabilities()` lives in
`paxman._capabilities.discovery` and is the single source of truth for "what
built-ins does this version ship?". The engine calls `builtin_capabilities()`
and feeds the result to `registry.load_builtins(...)` lazily, on the first
`canonicalize` call, never at `import paxman` time (mandate Law 8a).

Each future built-in grows as its own `_capabilities/<domain>/` package,
pinning its contract `version` and adding a new `register_contract` branch —
the same additive pattern the five shipped capabilities use. (Money is the
deliberate exception: it was reclassified as a *multi-field* canonicalization
— a currency field plus a decimal field — and deferred past the v2 RC, rather
than shipped as a single `MoneyCapability`. The `_capabilities/<domain>/`
pattern still applies should it be scoped later; see mandate §5.5.)

### `_dsl/parser.py` + `_capabilities/<domain>/contract.py` — The One Contract Format

The v2.0.0 contract vocabulary. The contract *kind* is dispatched by
`_dsl/parser.parse_contract`, which routes each `kind` to a per-domain
builder registered via `register_contract` (in `_registry/contract_registry.py`).
`_registry/contract_registry.register_contract` is the registry that replaced
the former central `_KIND_DISPATCH` dict and its per-kind `if` branches
(mandate §6.5): the core no longer enumerates domains. The two layers from
mandate §5.5 are concrete here — the **Paxman Contract Protocol**
(`paxman._core.contracts`, structural, names no domain) vs the **Domain
Contract** (the value object each capability owns in
`paxman._capabilities.<domain>.contract`).
Each domain owns its value object in `paxman._capabilities.<domain>.contract`
(`CanonicalEmailContract`, `CanonicalUUIDContract`, `CanonicalDateContract`)
plus the `Email()`, `UUID()`, `Date()` domain-type factories. The contract
can be expressed two equivalent ways (mandate §5):

1. **Dict DSL** — `{"kind": "canonical_email", "lowercase": True, ...}`.
    The `kind` discriminator is the wire form. An unknown `kind` (or a
    malformed spec) raises `ContractError` at parse time, but the
    orchestrator *catches* that and returns `Status.UNSUPPORTED` — the
    call never raises `ContractError` to the caller. So from the caller's
    perspective an unsupported `kind` is a returned `Status`, not a raised
    exception, unless a documented conversion path explicitly requires one at
    the boundary.
2. **Value-object / factory form** — `CanonicalEmailContract(...)` or the
   `Email(...)` domain-type factory. `parse_contract` short-circuits on an
   already-parsed `CanonicalEmailContract` (mandate Law 5 — the contract
   is the truth), so calling `parse_contract(Email(...))` is a no-op
   identity.

Both forms resolve to the same `CanonicalEmailContract` value object that
the engine and capabilities consume. Future contract kinds follow the same
additive path: bump the contract `version` and add a new `register_contract`
branch. Money is intentionally absent from this list — it was reclassified as
a multi-field canonicalization (currency field + decimal field) and deferred
past the v2 RC; it is not a single `MoneyCapability` (mandate §5.5).

### `_errors/` (exceptions.py) — Error Hierarchy

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

## What Is Gone, and Why

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
| `src/paxman/executor/` (executor, field_runner, budget_tracker) | There is nothing to execute beyond the pipeline. The canonicalization step is one function call owned by `_core/engine.py`. |
| `src/paxman/budget.py`, `src/paxman/policy.py` | There is no budget. There is no policy. Determinism is unconditional (mandate Law 1). |
| `src/paxman/artifact/` (artifact, replay, _hash, statistics) | The artifact is the result. There is one canonical artifact schema, in `_core/artifact.py`, and it is immutable (mandate Law 13). |
| `tests/integration/`, `tests/property/`, `tests/unit/`, `tests/fixtures/`, `tests/public_api/`, `tests/benchmark/` | Tests are tests. The 5-layer test-data model is gone. Paxman has three directories. |
| `examples/` (3 mini-packages) | Legacy examples demonstrated broken behavior. Paxman has no examples; the README is the example. |
| `playground/` (Docker, Jupyter, notebooks) | Legacy notebooks demonstrated broken behavior. Paxman has no playground. |
| `docs/adr/` (11 ADRs) | The ADRs describe a legacy architecture that does not exist in Paxman. New ADRs, when warranted, must be evaluated against the laws (mandate §10.3). |
| `docs/` (legacy Diátaxis tree: `docs/reference/`, `docs/guides/`, `docs/superpowers/`, etc.) | The legacy docs described a different architecture. The current `docs/` tree (see `docs/index.md`) is the live documentation and is authoritative where it does not conflict with this document or the mandate. |
| `mkdocs.yml`, `.readthedocs.yaml` | The docs site build config is out of scope for this architecture document; the `docs/` tree is plain Markdown consumed by the project's doc tooling. |
| `scripts/` (`golden bootstrap`, `coverage check`, `fetch_test_data`, `benchmark_import_time`) | Scripts that are tied to legacy subsystems. The current `scripts/` directory holds only the static-analysis greps that enforce this architecture; the legacy bootstrap / fetch / benchmark scripts are gone. |
| `Makefile` (236 lines, 47 targets) | Paxman has no Makefile. `uv run` is enough. |
| `CHANGELOG.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `AGENTS.md` | Stub files that referenced the legacy project structure. Paxman has no equivalent stubs. When `CONTRIBUTING.md` returns, its first sentence must be the closing mandate of the mandate: *"Paxman would rather reject a value than silently canonicalize it incorrectly"* (mandate §10.4). |
| `pyrightconfig.json`, `pyrightconfig-strict.json` | The legacy project had a "pyright strict mode" initiative. Paxman has one pyright config when it is needed. |