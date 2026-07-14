# The Mandate of Paxman

> **Status:** Mandate. This document is the constitutional boundary of Paxman.
> No future contributor — including the original author — may violate the laws
> recorded here. Every architectural decision, every pull request, and every
> new abstraction is evaluated against the principles in this document.
>
> **Supersedes:** the v1.x "contract-driven normalization" framing recorded in
> [`.sisyphus/introduction-to-paxman.md`](./.sisyphus/introduction-to-paxman.md).
> That document describes a system that was retracted on 2026-07-12; see
> [`RETRACTION.md`](./RETRACTION.md) and the audit in
> [`.agents/PAXMAN-BRUTAL-HONESTY-POSTMORTEM.md`](./.agents/PAXMAN-BRUTAL-HONESTY-POSTMORTEM.md).
>
> **Authoritative for:** v2 and all subsequent releases. Where this document
> conflicts with `README.md`, [`PROPOSED_STRUCTURE.md`](./PROPOSED_STRUCTURE.md),
> an ADR, or any other document, this document wins.

---

## 1. The Identity

**Paxman is a deterministic canonicalization engine.**

It transforms equivalent representations of *known* information into a single
canonical form. When the input does not contain enough information to
determine a unique result, Paxman reports that fact rather than guessing.

The project's v1.x drift was caused by leaving the boundaries implicit. They
are now explicit.

### 1.1 What Paxman is not

| Paxman is **not**… | …because |
|---|---|
| a **normalizer** | "Normalization" is a wider, fuzzier category that admits heuristic rules, scoring, and interpretation. Paxman does not interpret. It canonicalizes — it rewrites equivalent representations of *known* information into one chosen form. Normalization can guess; canonicalization cannot. |
| a **deterministic parser** | A parser maps text → structured value against a grammar. Paxman's job is broader on the input side (any representation of known information, not just text) and narrower on the output side (a single canonical form, not a parsed AST). Calling Paxman a parser mis-sets the expectation that the input must be a string and the output must be a syntax tree. |
| a **workflow engine** / **DAG orchestrator** | A user-defined pipeline places control flow in the caller's hands. Once you allow that, Paxman stops being a deterministic canonicalization engine and becomes a general-purpose workflow framework — it would re-create part of LangChain, Haystack, or a DAG orchestrator. See §4. |
| an **AI / extraction system** | v1.x drifted because it quietly adopted the mindset of an AI system: *"How do I maximize successful extraction?"* The mindset of a deterministic canonicalization engine is the opposite: *"How do I ensure that every successful canonicalization is unquestionably correct?"* See §7. |

If a contributor proposes any abstraction that turns Paxman into one of the
four above, the answer is no, and Law 11 is the rule that enforces it.

### 1.2 The Three Invariants

Paxman rests on exactly three invariants. Every law in §7 derives from at
least one of them. Every proposed change must be evaluated against all three.

#### Identity invariant

> Paxman only canonicalizes.
>
> It never interprets.
> It never infers.
> It never orchestrates.

This is what keeps Paxman out of AI territory forever. Law 3 (Canonicalize,
Don't Interpret) and Law 5 (Paxman Owns the Algorithm) are formalisations of
this invariant.

#### Determinism invariant

> The same `input`, `contract`, `capabilities`, `configuration`, and
> Paxman `version` always produce the same artifact.

Note the inclusion of **capabilities**, **configuration**, and **version**.
All three become part of replayability. Anything not fixed cannot be part of
deterministic execution. Law 1 (Determinism Above All) and Law 2 (Never
Guess) are formalisations of this invariant.

#### Replay invariant

> Every artifact is independently verifiable: `replay(artifact, contract)
> == artifact` byte-for-byte, *without re-executing capabilities*.

This property is unusual. Most libraries cannot promise it. Paxman can,
because every input to canonicalization is explicitly versioned and recorded.
The replay property is not a convenience feature; it is one of the three
pillars of the project's credibility. Law 12 (Replayability is a First-Class
Invariant) elevates this to a law.

### 1.3 Glossary

The following terms have one meaning in Paxman. A contributor who uses any
of them in a different sense in code, comment, docstring, or ADR is wrong.

