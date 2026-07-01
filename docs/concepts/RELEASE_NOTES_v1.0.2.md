# Paxman v1.0.2 Release Notes

**Released:** 2026-07-03 (Friday patch release per the
[v1.0.x milestone](https://github.com/nexusnv/paxman/milestone/3) policy)

**Type:** Patch release. No breaking changes.

**Previous version:** v1.0.1

---

## TL;DR

Paxman v1.0.2 is a Friday patch release that fixes all 7 open bugs
filed against v1.0.0 in the `v1.0.x` milestone. The release is safe
to upgrade for any v1.0.0 or v1.0.1 caller:

- **No breaking changes.** Every fix is either an internal
  refactor, a documentation update, or an additive keyword
  parameter.
- **No new dependencies.** No changes to the core
  `pyproject.toml` package list.
- **No new public types or functions.** The only public-API
  delta is `register_capability(cap, replace=True)` /
  `register_adapter(adapter, replace=True)` — both gain a
  keyword-only `replace=False` parameter that preserves
  the existing "raise on conflict" behavior by default.

Upgrade in place: `pip install paxman==1.0.2`.

---

## What's fixed

| # | Severity | Area | Summary |
|---|---|---|---|
| [#58](https://github.com/nexusnv/paxman/issues/58) | medium | Pydantic adapter | `Optional[Annotated[T, ...]]` is now accepted (was `UNSUPPORTED_FIELD_TYPE`). |
| [#59](https://github.com/nexusnv/paxman/issues/59) | medium | Public API | `register_capability()` and `register_adapter()` now accept `replace: bool = False`. |
| [#60](https://github.com/nexusnv/paxman/issues/60) | medium | Artifact | `capability_versions` is now derived from the reconciled evidence (single source of truth). |
| [#61](https://github.com/nexusnv/paxman/issues/61) | medium | Pydantic adapter | `float → DECIMAL` conflation is now documented loudly. |
| [#62](https://github.com/nexusnv/paxman/issues/62) | low | Pydantic adapter | `_is_optional()` uses `types.UnionType` identity, not a fragile `__name__` check. |
| [#64](https://github.com/nexusnv/paxman/issues/64) | low | Reconciler | Layer-boundary violation removed: `_check_constraint` extracted to `paxman.validation.constraints`. |

See the [full changelog](../operations/changelog.md) for per-bug
details and migration notes.

---

## Who should upgrade

**Everyone.** v1.0.2 is a safe drop-in replacement for v1.0.0 and
v1.0.1. The fixes address real ergonomic issues that affected
common caller patterns (Optional[Annotated[...]] in Pydantic,
re-registration during development, the reconciler's import
violation, replay integrity for normalized artifacts with
multi-version capabilities).

**Especially recommended** if you:

- Use `Optional[Annotated[T, Field(...)]]` in Pydantic contracts
  (#58)
- Hot-reload capabilities or adapters during development (#59)
- Replay artifacts that were normalized with a capability that
  has multiple versions (#60)
- Use `float` for non-money numeric fields in Pydantic contracts
  and were surprised by money-like behavior (#61)
- Maintain a fork of `paxman` that touches the reconciler /
  capabilities boundary (#64)

---

## What's *not* fixed

These are tracked for V2 and out of scope for a v1.0.x bugfix:

- A proper `FLOAT` field type (currently `float` maps to
  `DECIMAL`). The proper fix requires changes to the Reconciler,
  all 4 adapters, and existing artifacts — too large for a patch
  release. (#61, Option B — tracked for V2)
- The `DiagnosticCode` enum remains a closed V1 set; #60's
  conflict warning uses `structlog` rather than a new
  `DiagnosticCode` value because adding a new code requires an
  ADR per `PACKAGE_STRUCTURE.md` §5.4 invariant #5.

---

## Upgrade guide

```bash
pip install --upgrade paxman==1.0.2
```

No code changes required for v1.0.0 / v1.0.1 callers. If you
imported the private helper `_check_constraint` from
`paxman.capabilities.v1.validation` in your own code, it still
works via the re-export shim — but you should switch to the new
canonical location `paxman.validation.constraints.check_constraint`.

---

## Acknowledgments

All 7 bug reports were exceptionally high quality: each included a
minimal reproducer, a root-cause analysis, and a recommended fix
option. The fixes themselves are largely mechanical translations of
the recommended approaches in the issue bodies. Thank you to everyone
who reported, triaged, and reviewed these bugs.
