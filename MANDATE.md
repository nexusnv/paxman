# The Mandate of Paxman

> **Status:** Mandate. This document is the constitutional boundary of Paxman.
> No future contributor — including the original author — may violate the laws
> recorded here. Every architectural decision, every pull request, and every
> new abstraction is evaluated against the principles in this document.
>
> Where this document conflicts with `README.md`, `ARCHITECTURE.md`, an ADR,
> or any other document, this document wins.
>
> **Last amended:** 2026-07-18 — added **Law 15 (A Cited Source Is Adopted
> In Full, Or Not At All)**, forbidding partial adoption of any cited
> named-entity enumeration (countries, peoples, currencies, languages, …)
> as a discrimination-risk control. No prior law was repealed; Law 15
> closes the gap between Law 14 (cite your source) and full embodiment of
> that source's named-entity enumeration.
>
> ---

## 1. The Identity

**Paxman is a deterministic canonicalization engine.**

It transforms equivalent representations of *known* information into a single
canonical form. When the input does not contain enough information to
determine a unique result, Paxman reports that fact rather than guessing.

The project's drift was caused by leaving the boundaries implicit. They
are now explicit.

### 1.1 What Paxman is not

| Paxman is **not**… | …because |
|---|---|
| a **normalizer** | "Normalization" is a wider, fuzzier category that admits heuristic rules, scoring, and interpretation. Paxman does not interpret. It canonicalizes — it rewrites equivalent representations of *known* information into one chosen form. Normalization can guess; canonicalization cannot. |
| a **deterministic parser** | A parser maps text → structured value against a grammar. Paxman's job is broader on the input side (any representation of known information, not just text) and narrower on the output side (a single canonical form, not a parsed AST). Calling Paxman a parser mis-sets the expectation that the input must be a string and the output must be a syntax tree. |
| a **workflow engine** / **DAG orchestrator** | A user-defined pipeline places control flow in the caller's hands. Once you allow that, Paxman stops being a deterministic canonicalization engine and becomes a general-purpose workflow framework — it would re-create part of LangChain, Haystack, or a DAG orchestrator. See §4. |
| an **AI / extraction system** | Canonicalization drifts when it quietly adopts the mindset of an AI system: *"How do I maximize successful extraction?"* The mindset of a deterministic canonicalization engine is the opposite: *"How do I ensure that every successful canonicalization is unquestionably correct?"* See §7. |

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
| **contract** | A value (the starter format is the Dict DSL) that declares *what* the canonical form must be for an input. It is the source of truth (Law 4). The contract never declares *how* to produce it. |
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

### 1.4 Equivalence is semantic, not syntactic

The word *equivalent* in this document is precise, and the precision matters.

A naïve reading is: *two inputs are equivalent if they match the same standard
grammar.* That reading is **rejected**. Matching a grammar proves only that two
strings share syntax; it does not prove they name the same fact.

The correct reading, which every law here protects:

> Two representations are equivalent **iff** each deterministically expresses
> the *same underlying fact* — without requiring inference, external context,
> or a guess about intent.

Consequences:

- `"Thu, 16 Jul 2026"` (RFC 2822) and `"Thursday, 16 July 2026"` (not RFC
  2822) are equivalent, because both prove the same calendar date
  `2026-07-16`. They do **not** share a grammar; they share a *fact*.
- `"User@Example.COM"` and `"user@example.com"` are equivalent because the
  email standard deterministically licenses the lowercasing; the fact is the
  same mailbox.
- `"01/02/2026"` is **not** equivalent to either `2026-02-01` or
  `2026-01-02` until the locale is known, because the input alone does not
  deterministically fix the fact. It is reported `Ambiguous` (Law 4), not
  guessed.

Equivalence is therefore a property of *meaning under a contract*, not of
*shape*. When two distinct syntactic forms converge on the same canonical
value, the result is deterministic and welcome. When a single form admits
more than one fact, the result is `Ambiguous`. This is Principle 1 (§7.15).

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

Three things are commonly conflated in canonicalization systems. Naming them
is the first defense against drift.

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
of capability the SPI should admit:

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

### 4.4 Capabilities own domain knowledge

The core owns the *execution model* — the pipeline (§4.2), resolution (§6),
replay (Law 12), and evidence (Law 9). It does **not** own domain knowledge.

