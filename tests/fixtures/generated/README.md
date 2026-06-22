# Programmatic Fixtures (Layer 2)

This directory holds **Layer 2 fixtures** — programmatically generated inputs, contracts, candidates, and artifacts. These are produced at test time by `factory_boy` + `faker` + `hypothesis` and are **not committed to git**.

## What's here

Only:

- `.gitignore` (which ignores everything in this directory except itself)
- `README.md` (this file)

Everything else is generated at test time.

## How it's used

The generator module lives in `tests/fixtures/generators/` (a sibling directory, not in `generated/`):

- `tests/fixtures/generators/invoices.py` — `factory_boy` factories for invoice inputs.
- `tests/fixtures/generators/contracts.py` — `pydantic-factories` factories for `CanonicalContract`s.
- `tests/fixtures/generators/candidates.py` — `factory_boy` factories for `Candidate` sets.
- `tests/fixtures/generators/artifacts.py` — `factory_boy` factories for `ExecutionArtifact`s.
- `tests/fixtures/generators/hypothesis_strategies.py` — Hypothesis strategies for property tests.

A public `paxman.testing` module will re-export the Hypothesis strategies for downstream use.

## Reproducibility

- All programmatic fixtures are generated with a fixed random seed by default.
- `factory_boy` uses `factory.random.reseed_random(seed)`.
- `hypothesis` uses `derandomize=True` for property tests.
- The seed is recorded in `tests/fixtures/generated/SEED.txt` (gitignored) so a failing test can be reproduced.

```python
# In conftest.py
import factory.random
import hypothesis

@pytest.fixture(autouse=True)
def seed_programmatic_fixtures():
    factory.random.reseed_random(42)
    hypothesis.settings.register_profile("ci", derandomize=True)
    hypothesis.settings.load_profile("ci")
```

## Why this layer is gitignored

- **Reproducibility** — the seed is the source of truth, not the generated files.
- **Repo size** — thousands of generated files would bloat the repo.
- **Flexibility** — the generator can change without touching the repo.

## See also

- [docs/TEST_DATA.md §7 The Programmatic Layer](../../../../docs/TEST_DATA.md)
- [TESTING_STRATEGY.md §3 Property Tests](../../../../TESTING_STRATEGY.md)
- [DEPENDENCIES.md §4 Dev Dependencies](../../../../DEPENDENCIES.md)
