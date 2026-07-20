# Paxman — Product Requirements Document

*Written as if on day zero. Informed by where Paxman is heading.*

---

## 1. Vision

The world is full of data that means the same thing but looks different. The same
email address is written with mixed casing, with surrounding whitespace, with
comments appended. The same calendar date appears as `07/20/2026`, as
`2026-07-20`, as `20 Jul 2026`, as a Unix timestamp. The same monetary amount is
written with a currency symbol, with a three-letter code, with or without
thousands separators.

Every system that receives this data has to decide: *which form is the right
form?* Today that decision is re-litigated inside every application, every
pipeline, every integration. Each team writes its own normalization. Each team
makes subtly different choices. The result is drift: two systems that should
agree do not, and nobody can say which one is correct.

Paxman exists to end that drift.

**Paxman is a deterministic canonicalization engine.** It takes information that
is *known* to be equivalent and rewrites it into a single, agreed canonical
form — and it refuses to guess when the input does not determine a unique
result. Where other tools *interpret*, Paxman *canonicalizes*. It does not
infer meaning that is not present. It does not orchestrate. It does not
improvise. It makes the known known, consistently, forever.

---

## 2. The Promise

Paxman promises three things to everyone who depends on it:

1. **One form, agreed by all.** Feed Paxman the same logical input from two
   different starting shapes, and it will produce the exact same canonical
   output every time, everywhere.

2. **No silent guessing.** When the input is ambiguous — when more than one
   canonical reading is possible — Paxman says so explicitly rather than
   picking one and hoping. Refusing is a feature, not a failure.

3. **Perfect recall.** Any canonical artifact Paxman produces can be replayed
   back into Paxman and reproduced byte-for-byte, with no re-execution and no
   loss. The artifact is self-describing and trustworthy on its own.

Paxman is not a parser. It is not a formatter. It is not a general-purpose
transformation library. It is the single, principled authority for *"given
this kind of known information, what is the one right shape it should take?"*

---

## 3. The Three Invariants

These invariants are not features. They are the constitution. Every decision,
every line, every extension to Paxman must preserve them. If a change breaks an
invariant, the change is wrong, no matter how convenient.

### Invariant 1 — Identity

Paxman canonicalizes only. It never interprets beyond what the input and its
contract jointly determine. It never infers information that is not already
present. It never orchestrates, decides business meaning, or invents structure.
The boundary of what Paxman does is *rewrite the known into the agreed shape.*

### Invariant 2 — Determinism

For a given input, contract, set of registered capabilities, and configuration —
Paxman always produces the same artifact. There is no randomness, no clock
dependence, no hidden state, no environment leakage. Same in, same out, on any
machine, on any day. Determinism is a property of the library itself, not an
option you opt into.

### Invariant 3 — Replay

Every artifact Paxman emits can be handed back to Paxman and reconstructed
exactly, without re-running any logic. The artifact carries everything needed to
reproduce itself. Replay is not a reconstruction from memory; it is a faithful,
byte-for-byte return to the original.

---

## 4. Who Paxman Is For

Paxman serves three audiences, and the design honors all three.

- **Users** — engineers and systems that need a trustworthy, repeatable
  canonical form for known kinds of data, without building that logic
  themselves.
- **Extenders** — contributors who want to teach Paxman a new *kind* of known
  information (a new domain of canonicalization).
- **Forks** — teams who want to take Paxman and build a purpose-specific variant
  under their own direction, without fighting the architecture to do so.

A good architecture is one that serves the user, welcomes the extender, and
frees the forker. Paxman is built so that all three are first-class.

---

## 5. Proposed Architectural Design

Paxman is deliberately small at its core and deliberately open at its edges. The
design separates *what is fixed* from *what is extensible* so sharply that each
side can evolve without disturbing the other.

### 5.1 The Engine (fixed, owned, sealed)

At the center sits the engine. If Paxman were a courtroom, the engine would be
the bench: it never argues a case, it never invents the law, and it never
whispers to one side. It receives what is brought before it, confirms the law
applies, asks the right specialist to render a verdict, records that verdict
word-for-word, and can read the verdict back verbatim years later. The engine is
the unchanging frame inside which all change is permitted.

We spent many cycles refactoring to find the engine's true shape, and the
aspired sweet spot looks like this.