Domain knowledge — the lookup tables, recognizers, grammars, value objects,
and policy choices that decide *how* a specific kind of input is recognized
and validated — belongs to the capability that canonicalizes that domain. For
example, email is *protocol-oriented*: RFC 5321/5322 is its input grammar
because email participates in a network protocol, so the email capability owns
that grammar. Date is *value-oriented*: RFC 2822 is **not** its input grammar
— a date need only deterministically name a calendar day — so the date
standard is *provenance* (Law 14), not the recognizer's grammar. The core does
not need to know which role a standard plays for which domain; the capability
does.

The core must never *become* the central repository for "what email/date/
currency/phone/tax/unit means." If adding a new domain requires editing a core
file that enumerates every domain, the architecture has regressed (Principle 4,
§7.15).

This refines Law 6. "Paxman owns the algorithm" means Paxman owns the
*deterministic execution model*, not the *domain-specific recognition logic*.
A capability may freely own whatever internal strategy it needs, so long as
that strategy is deterministic and replayable (Law 8a).

### 4.5 Internal strategy is capability-private

Capabilities are not required to share an internal shape. A date capability
may run a lexical classifier → grammar recognizer → semantic extractor →
semantic validator → canonical renderer pipeline; a boolean capability may be
a single lookup table; a UUID capability may be a pattern plus structural
validation; a country capability may be an alias table. The common abstraction
is small:

```
Input
  ↓
Canonicalizer
  ↓
Result
```

Paxman mandates only the *boundary* (the SPI, §5), not the *internals*. The
lexer/parser/validator/renderer decomposition is an implementation detail of
one domain, not a template forced on all of them. This is why Law 11 evaluates
each abstraction against determinism, not against a uniform internal shape.

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

This shape — defined concretely in `src/paxman/_capabilities/protocol.py`
and re-exported from `paxman` as `Capability` — is the constitutional
interface. The shape must forbid control-flow verbs. Future changes to
the SPI require an explicit mandate amendment (this section), not a
silent extension of the protocol. **Absent from the SPI:**

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

### 5.5 Contract Protocol vs Domain Contract

The single word *contract* hides two distinct concepts. Conflating them is how
core ends up owning domain knowledge (§4.4).

**Paxman Contract Protocol** — owned by core. What can plug into Paxman:

- `Contract` (the abstract interface a domain contract satisfies)
- `CapabilityResult` / `ExecutionArtifact`
- `Provenance`

The core defines *how a contract participates in the engine*. It does not
define what any specific domain means.

**Domain Contract** — owned by the capability. What policy this capability
applies:

- Email: `lowercase=True`, `provider_aliases="gmail"`, `strict=False`
- Date: `locale="ISO"`
- UUID: `version="4"`

The domain contract declares *what canonical form is required* and *what policy
choices exist*. It is a **declarative DSL** — expressible both as Python
(`Date(locale="ISO")`) and as the Dict DSL (`{"kind": "canonical_date",
"locale": "ISO"}`). The contract is never the algorithm; it is the
destination (Law 5). The capability decides *how* recognition, validation, and
conversion happen.

This is Principle 5 (§7.15): **contracts define policy; capabilities implement
behavior.** Splitting the two layers is what lets a new domain be *additive*
(Principle 6) — the capability supplies both its domain contract and its
canonicalizer, and the core need not change.

---

## 6. The Algorithm — Resolver, not Planner

### 6.1 Why "planner" was retired

Earlier canonicalization work invested heavily in a "planner." That name is
retired. "Planner" implies intelligence and strategy. What Paxman actually
does is **resolve**:

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

### 6.5 Registry-based capability discovery

Resolution must not depend on the core enumerating every domain. The former
central dispatch

```python
_KIND_DISPATCH = {
    "canonical_email": CanonicalEmailContract,
    "canonical_uuid": CanonicalUUIDContract,
    "canonical_date": CanonicalDateContract,
}
```

was a scale liability: every new domain edited a core file, which violates
Principle 4 (§7.15) and Principle 6 (§7.15). It has been **removed** — see
`src/paxman/_registry/contract_registry.py`, whose header states it "replaces
the former `_KIND_DISPATCH` dict and the per-kind `if` branches."

The operative model is **self-registration**. Each capability registers its
`kind` and its domain-contract builder with the contract registry at import
time:

```python
register_contract("canonical_email", _build_email)
register_contract("canonical_date", _build_date)
```

The core then performs only `kind → registry lookup → construct contract`. It
no longer knows what email, date, or currency *means*. Discovery is additive:
shipping a new capability never requires touching core, and Law 11 stays
enforceable because the registry entry is itself a deterministic, auditable
registration — not a hardcoded branch.