| Term | Definition |
|---|---|
| **canonical form** | A single, chosen representation selected from a set of semantically equivalent representations. Defined formally in §2. |
| **canonicalization** | The act of producing a canonical form from an input. Defined formally in §2. |
| **contract** | A value (the v2 starter format is the Dict DSL) that declares *what* the canonical form must be for an input. It is the source of truth (Law 4). The contract never declares *how* to produce it. |
| **capability** | A pure, deterministic transformation that answers one question: *"Can I canonicalize this value, given this contract?"* and, if yes, produces a `CapabilityResult`. Capabilities do not orchestrate (Law 5, Law 8). |
| **resolver** / **dispatcher** | The component that, given `(contract, value)`, finds the capability (or capabilities) that explicitly declare they canonicalize it. Resolution is a deterministic lookup, never a guess (§6). |
| **registry** | The container that holds registered capabilities and answers `resolve(contract, value)`. It is a data structure, not a strategist. |
| **matching rule** | A deterministic predicate ("regex A matches → dispatch to ISO parser") used by the resolver. This is distinct from a *heuristic* in the soft sense (§3.2, §6.4). |
| **ExecutionArtifact** | The immutable return value of `canonicalize`. Carries the canonical value (on success) and the evidence of how it was produced. Immutability is mandated by Law 13. |
| **Status** | An enum value on every `ExecutionArtifact`: `Canonicalized`, `Invalid`, `Missing`, `Ambiguous`, `Unsupported`. Status values are *outcomes*, not exceptions (Law 7). |
| **evidence** | A structured record on the artifact of *what matched and why* — which capability ran, which rule fired, which checksum passed. Evidence replaces confidence scores (Law 9) and carries each rule's Law 14 provenance citation. |
| **capability result** | The internal value a capability returns from `canonicalize(value, contract)`. Carries the canonical value or a `Status` other than `Canonicalized`. |
| **Paxman version** | The version string of the library itself. Part of the determinism and replay invariants. |
| **contract version** | A version attached to a contract. Contracts evolve; replay across contract versions is governed by §"Decisions left to make." |

---

## 2. Canonicalization, defined formally

Ironically, the most important word in this document lacked a definition in
the first draft. It has one now.

> **Canonicalization** is the selection of exactly one representation from a
> set of semantically equivalent representations. The mapping
>
> ```
> canonicalize : Input × Contract → CanonicalValue
> ```
>
> must be:
>
> 1. **Deterministic.** Same input, contract, capabilities, configuration,
>    and Paxman version → same output. (Law 1.)
> 2. **Total on supported inputs.** For every `(input, contract)` pair that
>    any registered capability declares it can handle, `canonicalize` returns
>    an artifact. It may return `Status.Ambiguous` or `Status.Invalid`, but
>    it does not raise an exception on a supported pair.
> 3. **Idempotent.**
>    ```
>    canonicalize(canonicalize(x)) == canonicalize(x)
>    ```
>    Re-canonicalizing a canonical value yields the same value. Law 2 of
>    mathematics is also a law of Paxman: idempotence is required, not
>    optional.
> 4. **Totality-preserving on rejection.** When `canonicalize` cannot
>    produce a unique canonical value, it returns an artifact with a
>    `Status` other than `Canonicalized` — it never silently picks one. This
>    is the operational form of Law 3.

The idempotence property is surprisingly valuable. It:

- Eliminates an entire class of bugs where re-running canonicalization on
  already-canonical data drifts.
- Guarantees that storing an artifact and replaying it is byte-equivalent to
  re-canonicalizing the canonical value.
- Makes the pipeline compositional: capabilities can be applied in any order
  to canonical inputs and the result is stable.

Idempotence is now Law 2 (below), elevated from a property of the math to a
law of the project.

---

## 3. The Three Conflated Concepts

The conversation that motivated this reboot identified three things that v1.x
conflated. Naming them is the first defense against repeating the drift.

### 3.1 Deterministic algorithm — ✅ allowed

Every execution produces the same result. Same input, same contract, same
capabilities, same configuration, same Paxman version → same output.

