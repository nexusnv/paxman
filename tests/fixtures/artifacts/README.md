# Golden Execution Artifacts

This directory contains the **golden `ExecutionArtifact` JSON files** used by replay-equality tests. Each golden artifact is the **expected** output of `paxman.normalize()` for a specific `(input, contract)` pair.

## Why golden artifacts matter

Paxman's determinism and replay claims rest on the `replay_hash` being stable for the same `(input, contract, version)` triple. The golden artifacts in this directory are the **ground truth** for what the artifact should look like — including the `replay_hash`.

When the implementation produces a different `replay_hash` for the same input, the test fails. This is how we catch determinism regressions.

See [REPLAY_AND_DETERMINISM.md](../../../../REPLAY_AND_DETERMINISM.md) for the full replay model.

## Current goldens (V1, 8 files)

All goldens currently have `UNRESOLVED` status because no V1 capabilities are registered in the test environment. This is by design: the V1 test corpus is the determinism/replay claim, not the "can the heuristic chain produce resolved values" claim (that comes with V2 inference).

The catalog is the **single source of truth** — see [`_catalog.py`](./_catalog.py). Both `scripts/bootstrap_golden_artifacts.py` and `tests/integration/test_golden_artifacts.py` import from it.

| File | Source | Status |
|---|---|---|
| `invoice_unresolved_dict_dsl.json` | `paxman.normalize(raw_invoice, DICT_DSL_INVOICE)` | `UNRESOLVED` |
| `invoice_unresolved_pydantic.json` | `paxman.normalize(raw_invoice, Invoice)` | `UNRESOLVED` |
| `invoice_unresolved_json_schema.json` | `paxman.normalize(raw_invoice, JSON_SCHEMA_INVOICE)` | `UNRESOLVED` |
| `all_v1_types_unresolved.json` | `paxman.normalize(raw_text, DICT_DSL_ALL_V1_TYPES)` | `UNRESOLVED` |
| `money_unresolved.json` | `paxman.normalize(raw_text, DICT_DSL_WITH_MONEY)` | `UNRESOLVED` |
| `empty_input_unresolved.json` | `paxman.normalize("", DICT_DSL_INVOICE)` | `UNRESOLVED` (adversarial) |
| `unicode_input_unresolved.json` | `paxman.normalize(unicode_text, DICT_DSL_INVOICE)` | `UNRESOLVED` (adversarial) |
| `prompt_injection_unresolved.json` | `paxman.normalize(prompt_injection_text, DICT_DSL_INVOICE)` | `UNRESOLVED` (adversarial) |

> **Note:** the "planned" goldens in the original README (e.g. `invoice_success.json`,
> `quotation_success.json`) require real resolver capabilities registered in the
> test environment. Those land in V2 with the inference provider. V1 is the
> determinism/replay claim only.

## How goldens are generated

All goldens in this directory are **bootstrapped from real `paxman.normalize()` calls** — never predicted. The generation procedure is:

1. Run `uv run python scripts/bootstrap_golden_artifacts.py` from the repository root.
2. The script calls `paxman.normalize(input, contract)` for each curated fixture in
   [`GOLDEN_FIXTURES`](./_catalog.py).
3. The script strips the non-hash-relevant fields (`id` and `created_at`) from
   the resulting artifact.
4. The artifact is serialized via `paxman.artifact.serializer.encode_artifact`
   (which delegates to `paxman.serialization.stable_dumps`) and written to
   `tests/fixtures/artifacts/<name>.json`.

Re-running the script produces byte-equal JSON (verified by `md5sum`).
See [`GENERATION.md`](./GENERATION.md) for the full procedure and the
rationale for stripping `id` and `created_at`.

## How goldens are verified

The replay-equality test pattern (in `tests/integration/test_golden_artifacts.py`):

```python
def test_replay_reproduces_artifact():
    """The replay of a stored artifact reproduces it byte-for-byte."""
    artifact = paxman.normalize(input_data, contract)

    # The golden has two distinct representations:
    #   - `golden_raw_bytes`: the file's bytes as read from disk — used
    #     for byte-for-byte equality against the freshly-encoded
    #     artifact (the RFC 8785-style canonical JSON form).
    #   - `golden_parsed`: the same golden after ``json.load`` — used
    #     to read specific hash-relevant fields like ``replay_hash``
    #     and to introspect structure.
    golden_path = "tests/fixtures/artifacts/invoice_unresolved_dict_dsl.json"
    golden_raw_bytes = pathlib.Path(golden_path).read_bytes()
    golden_parsed = json.loads(golden_raw_bytes)

    # 1. Byte-for-byte equality of the encoded artifact vs. the on-disk golden.
    assert encode_artifact(artifact) == golden_raw_bytes

    # 2. The fresh artifact's ``replay_hash`` matches the golden's ``replay_hash``.
    assert artifact.replay_hash == golden_parsed["replay_hash"]
```

The same test also runs in a fresh Python subprocess
(`tests/integration/test_replay_golden_reproducibility.py`) to catch GIL
or module-cache contamination that in-process tests cannot detect.

## How to regenerate goldens

To regenerate all goldens:

```bash
uv run python scripts/bootstrap_golden_artifacts.py
```

To regenerate a single golden:

```bash
uv run python scripts/bootstrap_golden_artifacts.py --only invoice_unresolved_dict_dsl
```

This is useful when fixing a bug that affects the artifact shape (e.g., adding
a new field to `ExecutionArtifact`).

## When to regenerate

A golden is **regenerated** when the implementation produces a different
`replay_hash` for the same input+contract+version triple. Per the V1
determinism guarantee, this should only happen for:

- A change to the artifact shape (Sprint-level schema change).
- A change to the `compute_replay_hash` formula.
- A change to the planner algorithm.
- A change to the V1 capability set.
- A `paxman_version` bump (the version is a hash-relevant field).

The `paxman_version` check in `paxman.replay()` rejects artifacts produced
by a different Paxman version, which is what makes the cross-version byte
differences safe (a new version never silently replays a stale golden).

## Cross-cutting invariants

- The `id` and `created_at` fields are **stripped** from the golden to
  ensure cross-run stability.
- The `replay_hash` is **preserved** — it is the deterministic signature
  that replay tests verify.
- The goldens are written with `stable_dumps` (sorted keys, no whitespace,
  RFC 8785-style) so byte-equality is meaningful.

## See also

- [`REPLAY_AND_DETERMINISM.md`](../../../../REPLAY_AND_DETERMINISM.md) — replay model
- [`V1_ACCEPTANCE_CRITERIA.md`](../../../../V1_ACCEPTANCE_CRITERIA.md) — V1 definition of done
- [`docs/TEST_DATA.md §8.3`](../../../../docs/TEST_DATA.md) — golden artifact policy
- [`TESTING_STRATEGY.md §5 Replay Tests`](../../../../TESTING_STRATEGY.md)
- [`GENERATION.md`](./GENERATION.md) — generation procedure + bootstrap script invocation
- [`_catalog.py`](./_catalog.py) — single source of truth for the 8 goldens