This is the operational form of Principle 6: **new canonicalization domains
should be additive, not require core modification.**

The same principle holds at the capability layer. `CapabilityRegistry`
(`src/paxman/_registry/capability_registry.py`) holds the capability set and
freezes it on the first `canonicalize` call; new capabilities self-register via
`register_capability` rather than being enumerated in a central list. The
contract registry and the capability registry together are what keep Paxman's
core domain-ignorant — which is exactly Principle 4 (§7.15).

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
internal invariant violation) and are governed by the `paxman._errors`
package hierarchy.

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

This law becomes a filter for **every pull request**. It is the law that
prevents silent invention.

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
>    capability's published spec under `docs/capabilities/<domain>/index.md`).
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

### Law 15 — A Cited Source Is Adopted In Full, Or Not At All

> When a capability cites an authoritative source that enumerates **named
> entities** (countries, peoples, nations, currencies, languages, scripts,
> jurisdictions, or any other discrete set of named human or political
> subjects), Paxman must embody that enumeration **in full** or not cite it
> at all. Partial adoption of such a source is forbidden.

#### Why this law exists

Law 14 requires every rule to *cite* an authority. It does **not** require
the cited authority to be *fully embodied*. That gap permits a dangerous
failure mode: a capability can cite `ISO 3166-1:2020` for its country
table, satisfy Law 14, and yet include only a curated subset of the
enumerated names — silently omitting some nations while including others.
Including "Germany" but omitting "Lao People's Democratic Republic" is not
a neutral data choice. It is the appearance of a *selection* — a silent
editorial judgement about which named peoples are worth recognizing. That
is a discrimination risk and an accusation Paxman must be structurally
incapable of attracting.

The protection is therefore **not** "cite your sources" (Law 14). It is
**"if you cite a source that names peoples, you adopt its full naming, or
you do not cite it."** A capability that recognizes 40 of 249 ISO country
names while citing ISO 3166-1 violates this law, even though every one of
the 40 entries individually carries a valid Law 14 citation.

#### What counts as "named entities"

The law is scoped to enumerations of *named human or political subjects* —
the cases where partial adoption reads as a judgement about whose identity
is worth recording. This deliberately excludes bulk reference data whose
partial adoption carries no such implication (e.g. a sample of Unicode CLDR
localized strings, a subset of code-point ranges, a benchmark vector). For
those, partial adoption is governed by Law 14 plus an explicit scope
statement (see the allowed exceptions below).

#### Forbidden

- ❌ Citing `ISO 3166-1` for a country table that contains only a subset of
  the standard's enumerated names.
- ❌ Citing `ISO 4217` for a currency table that lists only the currencies
  the author happened to need.
- ❌ Any "curated," "common," or "Tier-1" subset of a named-entity
  enumeration presented as if it were the cited source.

#### Allowed (with a recorded justification)

