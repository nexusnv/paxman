# ADR-0008: License Decision

> **Status:** Accepted
> **Date:** 2026-06-22
> **Deciders:** Paxman core team
> **Supersedes:** —
> **Superseded by:** —

## Context and Problem Statement

Paxman's README states: "MIT (or Apache-2.0 — final TBD by the team." Sprint 0 closes this gap. The license decision blocks Sprint 1's `LICENSE` file creation, `pyproject.toml` metadata, and PyPI publishing configuration. Without a resolved license, no artifact can be published and no downstream consumer can legally integrate Paxman.

The trade-off analysis and full rationale are documented in the sibling specification at `../specs/license-decision.md`.

## Decision Drivers

- **Developer-focused library** (PRD §6.1) — Paxman's consumers are developers integrating a library, not end users of a service.
- **Python ecosystem convention** — MIT is the de facto standard for Python libraries on PyPI.
- **Minimal legal review surface** — the 3-package core dependency policy (DEPENDENCIES.md §2) keeps the legal footprint tiny.
- **No patent-encumbered domain** — Paxman normalizes documents; it does not operate in biotech, finance-specific, or standards-essential patent territory.
- **Downstream packaging friction** — Gentoo, Debian, conda-forge all have well-established MIT workflows.

## Considered Options

### Option A — MIT License (chosen)

~200 lines of plain English. Permissive. No explicit patent grant. The most common license for Python libraries.

**Pros:**

- Most familiar license to Python developers.
- Simplest legal text; easy to review, embed, and reference downstream.
- No `NOTICE` file maintenance burden.
- Compatible with all permissive and copyleft dependencies when used as a library.
- Lowest friction for downstream packagers (Gentoo, Debian, conda-forge).

**Cons:**

- No explicit patent grant — contributors grant copyright but not patent rights.
- No patent retaliation clause — nothing discourages a contributor from later asserting patents.

### Option B — Apache-2.0 License

~400 lines of legal text plus an appendix. Permissive with an explicit patent grant and patent retaliation clause. Standard for data/ML, enterprise, and corporate-friendly projects.

**Pros:**

- Patent grant protects users from contributor patent claims.
- Patent retaliation clause discourages patent aggression.
- Preferred by corporate and enterprise legal teams.

**Cons:**

- `NOTICE` file must be maintained and distributed with all copies.
- Longer text is harder to embed and review.
- Patent provisions are unnecessary for Paxman's domain.
- Slightly higher friction for downstream packagers.

### Option C — Dual MIT/Apache-2.0

Offer both licenses; the user chooses which applies. Used by Rust ecosystem (rust-lang/rust).

**Pros:**

- Maximum flexibility for consumers with different legal requirements.

**Cons:**

- Adds complexity to every distribution and attribution.
- Confusing for users unfamiliar with dual licensing.
- Overkill for a library with no patent risk.

## Decision Outcome

**Chosen option: A (MIT License).**

Paxman is a developer library, not a service or a standards-essential implementation. Its domain (document normalization) carries no patent risk. MIT is the dominant license for Python libraries on PyPI, and the 3-package core dependency policy keeps the legal review surface minimal. The 200-line MIT text is the easiest to review, embed, and reference downstream.

If patent concerns emerge — for example, a corporate sponsor with a patent policy, or a contributor with relevant patent claims — a new ADR will be written and this one marked Superseded.

## Consequences

### Positive

- Lowest friction for downstream packagers (Gentoo, Debian, conda-forge).
- Familiar to the Python ecosystem; no legal surprises.
- Minimal review burden for consumers integrating Paxman.

### Negative

- No patent grant — corporate users in patent-litigious domains may require an Apache-2.0 wrapper or contributor agreement.

### Neutral

- `LICENSE` file created in Sprint 1.
- `pyproject.toml` declares `license = { text = "MIT" }`.
- SPDX identifier `MIT` used consistently across metadata.

## Validation

- `LICENSE` file created in Sprint 1 (per `sprint-01-foundation.md` D1.4).
- `pyproject.toml` `license = { text = "MIT" }` set in Sprint 1.
- PyPI metadata declares MIT at publish time (Sprint 9 / 10).
- `README.md` §License updated to remove the TBD qualifier.
- `choosealicense.com` MIT template matches the committed `LICENSE` file verbatim.

## References

- Sibling document: `../specs/license-decision.md`
- `../index.md` §License
- `../reference/dependencies.md` §2 (core dependency policy)
- `../../PRD.md` §6.1 (developer-focused library)
- SPDX MIT: https://spdx.org/licenses/MIT.html
- choosealicense.com MIT: https://choosealicense.com/licenses/mit/
