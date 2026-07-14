# Quickstart

This walkthrough goes line by line through [`quickstart.py`](../../quickstart.py) at the root of the repository. After completing it, you will have used Paxman's three public verbs and seen the artifact format.

## Run It

From the repository root:

```bash
uv run python quickstart.py
```

Expected output:

```text
CANONICALIZED -> johndoe@gmail.com
evidence: [('stripped_whitespace', ''), ('lowercased_local_part', ''), ('lowercased_domain', ''), ('stripped_dots_in_local_part', '')]
replay ok
```

If you see that output, the install works and the artifact replays byte-for-byte. Move on to [Verify](verify.md) for what each line means.

## The Code, Line by Line

```python
import paxman
from paxman import Email
```

Two imports. `paxman` is the package; `Email` is the factory for declaring email contracts.

```python
result = paxman.canonicalize(
    "  John.Doe@Gmail.COM  ",
    Email(provider_aliases="gmail"),
)
```

One canonicalize call. The first argument is the input — a string. The second is the contract — an `Email()` value object built with the keyword argument `provider_aliases="gmail"`. The contract declares that Gmail's documented alias rules should apply (dots in the local part are ignored; `+tag` suffixes are stripped; the `googlemail.com` domain is normalized to `gmail.com`).

`canonicalize()` never raises for a valid call. It always returns an `ExecutionArtifact`. The artifact carries the outcome, the canonical value (if any), and a list of evidence entries that explain which rules fired.

```python
print(result.status.name, "->", result.value)
```

`result.status` is a `Status` enum. The five values are `CANONICALIZED`, `INVALID`, `MISSING`, `AMBIGUOUS`, and `UNSUPPORTED`. For this input the outcome is `CANONICALIZED` — the artifact's `value` is the canonical form `"johndoe@gmail.com"`.

```python
print("evidence:", [(e.rule, e.detail) for e in result.evidence])
```

The evidence list records what happened during canonicalization. Each entry is an `Evidence` with a `rule` name, a human-readable `detail`, and a `provenance` citation (the source of the rule — see [Why rules cite sources](../concepts/why-rules-cite-sources.md)). For this input, four rules fired in order:

1. `stripped_whitespace` — the leading and trailing spaces were removed.
2. `lowercased_local_part` — `John.Doe` was lowercased to `john.doe`.
3. `lowercased_domain` — `Gmail.COM` was lowercased to `gmail.com`.
4. `stripped_dots_in_local_part` — Gmail's rule: the dots in `john.doe` were removed.

```python
rehydrated = paxman.replay(result, Email(provider_aliases="gmail"))
assert rehydrated == result
print("replay ok")
```

`replay()` rehydrates the artifact from its stored form. It does **not** re-execute the capability. The contract is the same one used to create the artifact. The assertion `rehydrated == result` checks byte-for-byte equality. If the artifact was tampered with, or if the version stamp does not match the current environment, `replay()` raises `VersionMismatchError`.

This property — that an artifact is independently verifiable without re-running the transformation — is one of the three guarantees Paxman makes. See [The three invariants](../concepts/the-three-invariants.md) for the full set.

## What You Have Seen

- The three public verbs: `paxman.canonicalize()`, `paxman.replay()`, and `paxman.register_capability()`.
- The five outcomes of a canonicalize call (you saw one of them: `CANONICALIZED`).
- The evidence list and its `rule` / `detail` / `provenance` fields.
- The replay guarantee, demonstrated by `assert rehydrated == result`.

## Next

- [Verify the install](verify.md) — a small checklist of things to confirm in your own setup.
- [What canonicalization is](../concepts/canonicalization.md) — the conceptual background.