### 3.2 Heuristic ranking — ⚠ allowed only when the heuristic is a rule

A heuristic *can* be perfectly deterministic:

> If the string contains `@` and exactly one `.`, try `EmailParser`.

That is a heuristic. It is also a deterministic dispatch rule (a *matching
rule*; see §1.3). Same input, same parser, same output.

The danger is **not** heuristics. The danger is heuristics that encode
**opinion** instead of rules:

> Try the parser with the highest confidence.

Now you have introduced a hidden scoring model. Where did `0.8` come from? Can
it change? Why `0.8` and not `0.75`? Once subjective judgment enters the
dispatch, determinism has been silently forfeited.

### 3.3 Probabilistic inference — ❌ never

Anything that selects behavior based on estimated likelihood belongs outside
Paxman. This includes confidence scores, "best match" algorithms, probability
thresholds, model rankings, "most likely parser" logic, AI inference, and
fuzzy ranking. Law 3 forbids this; §"Law 3 — Never Guess" lists what it
immediately forbids.

---

## 4. Capabilities vs. Pipeline — the Central Distinction

This is the single decision that, if reversed, would turn Paxman into
something else.

### 4.1 Capabilities are orthogonal

A capability is one deterministic transformation that answers one question:
*"Can I canonicalize this value, given this contract?"* Examples of the kind
of capability the v2 SPI should admit:

```
DateParser   MoneyParser   EmailParser   PhoneNumberParser
UUIDParser   URLParser     BooleanParser
MalaysianICParser          USNPCCodeParser
SAPMaterialCodeParser      HospitalMRNParser
MyCompanyProductCodeParser
```

Each one is an independent, composable, deterministic transformation. Users
can contribute new capabilities. That is the **only** extension point.

### 4.2 The pipeline belongs to Paxman

A user-defined pipeline (`OCR → LLM → Regex → DateParser → MoneyParser →
Another LLM → Webhook → …`) is *not* Paxman. That is a workflow engine. The
point was blunt:

> Is that still Paxman? I don't think it is. That's a workflow engine.
> You've accidentally recreated part of LangChain, Haystack, or a DAG orchestrator.

The pipeline is part of Paxman's promise. Paxman owns:

```
Input
  ↓
Contract inspection
  ↓
Capability discovery
  ↓
Capability execution
  ↓
Validation
  ↓
Canonicalization
  ↓
Classification
  ↓
ExecutionArtifact
```

Users may plug new capabilities into **Capability execution**, but they
cannot rearrange the pipeline. The pipeline embodies Paxman's deterministic
contract.

### 4.3 The Python analogy

Python's `json.loads()` lets you provide custom decoders. It does not let
you redefine the JSON parser pipeline. Likewise, `datetime.strptime()` lets
you supply a format string, not rewrite how datetime parsing works.

> The extensibility point is the knowledge, not the control flow.

---

## 5. The SPI Rule

### 5.1 What a capability is allowed to do

A capability transforms. It does not orchestrate. The SPI a capability
implements is, in its narrowest form:

```python
class Capability(Protocol):
    name: str
    def can_handle(self, contract, value) -> bool: ...
    def canonicalize(self, value, contract) -> CapabilityResult: ...
```

Or whatever shape v2 settles on — but the shape must forbid control-flow
verbs. **Absent from the SPI:**

- `next()`
- `execute()`
- `pipeline`
- `stage`
- `context switching`
- `branching`

A capability doesn't orchestrate. It transforms.

### 5.2 The SPI litmus test

Every proposed SPI must answer this question:

> Can two independent implementations produce different outputs for the same
> input while still claiming to implement the Paxman SPI correctly?

**If yes → the SPI is too vague.** Reject it.

**If no → the SPI is probably a good deterministic abstraction.**

For example, an SPI of `CanonicalDate.parse("2025-01-01")` is good: every
compliant implementation must produce exactly the same canonical date. An SPI
of `infer_vendor_name(text)` is bad: one implementation chooses `"ABC Ltd"`,
another chooses `"ABC Holdings"`, both followed the interface. The abstraction
itself was not deterministic.

