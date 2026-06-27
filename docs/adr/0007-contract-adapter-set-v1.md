# ADR-0007: V1 Contract Adapter Set

> **Status:** Accepted
> **Date:** 2026-06-22
> **Deciders:** Paxman core team
> **Supersedes:** —
> **Superseded by:** —

## Context and Problem Statement

Paxman supports multiple contract formats via adapters. [PRD §5.1](https://github.com/nexusnv/paxman-wiki/blob/main/Internal-Development/PRD.md) lists 8 contract origin types (Python models, API schemas, ERP object models, agent tool schemas, JSON Schema, OpenAPI, custom DSLs, wrapper applications). Not all of these need a first-party adapter in V1. This ADR decides which adapters ship as required, optional, or not at all in V1.

## Decision Drivers

- **Adapter maintenance burden** (PRD §12 R-2) — every adapter adds long-term maintenance cost.
- **Coverage of common use cases** — Pydantic and JSON Schema cover most real-world callers.
- **Testability** — fewer adapters = smaller test matrix.
- **V1 scope discipline** — V1 should be small and reliable, not maximal.
- **Extensibility** — third-party adapters can fill gaps post-V1.

## Considered Options

### Option A — Ship 4 adapters: Pydantic, JSON Schema, Dict DSL, OpenAPI (chosen)

| Origin | V1 Adapter | Status |
|---|---|---|
| Python models (Pydantic) | Pydantic Adapter | **Required** |
| JSON Schema | JSON Schema Adapter | **Required** |
| Custom DSL | Dict DSL Adapter | **Required** |
| OpenAPI | OpenAPI Adapter | **Optional (best-effort)** |
| ERP object models | _(no V1 adapter)_ | Caller adapts to Pydantic/JSON Schema |
| Agent tool schemas | _(no V1 adapter)_ | Caller adapts to Pydantic/JSON Schema |
| Wrapper applications | _(no V1 adapter)_ | Caller adapts to Pydantic/JSON Schema |
| Plain API schemas (not OpenAPI) | JSON Schema Adapter | **Required** (JSON Schema is the lingua franca) |

**Pros:**

- Covers the dominant real-world formats.
- Three required adapters is a small, testable surface.
- OpenAPI is best-effort; we don't block V1 on full 3.1 coverage.

**Cons:**

- ERP / agent / wrapper use cases require an adaptation step.
- OpenAPI coverage is partial.

### Option B — Ship 6 adapters: above plus ERP and agent tool

**Pros:**

- More formats out of the box.

**Cons:**

- Doubles the adapter test matrix.
- ERP and agent tool formats are heterogeneous; a single adapter covers a small subset.
- Higher maintenance burden.

### Option C — Ship only 2: Pydantic and JSON Schema

**Pros:**

- Smallest possible surface.

**Cons:**

- No escape hatch (Dict DSL) for callers who don't use Pydantic.
- No OpenAPI support even at best-effort.

## Decision Outcome

**Chosen option: A.**

- **Required:** Pydantic Adapter, JSON Schema Adapter, Dict DSL Adapter.
- **Optional (best-effort):** OpenAPI Adapter.
- **Not in V1:** ERP, agent tool, wrapper adapters. Callers adapt these to a supported format.

The Dict DSL is included because it is Paxman's internal escape hatch and the source of truth for tests. It must ship.

The OpenAPI Adapter is best-effort: a passing test suite is enough for V1; full OpenAPI 3.1 coverage is not required.

## Consequences

### Positive

- Small, testable adapter surface (3 + 1).
- Most real-world callers are covered (Pydantic is the dominant Python schema library; JSON Schema is the dominant cross-language schema).
- The Dict DSL is the test source of truth.

### Negative

- ERP / agent / wrapper users must adapt to Pydantic or JSON Schema. This is a documented one-time cost.
- OpenAPI Adapter is partial; some 3.1 features are unsupported.

### Neutral

- Third-party adapters are encouraged. The `ContractAdapter` SPI is public.

## Validation

- Each required adapter has a dedicated test suite covering representative contracts.
- The OpenAPI Adapter has a smaller test suite covering the supported subset.
- The Dict DSL is used by all internal tests as the lingua franca.

## References

- PRD.md §5.1, §5.2
- ARCHITECTURE.md §4.1, §17.1
- PACKAGE_STRUCTURE.md §3