**The engine is a pure, stateless referee.** It holds no opinion about email or
dates or money. It holds only the rules of engagement. Given an input and a
contract, it performs a fixed sequence of moves, and that sequence is the entire
job of Paxman:

1. **Receive.** Take the raw input and the contract that names its kind.
2. **Resolve.** Ask the registry, deterministically, which single capability
   has declared that it owns this contract. There is no scoring, no ranking, no
   "best match" — exactly one capability claims it, or the engine reports that
   none does.
3. **Delegate.** Hand the input and contract to that capability and receive back
   a structured verdict: either a canonical form with the evidence that produced
   it, or an explicit refusal with the reason why no unique form exists.
4. **Seal.** Wrap the verdict, the contract, and the authority choices into a
   self-describing artifact — a record that needs nothing outside itself to be
   understood or replayed.
5. **Replay.** Given that artifact and the same contract, reproduce it exactly,
   without ever re-invoking the capability. Replay is reading the sealed record,
   not re-running the trial.

What makes this the sweet spot is not any single move but the *discipline of the
frame*. The engine is intentionally boring. It contains no branching that
depends on which domain is being canonicalized. It knows nothing about casing,
time zones, or currency. All of that lives elsewhere, behind the one door. This
is why the engine can be sealed: there is nothing inside it worth forking, and
nothing inside it that could drift. The invariants — Identity, Determinism,
Replay — are not sprinkled across the system; they are *concentrated* in this
one component, and concentration is what makes them provable.

The engine is **owned by Paxman**. Contributors do not rewrite the pipeline.
They do not redefine how verdicts are rendered or how artifacts are sealed. This
is not a limitation — it is the guarantee. Because the frame is sealed, every
extension that plugs into it inherits the three invariants for free, and a
broken extension cannot quietly corrupt the constitution.

### 5.2 Contracts (the shared language)

A *contract* is the agreement between caller and engine. It names the kind of
information being canonicalized and may pin specific authoritative choices
(Editions). Contracts are declarative and versioned. They are how a caller says
*"I am giving you a date; here is the authority I trust"* without writing any
logic.

Contracts keep the public surface stable and predictable. A caller learns the
contract once and can canonicalize any supported kind of information the same
way.

### 5.3 Capabilities (the only extension point)

Everything Paxman *knows how to canonicalize* lives behind a single, uniform
interface: a **capability**. The capability is the specialist the engine calls
to the stand — the only place where real domain knowledge is allowed to live. If
the engine is the bench, the capability is the expert witness: it knows
everything about its one subject and nothing about the others.

After many refactors, the aspired shape of a capability is small, honest, and
complete. A capability does exactly two things and nothing more.

**First, it declares what it owns.** A capability answers, for any contract put
before it: *"Is this mine?"* This is a clean, deterministic claim — not a
confidence score, not a heuristic. In the registry, capability claims do not
overlap; the engine's resolve step is a lookup, not a negotiation. A capability
owns a contract kind, and it owns it wholly.

**Second, it renders a verdict.** Given an input and the contract it owns, the
capability returns one of two outcomes, and the duality is the soul of Paxman:

- A **canonical verdict** — the single agreed form, accompanied by *evidence*:
  the named rules that fired, the order they fired in, and the authority whose
  standard was applied. Evidence is not decoration. It is the receipt. It is what
  lets a reader (human or machine) trust the verdict and what lets replay
  reconstruct it without re-running the reasoning.
- A **refusal** — an explicit, reasoned statement that the input does not
  determine a unique form. The capability does not guess, does not fall back to
  a "probably," does not pass the buck. It says *why* it cannot decide, and it
  stops. Refusal is a first-class result, stored in the artifact exactly like a
  success, because refusing correctly is as much a part of the promise as
  succeeding.

The capability never reaches outside itself for the answer. It does not call a
service, consult a clock, or read ambient state. Its output depends only on the
input and the contract. That is what makes its verdict *deterministic* and its
evidence *sufficient* — given the same two things, it always returns the same
verdict with the same evidence, and the evidence is enough to reproduce it.

Capabilities are organized one package per domain. Paxman today understands
several foundational domains — email, date, unique identifiers, and more — and
the shape of each capability package is identical. Adding a new domain means
copying that shape, not inventing a new architecture.

This is the heart of Paxman's extensibility: **the only thing you are allowed to
add is a capability, and the path for adding one is already paved.** There is no
secret hook, no special-case escape hatch, no fork-the-core requirement. The
capability is the whole game for an extender — and because the engine is sealed,
the extender cannot accidentally break the constitution while playing it.

