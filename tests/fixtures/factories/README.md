# Programmatic Fixtures (Layer 2)

This directory holds **Layer 2 fixtures** — programmatic, hand-written factory modules that produce realistic-looking test data without using real (potentially PII-containing) production data.

## What's here

Five factory modules (committed source):

- `__init__.py` — `SEED` constant and `reseed()` helper for `factory_boy` reproducibility.
- `contracts.py` — `factory_boy` factories for Dict DSL / Pydantic / JSON Schema / OpenAPI contracts.
- `inputs.py` — `factory_boy` factories for invoice / receipt / quotation / multi-page input texts.
- `candidates.py` — `factory_boy` factories for `Candidate` and `CandidateResult`.
- `artifacts.py` — `factory_boy` factory for `ExecutionArtifact` with a stable `replay_hash`.
- `policies.py` — `factory_boy` factories for `Budget` and `Policy`.

These modules are **committed to git** (they're hand-written code, not
machine-generated artifacts). Tests that need runtime-generated data
should use these factories directly.

## How it's used

```python
from tests.fixtures.factories import contracts, inputs, artifacts

# Generate a Dict DSL invoice contract.
contract = contracts.DictDSLInvoiceFactory()

# Generate an invoice input text.
text = inputs.InvoiceInputFactory()

# Generate a deterministic ExecutionArtifact with a stable replay_hash.
artifact = artifacts.ExecutionArtifactFactory()
```

The factories are deterministic for a fixed seed — running the same
sequence of factory calls produces byte-equal output.

## Reproducibility

- All factories use `factory.Faker._get_faker()` with the project-wide
  `SEED = 0x70617821` (the hex of `"pax!"`) for reproducibility.
- `factory.random.reseed_random(SEED)` is called at module import.
- `tests.fixtures.factories.reseed(seed)` allows tests to override the
  seed for a specific test run.

```python
from tests.fixtures.factories import reseed
from tests.fixtures.factories import inputs

def test_deterministic_inputs():
    reseed(42)
    a = inputs.InvoiceInputFactory()
    reseed(42)
    b = inputs.InvoiceInputFactory()
    assert a == b
```

## Why these factories exist

- **Realism** — `factory_boy` + `faker` produce realistic-looking
  inputs/contracts (company names, currency codes, dates, IDs) that
  exercise more code paths than hand-written literals.
- **Reproducibility** — fixed seed + `factory.Faker` produces
  byte-equal output across runs.
- **Coverage** — the wide distribution of values probes edge cases
  that hand-picked inputs miss.

## See also

- [docs/TEST_DATA.md §7 The Programmatic Layer](../../../docs/TEST_DATA.md)
- [TESTING_STRATEGY.md §3 Property Tests](../../../TESTING_STRATEGY.md)
- [DEPENDENCIES.md §4 Dev Dependencies](../../../DEPENDENCIES.md)
