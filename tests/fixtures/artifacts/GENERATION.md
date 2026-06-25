# Golden Artifact Generation

This directory holds the **golden `ExecutionArtifact` JSON files** used
by replay-equality tests. Each golden is the **expected output** of
`paxman.normalize()` for a specific `(input, contract)` pair.

## How goldens are generated

All goldens in this directory are **bootstrapped from real
`paxman.normalize()` calls** — never predicted. The generation
procedure is:

1. Run `uv run python scripts/bootstrap_golden_artifacts.py` from the
   repository root.
2. The script calls `paxman.normalize(input, contract)` for each
   curated fixture in :data:`GOLDEN_FIXTURES`.
3. The script strips the non-hash-relevant fields (``id`` and
   ``created_at``) from the resulting artifact.
4. The artifact is serialized via
   :func:`paxman.artifact.serializer.encode_artifact` (which delegates
   to :func:`paxman.serialization.stable_dumps`) and written to
   `tests/fixtures/artifacts/<name>.json`.

Re-running the script produces byte-equal JSON (verified by
``md5sum``). This is required by **exit criterion #8** of Sprint 7.

## How goldens are verified

The replay-equality test pattern is:

```python
def test_replay_reproduces_artifact():
    """The replay of a stored artifact reproduces it byte-for-byte."""
    artifact = paxman.normalize(input_data, contract)
    golden = load_golden("invoice_unresolved_dict_dsl.json")
    assert encode_artifact(artifact) == golden
    assert artifact.replay_hash == golden["replay_hash"]
```

This pattern is implemented in
`tests/integration/test_golden_artifacts.py` (see Sprint 7 D7.3).

## Current goldens (V1)

| File | Source | Status |
|---|---|---|
| `invoice_unresolved_dict_dsl.json` | `paxman.normalize(raw_invoice, DICT_DSL_INVOICE)` | UNRESOLVED (no V1 capabilities) |
| `invoice_unresolved_pydantic.json` | `paxman.normalize(raw_invoice, Invoice)` | UNRESOLVED |
| `invoice_unresolved_json_schema.json` | `paxman.normalize(raw_invoice, JSON_SCHEMA_INVOICE)` | UNRESOLVED |
| `all_v1_types_unresolved.json` | `paxman.normalize(raw_text, DICT_DSL_ALL_V1_TYPES)` | UNRESOLVED |
| `money_unresolved.json` | `paxman.normalize(raw_text, DICT_DSL_WITH_MONEY)` | UNRESOLVED |
| `empty_input_unresolved.json` | `paxman.normalize("", DICT_DSL_INVOICE)` | UNRESOLVED (adversarial) |
| `unicode_input_unresolved.json` | `paxman.normalize(unicode_text, DICT_DSL_INVOICE)` | UNRESOLVED (adversarial) |
| `prompt_injection_unresolved.json` | `paxman.normalize(injection_text, DICT_DSL_INVOICE)` | UNRESOLVED (adversarial) |

All goldens currently have `UNRESOLVED` status because no V1
capabilities are registered in the test environment. This is by
design: the V1 test corpus is the determinism/replay claim, not the
"can the heuristic chain produce resolved values" claim (that comes
with V2 inference).

## Regenerating a single golden

```bash
uv run python scripts/bootstrap_golden_artifacts.py --only invoice_unresolved_dict_dsl
```

This is useful when fixing a bug that affects the artifact shape
(e.g., adding a new field to `ExecutionArtifact`).

## When to regenerate

A golden is **regenerated** when the implementation produces a
different `replay_hash` for the same input+contract+version triple.
Per the V1 determinism guarantee, this should only happen for:

- A change to the artifact shape (Sprint-level schema change).
- A change to the `compute_replay_hash` formula.
- A change to the planner algorithm (Sprint 3 / V2+).
- A change to the V1 capability set (Sprint 4+).

A new Paxman version that changes nothing about the artifact shape
should produce **byte-equal** goldens across versions. (This is
verified by the `paxman_version` check in `paxman.replay()`.)

## Cross-cutting invariants

- The `id` and `created_at` fields are **stripped** from the golden
  to ensure cross-run stability.
- The `replay_hash` is **preserved** — it is the deterministic
  signature that replay tests verify.
- The goldens are written with `stable_dumps` (sorted keys, no
  whitespace, RFC 8785-style) so byte-equality is meaningful.

## See also

- [`REPLAY_AND_DETERMINISM.md`](../../../REPLAY_AND_DETERMINISM.md) — replay model
- [`TESTING_STRATEGY.md`](../../../TESTING_STRATEGY.md) §5 — replay tests
- [`docs/TEST_DATA.md`](../../../docs/TEST_DATA.md) §8.3 — golden artifact policy
