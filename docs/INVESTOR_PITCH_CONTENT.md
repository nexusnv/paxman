# Investor Pitch Content — Paxman

> **For internal use only. Supporting material for investor pitch deck.**
> Target audience: Senior management — Oil & Gas, Pharmaceutical, Medicine, ESG, Trading, Manufacturing, Aviation.

---

## 1. The Opening: The Hidden Tax on Every Enterprise

Every company in this room runs on **normalized data** — but nobody talks about how much it costs to get it.

Your procurement system needs supplier invoices in a consistent format. Your compliance team needs audit trails that connect a PDF to a database row with cryptographic integrity. Your ESG reporting needs emissions data from 50 different suppliers, each sending it differently. Your treasury needs multi-currency line items that actually add up.

You're currently paying for this in one of four ways, and none of them are good:

- **Hand-rolled pipelines** — armies of engineers writing extractors per source, per format, per field. High maintenance. Slow to adapt. No audit trail.
- **"Just call an LLM"** — plausible output with zero provenance. When it gets it wrong, you don't know why, and you can't prove it was right the first time.
- **Monolithic vendor services** — black boxes with opaque pricing. You own nothing. Your data leaves your control. Switching costs are brutal.
- **Schema validators alone** — they tell you when data is bad, but they don't help you make it good.

This is not a technical problem. This is a **structural tax** on every data-dependent operation in your business. And it's growing exponentially as data volumes and regulatory demands increase.

**The question is not whether you're paying this tax. The question is whether you know how much.**

---

## 2. The Insight: Field-Centric Thinking Changes Everything

Every document processing system today shares the same blind spot: they process **documents**, not **fields**.

When you receive a supplier invoice, you don't need "the invoice understood." You need the **invoice number**, the **total amount**, the **currency**, the **line items**, the **tax breakdown**, and the **due date**. Those are separate problems with separate solutions.

- Some fields are trivially extractable — regex finds an invoice number in milliseconds.
- Some need structured lookup — a currency code maps to a standard.
- Some need inference — a handwritten "PO-1234" on a scanned PDF.
- Some cannot be resolved at all — and you need to know that honestly, not silently.

**Why would you invoke an expensive LLM to resolve a field that regex can handle in 50 microseconds?**

Paxman is built on this insight: each field should get its own execution plan, optimized for that field's requirements and that input's characteristics. The pipeline is synthesized dynamically per (contract, input) pair. Never one-size-fits-all. Never wasteful.

This is the difference between hiring a PhD to read every line of a document and having a trained assistant who knows exactly which parts to read carefully and which parts to handle automatically.

---

## 3. The Problem: Five Industries, One Hidden Crisis

### Oil & Gas

You manage procurement across dozens of countries, hundreds of suppliers, and thousands of contracts — each with different formats, currencies, tax regimes, and language conventions. Your compliance obligations (SOX, SEC, local regulators) demand auditable trails from raw document to ledger entry. Current solutions either require enormous manual effort or produce opaque results that auditors reject.

**The cost:** Millions in manual invoice processing. Months to onboard new suppliers. Compliance gaps that emerge during every audit cycle.

### Pharmaceutical

Clinical trial documents, regulatory submissions (FDA, EMA), supplier quality agreements, batch records — every document type has a schema, every schema has a regulatory requirement, every submission must survive inspection. Your data pipelines need to be not just correct, but **provably correct** — with evidence chains that connect raw source documents to structured outputs.

**The risk:** A data extraction error in a regulatory submission can delay a drug approval by months. A pattern of untraceable errors can trigger a warning letter.

### Medicine / Healthcare

Claims processing, medical records normalization, supplier procurement — HIPAA adds another dimension. PHI must be protected end-to-end. Auditors need to trace every data point to its source. But today's normalization approaches either expose PHI to third-party services or produce outputs with no evidentiary chain.

**The constraint:** You cannot simply "send everything to an LLM" when patient data is involved. You need a system that respects data minimization by design.

### ESG / Sustainability

You're collecting emissions data, environmental reports, and supplier questionnaires from hundreds of entities — each using different formats, different units, different reporting periods, different levels of granularity. Regulators (SEC climate rules, CSRD, ISSB) are demanding auditable, standardized data. The MONEY amounts in carbon credit trades cannot tolerate floating-point rounding errors.

**The pressure:** ESG reporting is moving from voluntary to mandatory. The tools most companies use today (spreadsheets, email, manual data entry) will not survive regulatory scrutiny.

### Trading / Finance