### 5.3 What users may and may not extend

> Users should be able to teach Paxman new facts, but they should not be able
> to redefine how Paxman thinks.

- ✅ New capabilities, new parsers, new validators, new canonicalizers —
  teaching Paxman new deterministic *knowledge*.
- ❌ User-defined pipelines, custom execution graphs, branching workflows,
  orchestration — redefining how Paxman *thinks*.

Once you allow the second, Paxman stops being a deterministic canonicalization
engine and starts becoming a general-purpose workflow framework.

### 5.4 Capability resolution uniqueness

A stronger form of the §5.2 litmus, elevated to a principle:

> Every supported `(contract, value)` pair must resolve to **at most one**
> capability.

If two capabilities both return `can_handle() == True` for the same pair,
the orchestrator classifies the outcome as `Status.Ambiguous` (Law 3) rather
than picking one — but the *principle* is uniqueness. A contract/value pair
that has a canonical answer has exactly one capability that produces it. A
pair that has more than one candidate capability has, by construction, no
unambiguous canonical answer and is reported as `Ambiguous`.

This invariant is enforced by Law 5 (the orchestrator never silently picks)
and recorded on the artifact as evidence (Law 9 — *"two capabilities claimed
this pair; classified Ambiguous"*).

---

## 6. The Algorithm — Resolver, not Planner

### 6.1 Why "planner" was retired

v1.x invested heavily in a "planner." After this reboot, that name is retired.
"Planner" implies intelligence and strategy. What Paxman actually does is
**resolve**:

```
Contract  →  Capability Resolution  →  Execution
```

The system is not deciding *what seems best*. It is *discovering* which
capability explicitly declares that it canonicalizes this contract. That is a
deterministic lookup.

### 6.2 The compiler analogy

A compiler does not say *"I heuristically think this is an integer."* It
knows. Because the grammar says so. Likewise, Paxman should not ask *"Who has
the highest confidence?"* It asks *"Which capability explicitly declares
that it canonicalizes this contract?"* — a deterministic lookup.

### 6.3 Vocabulary to retire, vocabulary to adopt

Words matter. People hear `heuristic` and think *approximate, best effort,
probably, confidence*. Those words do not belong in Paxman.

**Retire:**

- heuristic
- approximate
- best effort
- probably
- confidence

**Adopt:**

- resolver
- dispatcher
- registry
- matcher
- capability resolution

The adopted words imply deterministic *selection*. The retired words imply
probabilistic *guessing*.

### 6.4 The one place a "heuristic" may still belong

If the contract is `CanonicalDate()` and Paxman ships `ISODateCapability`,
`USDateCapability`, `RFC2822Capability`, and `UnixTimestampCapability`, how
does Paxman choose? A matching rule might say: *"Regex A matches → dispatch
to ISO parser."* That is fine — because the regex itself is deterministic. It
is a *matching rule*, not a heuristic in the soft sense. The position taken
here is: *I'd almost stop calling that a heuristic. It's a matching rule.*

---

## 7. The Constitution — Fourteen Laws

These are the laws. No PR may violate any of them. Law 11 (Abstraction
Preserves Determinism), Law 13 (Artifact Immutability), and Law 14
(Canonical Forms Have Provenance) are the filters that enforce all
the others.

### Law 1 — Determinism Above All

> The same `input`, `contract`, `registered capabilities`, `configuration`,
> and Paxman `version` must always produce the same `ExecutionArtifact`.

Note the inclusion of **capabilities**, **configuration**, and **version**.
All three become part of replayability. Anything not fixed cannot be part of
deterministic execution.

### Law 2 — Idempotence

> For every supported input, `canonicalize(canonicalize(x)) == canonicalize(x)`.

Re-canonicalizing a canonical value yields the same value. This eliminates
an entire class of bugs where re-running canonicalization on
already-canonical data drifts. It also makes `replay(byte_equal)` trivial to
reason about: the canonical value is a fixed point of `canonicalize`.

### Law 3 — Never Guess

> Paxman never selects behavior based on estimated likelihood. Every
> execution path must be chosen through explicit, deterministic rules derived
> from the contract, the input, or registered capabilities.

This immediately forbids:

- ❌ Confidence thresholds
- ❌ "Best match" algorithms
- ❌ Probability thresholds
- ❌ Model rankings
- ❌ "Most likely parser"
- ❌ AI inference
- ❌ Fuzzy ranking

This allows:

- ✅ Exact capability registration
- ✅ Exact type matching
- ✅ Declarative matching rules
- ✅ Deterministic parser selection
- ✅ Rule-based fallback, when the rule itself is explicit and reproducible

### Law 4 — Canonicalize, Don't Interpret

> Paxman transforms representations of known information. It does not infer
> unknown information.

If multiple canonical values are possible, Paxman must report ambiguity
(`Status.Ambiguous`) rather than choose one.

#### Allowed

- `"RM100"` → `"MYR 100"`
- `"100 MYR"` → `"MYR 100"`

These are different representations of the **same known** value; Paxman
rewrites them into the chosen canonical form.

#### Not allowed

- `"Apple"` → `"Fruit"` — that's interpretation, not canonicalization.
- `"03/04/2025"` → `"2025-03-04"` — not allowed **unless** the locale is
  known; otherwise the value admits two canonical readings and Paxman must
  report ambiguity.

This single law keeps Paxman out of AI territory forever.

### Law 5 — Contract is Truth — and Contracts Specify *What*, Not *How*

> The contract defines what canonical means.

Not the input. Not the capability. The contract.

The contract defines the **destination**, not the **algorithm**. A contract
that says `Date` declares *what* the canonical form is; it never authorises
the use of GPT to infer it. If a future contributor argues "the contract says
`Date`, therefore I'll use GPT to infer it," that argument is forbidden by
this law — not by Law 3 alone, but by the explicit separation of *what* from
*how*.

Without a contract, Paxman has no work to do. Capabilities don't invent
meaning; they satisfy contracts.

### Law 6 — Paxman Owns the Algorithm

> Users may extend Paxman with deterministic capabilities. Users may not
> redefine Paxman's execution model.

This protects Paxman from becoming another workflow framework.
Non-negotiable.

### Law 7 — Explicit Over Clever

> Whenever two implementations are possible, Paxman prefers the one that is
> easier to reason about over the one that is more automatic.

#### Good

- `CanonicalDate(locale="MY")` — explicit, reproducible.
- `Money(currency="MYR")` — explicit, reproducible.

#### Bad

- `CanonicalDate(auto_detect=True)` — asks the system to figure it out.
- `Money()` — hopes the system picks the right currency.

### Law 8 — Fail Informatively

> Paxman should always know why. Every failure is deterministic too.

Instead of returning a bare `failed`, Paxman classifies the failure into a
`Status`:

- `Invalid` — the input cannot satisfy the contract.
- `Missing` — the contract requires a field the input does not provide.
- `Ambiguous` — Law 4: the input admits more than one canonical reading.
- `Unsupported` — the contract's shape is recognized but no registered
  capability declares that it canonicalizes it.

A successfully-returned artifact with a non-`Canonicalized` `Status` is not
an exception; it is a deterministic outcome. Exceptions are reserved for
calls that *cannot proceed at all* (broken contract, version mismatch,
internal invariant violation) and are governed by `PROPOSED_STRUCTURE.md`'s
`_errors.py` hierarchy.

### Law 8a — Capabilities Depend Only On Replayable Inputs

The earlier draft of this law read *"capabilities cannot perform HTTP,
database access, filesystem access, etc."* That formulation bans
*technologies*. It mis-classifies determinism.

> A capability may only depend on inputs that are **explicitly versioned and
> participate in replay**.

The real enemy is not HTTP. The real enemy is **hidden mutable state**. A
capability that does:

```
GET https://iso3166.example/countries
```

is deterministic if the dataset is versioned, immutable, and that version is
recorded on the artifact (so replay re-fetches the same bytes). A capability
that does an `SQLite` lookup is deterministic if the database is bundled with
Paxman and its content version is part of the artifact'sevidence. A
capability that reads `time.now()` is *not* deterministic — `time.now()` is
hidden mutable state that is not versioned and not replayable.

The principle generalises:

- ❌ Anything that reads state the caller did not supply and did not version.
- ❌ Anything that returns different bytes on a second call with the same
  inputs.
- ✅ Pure functions of `(value, contract)`.
- ✅ Lookups into a bundled, versioned dataset, where the dataset's version is
  recorded on the artifact'sevidence.

This law makes Law 1 and the replay invariant jointly enforceable. A
capability that depends on un-versioned state breaks both — even if it never
makes a network call.

### Law 9 — Evidence Over Confidence

> Paxman records what matched and why, not how confident it is.

#### Not this

- `Confidence: 0.91`

#### This

- `Resolved because: ISO8601 parser matched.`
- `Regex X matched.`
- `Checksum valid.`
- `Two capabilities claimed this pair; classified Ambiguous.`

That's evidence, not opinion.

### Law 10 — One Responsibility

> Paxman is a canonicalization engine.

Not OCR. Not ETL. Not AI. Not workflow. Not storage. Not orchestration.

Every feature request should answer one question:

> Does this help deterministic canonicalization?

If not, it belongs elsewhere.

### Law 11 — Every Abstraction Must Preserve Determinism

> Every new abstraction — capability, resolver, matcher, dispatcher, parser,
> validator — is run through the same filter:
>
> 1. Can two independent implementations of this abstraction produce different
>    results for the same input? → If yes, reject.
> 2. Can it ever guess? → If yes, reject.
> 3. Can score ordering change between runs? → If yes, reject.

This law becomes a filter for **every pull request**. It is the law that would
have saved v1.x.

### Law 12 — Replayability is a First-Class Invariant

> For every artifact produced by `canonicalize`, `replay(artifact, contract)
> == artifact` byte-for-byte, without re-executing capabilities.

This is the replay invariant from §1.2 elevated to a law. Most libraries
cannot make this promise; Paxman can, because every input to canonicalization
is explicitly versioned and recorded on the artifact.

Replay is not a convenience feature. It is one of the three pillars of the
project's credibility, alongside identity and determinism. Violating it — by,
for example, introducing a capability that depends on un-versioned state
(Law 8a) — is grounds for rejecting the PR.

### Law 13 — ExecutionArtifact Is Immutable

> An `ExecutionArtifact`, once produced, is never mutated in place.

Mutation would break the replay invariant (Law 12): a caller that does
`artifact.status = SUCCESS` after the fact produces an artifact whose
`replay_hash` no longer matches its content. The artifact is a value, not a
box. To "modify" an artifact is to produce a new artifact via a new
`canonicalize` call.

This applies to every field on the artifact: the canonical value, the
`Status`, the evidence list, the `replay_hash`, the version stamps. None
of them may be reassigned after construction.

### Law 14 — Canonical Forms Have Provenance

> Paxman does not invent canonical forms. Every normalization rule that a
> capability applies must derive its canonical form from one of exactly
> three sources, recorded as provenance:
>
> 1. **An authoritative specification** — cited by document and section
>    (e.g., RFC 5321 §2.4, ISO 4217, RFC 4122).
> 2. **Documented platform behavior** — cited by vendor document title,
>    version, and retrieval date (e.g., Google Help: "Use aliases on your
>    Account," retrieved 2026-07-14).
> 3. **An explicitly declared Paxman policy** — cited by a Paxman document
>    that records the decision (MANDATE.md section, an ADR, or the
>    capability's published spec under `docs/superpowers/specs/`).
>
> A rule with no provenance citation is, by construction, a rule without
> an authority — which is precisely what Law 4 (Canonicalize, Don't
> Interpret) forbids. Provenance is what makes the difference between
> "Paxman applied a spec" and "Paxman invented a rewrite."

#### What "rule" means here

A *rule* is any code path inside a capability that, when it fires,
contributes to the canonical value or to an evidence entry that records
*why the canonical value is what it is*. Rejection paths
(`Status.Invalid`, `Status.Ambiguous`, etc.) also carry provenance for
the *criterion* that triggered the rejection — e.g., "missing `@`"
cites RFC 5322 §3.6, "non-RFC-5321 grammar" cites RFC 5322 §3.2.3.

#### What the law forbids

- ❌ A rule invented because it "felt right." Examples: silently
  strip trailing slashes from email domains; collapse consecutive dots in
  an arbitrary local part; reverse the local part; uppercase everything.
- ❌ A rule derived from observed production patterns or training-data
  statistics. Observed patterns aren't a spec; they drift.
- ❌ A rule whose provenance cannot be named. "Because I wrote it that
  way" is not a citation.
- ❌ A rule that silently accepts malformed input without a grammar gate
  backed by a cited specification — the EmailCapability's pre-Law-14
  behaviour of returning `CANONICALIZED` for `user@example.com@example.com`,
  `user@[127.0.0.300]`, `user@-domain.com`, etc., is the exact failure
  mode this law exists to forbid.

#### What the law allows

- ✅ A rewrite rule whose canonical form is selected by RFC (e.g.
  lowercasing the domain, citing RFC 5321 §2.4).
- ✅ A rewrite rule whose canonical form is selected by documented
  vendor behavior (e.g. Gmail's dot-ignoring and `+tag`-stripping, cited
  to a Google Help article).
- ✅ A rewrite rule whose canonical form is selected by an explicit
  Paxman policy (e.g. local-part lowercasing as a default matching
  convenience), provided the policy is recorded in MANDATE, an ADR, or
  the capability's spec.

#### The three operational consequences

1. **Provenance is part of the evidence record.** Each `Evidence` entry
   in an `ExecutionArtifact` carries a `provenance: str` field. A rule
   with an empty `provenance` string is a violation. This makes the law
   machine-checkable at runtime and at code review, not merely
   aspirational.

2. **Provenance is cited at capability construction time, never inferred.**
   There is no `infer_provenance(rule_name)` path. Each rule's citation is
   a constant in the capability module (`_RULE_PROVENANCE: Mapping[str,
   str]` in `email.py`). Changing a citation is a capability-version
   bump, not a no-op — the capability's behavior identity includes the
   provenance set under which it operates.

3. **Existing rules are not grandfathered.** Adopting this law requires
   auditing every rule in every shipped capability against the three
   authoritative sources. A rule that cannot be cited is removed; if its
   removal changes the canonical form of inputs that previously
   canonicalized, that is the law doing its job — it surfaces silent
   invention that had been hiding behind a `CANONICALIZED` status.

#### Provenance freezes at the capability's version

Provenance citations reference documents as they existed at the time the
capability version was published. Subsequent upstream changes to a cited
spec (RFC revision, vendor help article edit, MANDATE amendment) motivate
a *new capability version*, not a re-interpretation of past artifacts.
This keeps Law 1 (Determinism) and Law 12 (Replayability) intact: an
artifact's provenance is recorded on the artifact; the same artifact
replayed tomorrow cites the same document, even if the document mutates.

---

## 8. Versioned Contracts

The determinism invariant (§1.2) explicitly includes the Paxman version and
the registered capability set. It has not, until now, explicitly included the
contract.

Contracts evolve. A user today builds a contract that declares `Money(currency
= "MYR")`; next year they extend it to declare `Money(currency = "MYR",
locale = "en-MY")`. Replay across that boundary is governed by two rules:

1. **A contract carries a version.** The Dict DSL will grow a `version` field
   (or equivalent) so that an artifact records not only the Paxman version
   and the capability set but also the contract version that produced it.
2. **Replay against a different contract version is a v2 design decision.**
   It is recorded in `PROPOSED_STRUCTURE.md` §"Decisions left to make." The
   conservative default is to raise `VersionMismatchError`; a permissive
   future option is to allow replay if the byte-equal contract is unchanged.

The principle behind both rules: an artifact is reproducible only if every
input that shaped it — including the contract — is part of its evidence.
Contracts are not exempt from the determinism invariant.

---

## 9. The Two Mindsets

v1.x drifted because it quietly adopted the mindset of an AI system. v2
deliberately inverts it.

| v1.x mindset (rejected) | v2 mindset (mandate) |
|---|---|
| "How do I maximize successful extraction?" | "How do I ensure that every successful canonicalization is unquestionably correct?" |

These sound similar; they lead to very different architectures. The first
encourages heuristics, confidence scores, and ever-more-sophisticated
guessing. The second encourages explicit contracts, deterministic dispatch,
and saying *"I don't know"* whenever uniqueness cannot be proven.

There are countless libraries that promise to "handle anything." Very few
earn trust by saying, *"Here are the exact conditions under which I will
refuse to continue."* That restraint is not a weakness — it is the foundation
of credibility.

---

## 10. How To Use This Document

### 10.1 For contributors

Before writing code, re-read Law 11. If the abstraction you are about to
introduce can be implemented in two ways that produce different outputs for
the same input, you do not have a Paxman abstraction; you have a heuristic
in disguise. Before writing a capability, re-read Law 8a: if it depends on
state the caller did not version, it does not belong in Paxman.

### 10.2 For code reviewers

PRs that introduce any of the retired words in §6.3 — `heuristic`,
`confidence`, `best match`, `probably`, `approximate` — in either code,
comment, or docstring, must either:
1. Replace the word with one of the adopted words in §6.3, **or**
2. Justify, in the PR description, why the specific use is a deterministic
   *matching rule* (§6.4) and not a probabilistic *heuristic* (§3.2).

PRs that mutate an `ExecutionArtifact` in place (Law 13) or that allow a
capability to depend on un-versioned state (Law 8a) are rejected on sight.

PRs that introduce a new rule (transforming or rejecting) inside a capability
without an entry in that capability's `_RULE_PROVENANCE` manifest are
rejected on sight (Law 14). A reviewer asking "what spec backs this rule?"
and getting an answer that is not one of the three Law 14 sources is a
blocker.

### 10.3 For ADR authors

A new ADR must declare which of the fourteen laws are relevant to it, and
must not violate any of them. If a proposed ADR would require violating a law,
the ADR's first section must be a constitutional amendment argument, not a
design argument. An ADR that introduces or changes a canonical-form rule must
record the rule's Law 14 provenance citation as a first-class section.

### 10.4 For every design decision

When in doubt, choose the implementation that is **more deterministic, more
explicit, and more predictable** — even if it is less automatic or
recognizes fewer inputs.

> Paxman would rather reject a value than silently canonicalize it
> incorrectly.

That sentence captures everything in this document.

---

## 11. Provenance

This document codifies the conversation that motivated the v2 reboot
(2026-07-13), which followed the v1.x retraction recorded in
[`RETRACTION.md`](./RETRACTION.md). The eleven original laws and the
capability/pipeline distinction are drawn directly from that conversation.
Law 2 (Idempotence), Law 12 (Replayability), Law 13 (Artifact Immutability),
Law 8a (Capabilities Depend Only on Replayable Inputs), and the §2 formal
definition of canonicalization were added during the first review pass to
make explicit what the original conversation left implicit.

Law 14 (Canonical Forms Have Provenance) was added on 2026-07-14, after a
first-time-user experiment surfaced that the v2 EmailCapability silently
returned `CANONICALIZED` for malformed inputs (`user@example.com@example.com`,
`user@-domain.com`, `user@[127.0.0.300]`, etc.). The existing thirteen laws
described *how* Paxman behaves (deterministically, no guessing,
evidence-first) but none of them described *where canonical forms come from*.
Law 14 closes that gap; it is the constitutional answer to silent
canonical-form invention. The recalibration audit for the EmailCapability
is recorded in
[`docs/superpowers/specs/2026-07-14-law-14-canonical-form-provenance.md`](./docs/superpowers/specs/2026-07-14-law-14-canonical-form-provenance.md).

The constitutional framing — "laws, not ADRs" — is the lesson of the audit
in [`.agents/PAXMAN-BRUTAL-HONESTY-POSTMORTEM.md`](./.agents/PAXMAN-BRUTAL-HONESTY-POSTMORTEM.md):
v1.x failed because it lacked constitutional boundaries, not because it
lacked components.