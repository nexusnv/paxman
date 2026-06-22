# Golden Execution Artifacts

This directory contains the **golden `ExecutionArtifact` JSON files** used by replay-equality tests. Each golden artifact is the **expected** output of `paxman.normalize()` for a specific `(input, contract)` pair.

## Why golden artifacts matter

Paxman's determinism and replay claims rest on the `replay_hash` being stable for the same `(input, contract, version)` triple. The golden artifacts in this directory are the **ground truth** for what the artifact should look like — including the `replay_hash`.

When the implementation produces a different `replay_hash` for the same input, the test fails. This is how we catch determinism regressions.

See [REPLAY_AND_DETERMINISM.md](../../../../REPLAY_AND_DETERMINISM.md) for the full replay model.

## V1 golden artifacts (planned)

| File | What it tests | Expected status |
|---|---|---|
| `invoice_success.json` | Invoice that fully resolves | `SUCCESS` |
| `invoice_partial.json` | Invoice with one `UNRESOLVED` field | `PARTIAL_SUCCESS` |
| `invoice_unresolved.json` | Invoice with no resolvable fields | `UNRESOLVED` |
| `quotation_success.json` | Quotation that fully resolves | `SUCCESS` |
| `procurement_success.json` | Procurement record that fully resolves | `SUCCESS` |
| `invalid_contract.json` | Bad contract | `INVALID_CONTRACT` (exception, not artifact) |
| `execution_failed.json` | Capability crash | `EXECUTION_FAILED` |
| `money_mismatch.json` | MONEY with conflicting currencies | `PARTIAL_SUCCESS` |
| `multi_page.json` | Multi-page PDF | `SUCCESS` |

## Status

**As of the current state of the project, these golden artifacts are NOT written yet.**

This is a deliberate gap. The `ExecutionArtifact` JSON shape is not finalized until the actual `ExecutionArtifact` Pydantic model is implemented in code. Writing golden artifacts now would commit us to a specific shape that the code might evolve.

**The golden artifacts will be written when:**

1. The `ExecutionArtifact` Pydantic model is implemented.
2. The `CanonicalContract` and `FieldResult` schemas are stable.
3. The planner + executor + reconciler produce a real artifact from a real fixture.

At that point, the implementation will:

1. Run `paxman.normalize(input, contract)` for each curated fixture.
2. Capture the resulting `ExecutionArtifact`.
3. Save it as the golden file.
4. Re-run to verify byte-equal reproducibility.
5. Commit.

This is a one-time bootstrap that happens during the V0.3 (alpha) → V0.5 (beta) transition.

## How to use golden artifacts (once written)

The replay-equality test pattern:

```python
def test_replay_reproduces_artifact():
    """The replay of a stored artifact reproduces it byte-for-byte."""
    artifact = paxman.normalize(input_data, contract, budget, policy)
    golden = load_golden("invoice_success.json")
    assert serialize(artifact) == serialize(golden)
    assert artifact.replay_hash == golden.replay_hash
```

## How to regenerate golden artifacts

When the artifact schema changes (e.g., new field, version bump):

```bash
# Regenerate the golden artifacts
python scripts/regenerate_golden_artifacts.py

# Run the tests to verify
make test-integration
```

This script is **not yet written**; it will be written when the artifact schema is stable.

## See also

- [REPLAY_AND_DETERMINISM.md](../../../../REPLAY_AND_DETERMINISM.md) — replay model
- [V1_ACCEPTANCE_CRITERIA.md](../../../../V1_ACCEPTANCE_CRITERIA.md) — V1 definition of done
- [docs/TEST_DATA.md §8.3](../../../../docs/TEST_DATA.md) — golden artifact policy
- [TESTING_STRATEGY.md §5 Replay Tests](../../../../TESTING_STRATEGY.md)