Your trading, treasury, and procurement systems deal with MONEY — not numbers. Currency conversions, decimal precision, multi-currency line items — these are not "decimal fields with annotations." They are a distinct data type with its own rules, its own precision requirements, and its own compliance implications. A rounding error in FX across thousands of transactions is not a bug. It's a loss.

**The reality:** Most normalization systems treat MONEY as a tagged DECIMAL. Paxman treats it as a first-class type — amount + ISO-4217 currency + explicit precision. Never float. Never ambiguous.

### Manufacturing

Your supply chain runs on supplier quotations, purchase orders, invoices, and shipping documents — each from a different ERP, each with its own quirks, each needing to feed into your systems with integrity. Multi-currency, multi-language, multi-unit. The cost of manual re-keying and exception handling is buried in your operating expenses, invisible to management dashboards.

**The hidden cost:** Every minute a procurement professional spends reformatting a supplier document is a minute not spent negotiating, sourcing, or managing relationships.

### Aviation

Maintenance records, parts procurement documents, regulatory compliance filings (EASA, FAA) — accuracy is not optional. An incorrect part number in a maintenance record can ground an aircraft. A broken evidence chain in a compliance filing can trigger regulatory action. Your suppliers range from multinational OEMs to small MRO shops, each with different documentation practices.

**The requirement:** Deterministic, auditable, replayable normalization. You cannot fix an error after the fact if you cannot replay how the data was produced.

---

## 4. The Solution: Paxman

**What it is:** A Python library that takes arbitrary input (PDFs, scans, emails, spreadsheets, free text) and a caller-supplied contract (your schema, your rules, your requirements) and produces a normalized, evidence-backed, replayable artifact.

**What it is not:** A SaaS platform, a vendor lock-in trap, a black box, or yet another "AI agent for documents."

### The Core Loop

```
You bring a contract ──► Paxman synthesizes ──► Executes the ──► Returns an artifact
(any schema format)      the cheapest plan      cheapest plan      with evidence +
                        per field, per input     per field         confidence + hash
```

### The Seven Design Decisions That Make This Possible

**Decision 1: Field-centric, not document-centric.**
Every field gets its own plan. Never waste inference on fields you could parse. Never parse fields you need to infer. Cost-optimized at the most granular level possible.

**Decision 2: Deterministic planner.**
The planner is a pure function — no LLM, no agent, no AI-generated logic. Given the same input and same contract, it produces the same plan every time. Predictable. Testable. Auditable.

**Decision 3: Reconciler as sole truth authority.**
Capabilities do their job (extract, parse, infer) and produce candidates. The Reconciler decides what is true. No confidence inflation. No conflicting truth claims. One source of resolved truth per field.

**Decision 4: Replay without recomputation.**
Once an artifact is produced, replay is pure deserialization. No capabilities are re-invoked. No plans are regenerated. The SHA-256 hash cryptographically ties every resolved value to its evidence. Tamper with the artifact, and replay fails.

**Decision 5: MONEY as a first-class type.**
Not a tagged DECIMAL. Not a float with annotations. MONEY has amount (Decimal), currency (ISO-4217), and precision. Cross-currency handling is explicit, never implicit.

**Decision 6: Three explicit truth layers.**
- **Contract Truth:** What the caller requires.
- **Candidate Truth:** What capabilities discovered.
- **Resolved Truth:** What the Reconciler accepts.

Every field in every artifact can be traced through these three layers. No silent decisions. No hidden transformations.

**Decision 7: Tiny, stable public surface.**
Five public functions. Learnable in minutes. Embeddable in any stack. Zero persistence — Paxman returns an artifact and stops. Storage, orchestration, and lifecycle are yours.

---

## 5. The Moat: Why This Is Hard to Copy

**Open source is the moat, not the product.**

Paxman is MIT-licensed — anyone can use it, modify it, embed it. This is a deliberate choice, not a concession. Here's why it matters:

- **Adoption velocity:** Zero procurement friction. A developer at a Petrobras supplier can download Paxman and start normalizing invoices in five minutes. No sales call. No legal review. No vendor onboarding.
- **Ecosystem gravity:** Every adapter, capability, or inference provider is a potential `paxman-*` package on PyPI. The core team maintains the nucleus; the community builds the solar system.
- **Switching costs run the other way:** Paxman owns zero schemas, zero storage, zero data. The caller owns everything. If they leave, they take their contracts, their artifacts, and their replay chain. There is no data hostage.
- **Enterprise features are additive, not extractive:** Compliance, audit, and governance features sit on top of the open-source core. The core is free and complete for the basic use case. Advanced needs drive enterprise adoption of complementary services.

**Why competitors cannot replicate this:**

