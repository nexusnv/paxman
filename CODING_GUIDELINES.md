# Coding Guidelines

This document captures the engineering practices that this repository expects,
distilled from recurring code-review feedback and the project's constitutional
rules. It is written in a general voice so it stays useful regardless of which
change or pull request prompted a given lesson. Where the project's own
constitutional documents (`MANDATE.md`, `ARCHITECTURE.md`, `AGENTS.md`) are
authoritative, they win; this file is a practical summary, not a replacement.

## 1. Determinism and purity are the contract

Every capability is a pure function of `(value, contract)`. No I/O, no wall
clock, no filesystem, no network, no environment lookups, no randomness, and no
calendar-math imports inside the capability packages. If a transform needs to
read the current time or a timezone database, the design is wrong — move that
responsibility to the contract (a policy field) or to the caller.

A capability must be a fixed point of itself: canonicalizing an already
canonical value returns that value unchanged. Idempotence is not a nice-to-have;
it is an invariant the property suite enforces.

## 2. Follow RFCs and standards literally, then test the edge cases

When a feature is specified by an external standard (URI normalization, date
math, UUID formatting), implement the algorithm as written in the normative
text rather than a "good enough" reinterpretation. Segment-based shortcuts for
character-based algorithms frequently mishandle the empty-segment and
trailing-slash edge cases. The standard's pseudocode exists for a reason —
port it faithfully, then add regression tests for the exact cases the standard
calls out (empty segments, leading slashes, dot segments, trailing dots).

## 3. Validate inputs strictly and reject, never guess

Invalid input is an explicit outcome (`Status.INVALID` / `Status.UNSUPPORTED`),
not a guessed value and not a raised exception for a recoverable canonicalization
result. When validating authority/host/port forms:

- Reject malformed structured values (e.g. an IPv6 literal with more than the
  allowed number of colons, or a port outside `0..65535`).
- Accept values the standard permits even when they look unusual (a registered
  name may be digit-leading; an empty port is malformed and must be rejected
  rather than silently coerced away).
- Prefer a well-tested standard library validator over a hand-rolled regex for
  complex grammars such as IPv6.

The library would rather reject a value than silently canonicalize it
incorrectly.

## 4. Provenance is not optional

Every emitted evidence rule must cite its source. The rule-manifest maps each
rule name to a citation (an RFC section, the WHATWG standard, or an explicitly
declared policy). A rule that fires should correspond to an actual transformation
that changed the value — do not emit a "transformation happened" rule when
nothing changed. Dispatch-level invariants that are allowed to carry empty
provenance must be explicitly documented as an allow-list, not left implicit.

New code that touches a constitutional area should declare which mandate laws
it upholds. A short module-level comment identifying the relevant laws (for
example, determinism, never-guess, replay, provenance) is expected on
capability and contract modules and on their tests.

## 5. Type safety and tooling discipline

- `mypy` runs with `disallow_untyped_defs = true`. Every public function and
  method needs explicit parameter and return annotations. Do not widen the
  config or add suppression comments to satisfy it.
- Never suppress type errors with `as any`, `# type: ignore`, or `# noqa`. Use a
  `Protocol`, a `TypeAlias`, or a real annotation instead.
- `ruff` enforces line-length 100 and a curated rule set. Run `ruff format`
  before committing; do not apply `ruff check --fix` blindly — review every
  automatic edit.
- Value types are `attrs` frozen dataclasses. Immutability is load-bearing; the
  artifact is frozen and must stay that way.

## 6. Retired vocabulary

Certain words are retired by the project's vocabulary rules and must not appear
in code, comments, or documentation: `heuristic`, `confidence`, `best match`,
`probably`, `approximate`. Their adopted replacements are `resolver`,
`dispatcher`, `registry`, `matcher`, `capability resolution`, `matching rule`.
A CI script fails the build if any retired word appears in the source tree.

## 7. Tests are the evidence, not an afterthought

- Three test directories only: `unit/`, `property/`, `integration/`. Do not
  create new test directories.
- Property tests must use Hypothesis and carry the `property` marker. They are
  the mechanical evidence for the core invariants (replay byte-equality,
  idempotence, artifact immutability, canonicalization determinism, and the
  uniqueness/ambiguity rule). Plain (non-Hypothesis) assertions about built-in
  behavior belong in the unit suite, not the property suite.
- Name property tests so their invariant is obvious
  (`test_replay_invariant`, `test_idempotence_invariant`, and so on). Flag any
  change that drops or weakens a required invariant test.
- The coverage gate is **per subpackage**, not global: each `_*` package under
  the source tree must stay at or above 90% line coverage. New code ships with
  tests that keep its package green. Deleting or weakening a failing test to
  make the suite pass is never acceptable.
- Do not derive test expectations from the very table or constant under test —
  use explicit literals so a change to the table cannot silently pass the test.

## 8. Documentation accuracy

Architecture and capability documentation must match the shipped code. When a
new built-in or package is added, update every directory tree and enumeration
that claims to list the built-ins, and keep tree connectors (the `├──` / `└──`
markers) correct so the final child is actually last. Do not reference
documents that do not exist in the repository. Keep configuration files (such as
review or CI configuration) synchronized with the actual job names and counts
they describe.

## 9. Keep changes minimal and review your own work

Fix what the review identifies as valid; skip findings that no longer apply and
state why briefly. Do not bundle unrelated refactors into a targeted fix. Before
claiming a change is complete, run the lint, type-check, and test gates the CI
runs, and confirm the relevant coverage gate still passes.