### 5.4 The Registry (safe by construction)

Capabilities are registered before the engine runs. Once the engine begins its
work, the set of capabilities is frozen. This prevents the silent, order-
dependent behavior that plagues extensible systems: you cannot register a
capability mid-flight and change the outcome of an in-progress run. Freezing
makes determinism observable and enforceable rather than hoped-for.

### 5.5 Authoritative Editions

Different authorities publish different canonical forms for the same domain.
Paxman models this explicitly through *editions* — named, selectable versions of
an authority. A caller can rely on the active default, or pin a specific edition
for a single call, or pin editions across an entire engine. This lets Paxman
honor real-world authority without hardcoding a single worldview, and it keeps
canonicalization both configurable and reproducible.

---

## 6. Why This Architecture Is Clean

The architecture earns its cleanliness from a small number of deliberate
choices:

- **One sealed core, one open edge.** The invariant-protecting logic lives in
  exactly one place. Everything else plugs in through one well-lit door.
- **Uniform extension shape.** Every capability looks the same. There is one
  pattern to learn, not seventeen.
- **No hidden behavior.** Freezing, determinism, and replay are enforced by
  structure, not by convention or documentation alone.
- **Declarative contracts.** Callers describe *what* they want canonicalized;
  they never write *how*. The how lives with the capability author.
- **Self-describing artifacts.** Output carries its own provenance and can be
  replayed without external context.

The result is an architecture a newcomer can hold in their head: engine in the
middle, contracts in, capabilities around the edge, registry keeping order,
artifacts coming out the other side fully described.

---

## 7. Why This Architecture Is Easy to Extend

For a contributor adding a new domain:

- Mirror an existing capability package. The file layout, the interface, and the
  contract shape are already established.
- Implement the two questions every capability must answer. Nothing else is
  required.
- Register the capability before the engine runs. The system handles the rest.

There is no need to understand the engine internals. There is no need to modify
shared code. There is no risk of accidentally breaking another domain, because
capabilities are isolated by contract. The blast radius of a new contribution is
exactly one package.

For a user consuming Paxman:

- Learn the contract model once.
- Call the canonical entry point.
- Receive an artifact that is trustworthy and replayable.

The mental model does not grow with the number of supported domains.

---

## 8. Why This Architecture Is Easy to Fork

Paxman is built to be taken. A team that wants a variant — a stricter policy, a
different set of domains, a domain-specific authority — can fork and reshape
without wrestling the core:

- The engine stays intact and continues to guarantee the invariants.
- New or replaced capabilities slot in through the same door every other
  capability uses.
- Contracts and editions let a fork express its own authoritative choices
  without forking the pipeline.
- The sealed core means a fork cannot easily drift into non-deterministic or
  non-replayable territory even by accident.

In other words, forking Paxman gives you a *hardened foundation* rather than a
*starting scramble*. You inherit correctness; you spend your effort on scope.

---

## 9. What Paxman Deliberately Is Not

To protect the invariants and the promise, Paxman refuses certain roles:

- It is not an inference engine. It will not decide what an ambiguous input
  "probably" means.
- It is not a general transformation or ETL framework.
- It is not a network or I/O service. Determinism forbids hidden external
  dependence.
- It is not a business-rules engine. Canonical form is about shape and
  authority, not about what you should *do* with the data.

Saying no here is what keeps Paxman trustworthy.

---

## 10. Success Looks Like

- A caller canonicalizes the same logical input from any of its equivalent
  shapes and receives an identical artifact.
- An ambiguous input produces an explicit "I will not guess" result, with clear
  reason, rather than a silent wrong answer.
- Any artifact replays to itself exactly, with no re-execution.
- A new contributor ships a new domain by mirroring one existing package and
  registering it — without touching the engine.
- A fork ships a purpose-built variant on the same sealed, invariant-protecting
  core.

---

## 11. Closing

Paxman starts, on day zero, with a clear promise and an uncompromising
constitution. The architecture is small where it must be firm and open where it
must grow. It serves the user who wants a trustworthy answer, the contributor
who wants to teach it something new, and the team who wants to take it somewhere
Paxman's authors never imagined — all without sacrificing the one thing that
makes Paxman matter: you can always trust the output, and you can always
reproduce it.