| Competitor type | Why they can't copy |
|---|---|
| **Vendor services** | Black-box architecture. They cannot offer replay + cryptographic integrity without rebuilding from scratch. Their business model depends on opacity. |
| **ETL frameworks** | Document-centric by design. Field-centric would require a complete architectural rewrite. |
| **LLM wrappers** | Non-deterministic by nature. They cannot guarantee replay without caching every LLM response — which they don't. |
| **Hand-rolled solutions** | Every company that builds its own is starting from zero. Paxman is the shared investment. |

---

## 6. The Market: Every Company Is a Data Normalization Company

**Total addressable market:** Every organization that receives unstructured or semi-structured data and needs structured, auditable outputs.

**Served market (V1 focus):** Procurement, accounts payable, compliance, and regulatory documentation teams — the functions that live at the intersection of "data arrives messy" and "output must be correct."

**Why now:**

1. **Regulatory pressure is intensifying.** SEC climate rules, CSRD, FDA data integrity requirements, SOX compliance, HIPAA enforcement — the regulatory environment is demanding provably correct data pipelines.
2. **AI adoption is exposing the provenance gap.** Companies that rushed to deploy LLM-based extraction are discovering that "plausible" is not the same as "correct." The need for evidence-backed AI outputs has never been more acute.
3. **The cost of manual processing is no longer acceptable.** In an era of margin pressure, the hidden tax of manual data normalization is increasingly visible to CFOs.
4. **Vendor lock-in fatigue is real.** Every major enterprise has been burned by a platform that made extraction easy and exit impossible. The market is ready for a library that respects caller ownership.

---

## 7. The Vision

**Today:** You bring a contract and data; Paxman returns a normalized, evidence-backed artifact.

**Tomorrow:** Paxman is the normalization layer for the world's structured and semi-structured data. Every document, every form, every email, every PDF that needs to become a database row passes through a field-centric plan. Every artifact is replayable. Every output is auditable. Every unresolved field is explicit.

**Not because Paxman owns the data. Because Paxman owns the method.**

And methods, unlike platforms, don't disappear when the vendor pivots.

---

## 8. Key Metrics & Targets (V1)

| What | Target |
|---|---|
| Time to normalize a 20-field contract on 100 KB input | ≤ 200 ms (p50), ≤ 2 s (p99) |
| Time to replay a 100 KB artifact | ≤ 50 ms (p50), ≤ 500 ms (p99) |
| Cold-start import + capability registration | ≤ 100 ms |
| Field resolution rate (canonical invoice corpus) | ≥ 90% SUCCESS |
| Replay reproducibility | 100% identical artifact hash |
| Core dependencies | 2 packages (`attrs`, `typing-extensions`) |
| Public API surface | 5 functions |
| License | MIT |

---

## 9. The Ask (Suggested Positioning)

We are building the normalization infrastructure for the next decade of enterprise data processing. We need partners who understand the problem — not just technically, but structurally.

We are not selling a tool. We are offering an architecture for how enterprises will process documents in a world where correctness, auditability, and cost-efficiency are non-negotiable.

**The opportunity:** Be part of defining how the world normalizes data — before the market consolidates around the wrong answer.

---

## APPENDIX: Glossary for Non-Technical Stakeholders

| Term | Plain English |
|---|---|
| **Normalization** | Converting messy, inconsistent input into clean, structured output that systems can use |
| **Deterministic** | Given the same input, always produces the same output — no randomness, no surprises |
| **Replay** | Re-running a previous result exactly as it was — like having a recording, not a memory |
| **Replay hash** | A cryptographic fingerprint that proves an artifact hasn't been tampered with |
| **Artifact** | The final output package — includes the data, how each value was obtained, and how confident the system is |
| **Contract** | Your specification of what fields you need, their types, and any validation rules — like a data contract |
| **Field plan** | The step-by-step process for resolving one specific field, optimized for that field alone |
| **Capability** | One atomic operation like text extraction, regex matching, or LLM inference |
| **Reconciler** | The subsystem that decides the final truth when multiple sources offer different answers |
| **Confidence band** | A rating from CERTAIN to UNTRUSTED — tells you how reliable each resolved value is |
| **Field-centric** | Optimizing per field rather than processing entire documents as a unit |
| **MONEY type** | A data type that handles currency values with proper decimal precision and currency codes — never floats |
| **Adapter** | A translator that converts external schema formats (Pydantic, JSON Schema, OpenAPI) into Paxman's internal format |
| **Evidence** | The provenance trail showing where each value came from — which capability produced it, from what part of the input |
| **Secrets by reference** | API keys and credentials are never stored in the artifact — only references to where they can be found |