Partial adoption of a *named-entity* source is permitted **only** when a
strong, recorded justification exists, and that justification is itself
captured as provenance (Law 14 source #3 — an explicit Paxman policy):

- **Version mismatch** — the bundled data reflects a different edition of
  the source than the one currently published, and the discrepancy is
  documented (e.g. the dataset was frozen at `iso3166-1:2020` and the
  capability cites that frozen edition explicitly, not the live standard).
- **Data unavailable at publish time** — a portion of the source could not
  be obtained or verified when the capability was authored; the missing
  portion is enumerated in the recorded justification.
- **Explicit scope boundary for non-named-entity bulk data** — for sources
  that are not named-entity enumerations (CLDR samples, code-point subsets),
  a documented scope statement records *why* a subset was chosen. This is a
  Law 14 + scope-statement path, not a Law 15 waiver, and must never be
  used to excuse a partial *named-entity* adoption.

A justification that reduces to "we only needed a few" or "these are the
common ones" is **not** strong and does not satisfy this law.

#### Operational consequence

When a capability cites a named-entity source, its dataset must be
complete against that source's enumeration, or the citation must name the
exact frozen edition that the dataset *does* fully embody. Adopting this
law may require back-filling an existing table to full coverage (e.g.
extending a country name table from a curated subset to all enumerated
ISO 3166-1 names) — that back-fill is the law doing its job, not a breaking
change to be avoided.

### 7.15 Design Principles

The fourteen laws are the constitutional floor. The architecture discussion
that refined this document surfaced six design principles that the laws
protect and that guide *future* extension. They are not laws — they are the
load-bearing intuitions a contributor should reach for when a law does not
already decide the case.

**Principle 1 — Semantic equivalence, not textual similarity.**
Canonicalization is about whether two representations deterministically
express the same *fact*, not whether they share syntax. See §1.4.

**Principle 2 — Standards are provenance sources, not necessarily complete
input grammars.**
A standard such as RFC 2822 is the *input grammar* for email (email
participates in a network protocol) but only *provenance* for dates (a date
need not satisfy RFC 2822 to name a unique calendar day). Which role a
standard plays depends on the domain; see §4.4.

**Principle 3 — Determinism means proving uniqueness, not selecting a single value.**

This restates Law 1 and Law 4: when more than one fact is possible, report
`Ambiguous`; never select a single candidate.

**Principle 4 — The core engine should not own domain knowledge.**
Domain tables, grammars, and policies belong to capabilities (§4.4). The core
owns execution, lifecycle, the contract *protocol*, results, and tracing.

**Principle 5 — Contracts define policy; capabilities implement behavior.**
The two layers of *contract* are split in §5.5. The domain contract is a
declarative DSL; the capability owns the algorithm that satisfies it.

**Principle 6 — New domains are additive, not core-modifying.**
Shipping a new canonicalization domain must not require editing core. Registry
self-discovery (§6.5) is the mechanism that keeps this true.

These six principles, together with the fourteen laws, point to the intended
long-term shape of Paxman:

```text
Small deterministic core
        +
Capability-owned canonicalizers
        +
Declarative contracts
        +
Registry-based discovery
        +
Explicit provenance and trace
```

Adding dates, currencies, tax codes, units of measure, addresses, or
identifiers should make Paxman *broader*, never *larger internally*: the core
remains a stable canonicalization kernel surrounded by specialized knowledge
modules.

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
2. **Replay against a different contract version is an open design decision.**
    The conservative default is to raise `VersionMismatchError`; a permissive
    future option is to allow replay if the byte-equal contract is unchanged.

The principle behind both rules: an artifact is reproducible only if every
input that shaped it — including the contract — is part of its evidence.
Contracts are not exempt from the determinism invariant.

---

## 9. The Two Mindsets

Canonicalization drifts when it quietly adopts the mindset of an AI system.
Paxman deliberately inverts it.

| AI / extraction mindset (rejected) | Canonicalization mindset (mandate) |
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

PRs that cite a named-entity source (countries, peoples, currencies,
languages, scripts, jurisdictions — any discrete set of named human or
political subjects) for a capability dataset are rejected on sight unless
the dataset embodies that source's enumeration **in full** or names the
exact frozen edition it does fully embody, with any partial-adoption
justification recorded as provenance (Law 15). A reviewer asking "is this
the complete enumeration, or a curated subset?" and getting "we only needed
a few" is a blocker.

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

The eleven original laws and the capability/pipeline distinction are drawn
directly from the conversation that produced this document. Law 2
(Idempotence), Law 12 (Replayability), Law 13 (Artifact Immutability), Law 8a
(Capabilities Depend Only on Replayable Inputs), and the §2 formal
definition of canonicalization were added during the first review pass to
make explicit what the original conversation left implicit.

Law 14 (Canonical Forms Have Provenance) was added on 2026-07-14, after a
first-time-user experiment surfaced that the EmailCapability silently
returned `CANONICALIZED` for malformed inputs (`user@example.com@example.com`,
`user@-domain.com`, `user@[127.0.0.300]`, etc.). The existing laws
described *how* Paxman behaves (deterministically, no guessing,
evidence-first) but none of them described *where canonical forms come from*.
Law 14 closes that gap; it is the constitutional answer to silent
canonical-form invention. The recalibration audit for the EmailCapability
is recorded in its capability spec under `docs/capabilities/email/index.md`.

The constitutional framing — "laws, not ADRs" — is what makes Paxman
resistant to the kind of silent invention that constitutional boundaries
exist to prevent: a system can fail not because it lacked components, but
because it lacked the laws to reject inventions.

---

On 2026-07-15, an architecture discussion refined the document with the
semantic-equivalence clarification (§1.4), the capability ownership of domain
knowledge (§4.4–§4.5), the two-layer contract model (§5.5), registry-based
discovery (§6.5), and the six Design Principles (§7.15). None of these
contradict the fourteen laws; they make explicit what the original
conversation left implicit about *equivalence*, *where domain knowledge
lives*, and *how new domains join without modifying core*. The discussion's
date-pipeline example (lexer → grammar → recognizer → validator → renderer)
is recorded as one *capability-private* strategy, not a mandated shape — see
§4.5.