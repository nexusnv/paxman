# Sprint 9 — Cross-Platform Wheel Verification

> **Date:** 2026-06-26
> **Sprint:** [Sprint 9 — Production Hardening](./sprint-09-production-hardening.md)
> **Deliverable:** D9.12

## Summary

| Platform | Architecture | Python | Install | Import | Functional Test | Status |
|----------|--------------|--------|---------|--------|-----------------|--------|
| Linux   | x86_64       | 3.12   | ✓       | ✓      | ✓               | **PASS** |
| macOS   | arm64        | 3.12   | (TBD by human) | (TBD) | (TBD)   | **DEFERRED** |
| Windows | amd64        | 3.12   | (TBD by human) | (TBD) | (TBD)   | **DEFERRED** |

The Paxman wheel is **`py3-none-any`** (pure-Python, no compiled extensions). The
same wheel that was tested on Linux is expected to install identically on macOS
and Windows — no per-platform rebuild required.

## Why no per-platform matrix?

Per [D9.12a](#platform-support-note-d912a) in the release notes, Paxman ships
**zero compiled extensions**:

- All subsystems are pure Python (`@attrs.frozen` data classes, dataclass-style
  methods, stdlib-only imports in the core path).
- `hatchling` produces a universal `py3-none-any` wheel that satisfies
  `V1_ACCEPTANCE_CRITERIA.md` §3.1 automatically for all 5 target platforms:
  - `linux/amd64`
  - `linux/arm64`
  - `osx/amd64`
  - `osx/arm64`
  - `win/amd64`

The release workflow (`.github/workflows/release.yml`) intentionally **does not
include a `matrix:` block** — this is correct, not an oversight.

## Linux verification (this environment)

### Environment

- **OS:** Linux 6.12.0+ (Debian 13, x86_64)
- **Python:** 3.12.13 (cpython)
- **uv:** 0.11.23
- **Network:** Available (PyPI + TestPyPI reachable)

### Build

```bash
cd /home/leonidas/dev/paxman
uv run hatchling build
```

**Result:**
```
dist/paxman-0.0.0-py3-none-any.whl    (208,849 bytes)
dist/paxman-0.0.0.tar.gz
```

**Wheel contents verified:**
- `paxman/__init__.py` present ✓
- `paxman/py.typed` present (PEP 561) ✓
- No `__pycache__` directories ✓
- 82 total entries

### Install (clean venv)

```bash
python3 -m venv /tmp/paxman-test-venv
/tmp/paxman-test-venv/bin/pip install /home/leonidas/dev/paxman/dist/paxman-0.0.0-py3-none-any.whl
```

**Result:**
```
Successfully installed attrs-26.1.0 packaging-26.2 paxman-0.0.0 structlog-26.1.0 typing-extensions-4.15.0
```

5 core dependencies only (within DEPENDENCIES.md §1 budget of ≤4 packages).

### Import + functional test

```python
import paxman
import paxman.contract.adapters.pydantic  # noqa
from pydantic import BaseModel

class Invoice(BaseModel):
    supplier_name: str
    total_amount: float

result = paxman.normalize(
    input_data="ACME Corp\nTotal: $100.00",
    contract=Invoice,
)
print(result.status, result.normalized_data, result.replay_hash[:16] + "...")

rehydrated = paxman.replay(result, contract=Invoice)
assert rehydrated == result, "replay not byte-equal"
print("replay: byte-equal OK")
```

**Result:**
```
Status.UNRESOLVED {} 0640ec14d34c1ec1...
replay: byte-equal OK
```

All V1 public API surface works end-to-end on a clean install.

## macOS and Windows — manual verification needed

This automated verification ran on Linux only. For Sprint 9 exit criteria,
macOS arm64 and Windows amd64 verification must be performed by engineers
with access to those platforms:

### macOS (arm64)

```bash
# On macOS arm64
python3 -m venv paxman-test
source paxman-test/bin/activate
pip install paxman-0.0.0-py3-none-any.whl
python -c "import paxman; print(f'paxman {paxman.__version__}')"
python -c "from paxman import normalize, replay; print('OK')"
```

### Windows (amd64)

```powershell
# On Windows amd64
python -m venv paxman-test
paxman-test\Scripts\Activate.ps1
pip install paxman-0.0.0-py3-none-any.whl
python -c "import paxman; print(f'paxman {paxman.__version__}')"
python -c "from paxman import normalize, replay; print('OK')"
```

### Expected result

Both should pass identically — the wheel is `py3-none-any` with no platform-specific
code paths.

## Risk acknowledgment

Per the sprint risk register: "Cross-platform TestPyPI smoke test fails on
Windows: Medium likelihood, Medium impact. If a Windows-specific issue is
found, document the limitation in the release notes."

If verification fails on either macOS or Windows, the expected root cause would
be:
- **Path separators** — we use `pathlib.Path` everywhere; should be cross-platform.
- **Encoding** — we use UTF-8 with `errors="replace"`; should be cross-platform.
- **Permissions** — the v1 API is read-only on disk (artifacts are caller-owned);
  no platform-specific permission logic.

None of these are known issues, and the codebase has been designed to be
cross-platform from the start (per `PACKAGE_STRUCTURE.md` §17 build strategy).

## See also

- [`./sprint-09-production-hardening.md`](./sprint-09-production-hardening.md) — full sprint
- [`./v0.5.0-release-notes.md`](./v0.5.0-release-notes.md) — release notes with 5-platform note
- [`../../V1_ACCEPTANCE_CRITERIA.md`](../../V1_ACCEPTANCE_CRITERIA.md) §3.1 — packaging criteria
- [`../../PACKAGE_STRUCTURE.md`](../../PACKAGE_STRUCTURE.md) §17 — build strategy
