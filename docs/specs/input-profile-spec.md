# InputProfile Module Specification

> **Status:** Accepted
> **Date:** 2026-06-22
> **Deciders:** Paxman core team
> **Related docs:** [ARCHITECTURE.md §4.2](../../ARCHITECTURE.md), [PACKAGE_STRUCTURE.md §4.2](../../PACKAGE_STRUCTURE.md), [ADR-0002](../adr/0002-rule-based-planner-v1.md), [REPLAY_AND_DETERMINISM.md](../../REPLAY_AND_DETERMINISM.md)

---

## 1. Overview

`InputProfile` is a **lightweight metadata structure** derived from raw input before any capability invocation. It sits between input reception and `planner.plan(...)`, providing the Planner with the minimal signal it needs to make heuristic decisions without re-scanning the input.

Per [ARCHITECTURE.md §4.2](../../ARCHITECTURE.md), the Planner is a **pure function** over `(CanonicalContract, InputProfile, Budget, Policy, CapabilityRegistry)`. The InputProfile is the Planner's view of the input — not the input itself. It is derived once, passed into the Planner, and never mutated.

**Why it exists:** The Planner's heuristic chain needs to answer questions like "is this input empty?", "is this JSON or plain text?", "how dense is the content?" — without invoking capabilities (which is the Executor's job). InputProfile answers these questions in O(input_size) time with zero side effects.

**Where it lives:** `planner/input_profile.py` per [PACKAGE_STRUCTURE.md §4.2](../../PACKAGE_STRUCTURE.md). It is an internal module; not re-exported in `api/`.

---

## 2. Design Goals

1. **Lightweight.** O(input_size) once, cached via `content_hash`. No multi-pass scanning, no external calls.
2. **Deterministic.** Same input bytes → same InputProfile, byte-for-byte. No clock, no I/O, no random state.
3. **Pure.** No capability invocation. The profile is derived from raw bytes alone. Per [PACKAGE_STRUCTURE.md §4.2](../../PACKAGE_STRUCTURE.md): "lightweight input classifier (no capability invocation)."
4. **Side-effect-free constructor.** The `make_profile()` function is a pure function. Per [ADR-0002](../adr/0002-rule-based-planner-v1.md), the Planner is a pure function; its inputs must be equally pure.
5. **Five-field V1 surface.** Cap at 5 fields per the risk register in the sprint-00 document. Defer content classification (e.g., "is this a financial document?") to V2.
6. **Constructed at most once per `paxman.normalize()` call.** The Planner receives the already-constructed profile. No lazy construction, no re-derivation.

---

## 3. Data Model

```python
from attrs import frozen
from typing import Literal

InputType = Literal[
    "text",
    "html",
    "csv",
    "json",
    "pdf_text",
    "email",
    "empty",
    "unknown",
]


@frozen
class InputProfile:
    input_type: InputType
    size: int
    content_hash: str  # 64-char lowercase hex (SHA-256)
    density: float     # 0.0–1.0
    is_empty: bool
```

### 3.1 Field Definitions

| Field | Type | Range | Semantics | Readers |
|---|---|---|---|---|
| `input_type` | `InputType` | 8 enum values | Coarse classification of the raw input format. Drives heuristic selection in the Planner (e.g., "JSON input → try regex before inference"). | Planner (`heuristics.py`) |
| `size` | `int` | `>= 0` | Byte count of the normalized input (UTF-8 encoded if `str` was provided). Used by Planner to estimate cost and by Budget to reject oversized inputs. | Planner, Budget |
| `content_hash` | `str` | 64-char lowercase hex | SHA-256 hex digest of the normalized bytes. Used for replay hash composition ([REPLAY_AND_DETERMINISM.md §2.1](../../REPLAY_AND_DETERMINISM.md)) and as a cache key. | Artifact (`replay_hash`), Planner (cache key) |
| `density` | `float` | `0.0 <= density <= 1.0` | Ratio of non-whitespace characters to total bytes. Heuristic signal for "is this a token-heavy LLM candidate?" Used by Planner to short-circuit capability selection. | Planner (`scoring.py`) |
| `is_empty` | `bool` | `True` / `False` | `True` if `size == 0` or the input is whitespace-only. The Planner short-circuits to `UNRESOLVED` for all fields when `is_empty` is `True`. | Planner (`heuristics.py`) |

### 3.2 Validation Rules

The `@frozen` decorator enforces immutability. Additional invariants are validated at construction time:

| Rule | Enforcement |
|---|---|
| `size >= 0` | `attrs` validator; raises `ValueError` |
| `0.0 <= density <= 1.0` | `attrs` validator; raises `ValueError` |
| `content_hash` is 64-char lowercase hex | `attrs` validator; raises `ValueError` |
| `input_type` is one of the 8 `Literal` values | `typing.Literal` check at type-check time; runtime guard in `make_profile()` |

---

## 4. Construction Algorithm

`InputProfile` is constructed by the `make_profile()` function. It is a **pure function**: no I/O, no clock, no random state, no capability invocation.

### 4.1 Signature

```python
def make_profile(input_data: str | bytes) -> InputProfile:
    """Derive an InputProfile from raw input.

    Args:
        input_data: Raw input as str or bytes. If str, encoded as UTF-8
            with errors="replace".

    Returns:
        A frozen InputProfile with 5 fields.
    """
```

### 4.2 Algorithm

```
function make_profile(input_data):
    1. Normalize to bytes:
       - If input_data is str → encode as UTF-8 with errors="replace"
       - If input_data is bytes → use as-is

    2. size = len(normalized_bytes)

    3. content_hash = sha256(normalized_bytes).hexdigest()

    4. is_empty = (size == 0) OR (normalized_bytes.strip() == b"")

    5. input_type = classify(normalized_bytes)    // see §5

    6. density = compute_density(normalized_bytes, input_type)  // see §6

    7. return InputProfile(
           input_type=input_type,
           size=size,
           content_hash=content_hash,
           density=density,
           is_empty=is_empty,
       )
```

### 4.3 Determinism Guarantee

Every step is deterministic:

- UTF-8 encoding with `errors="replace"` is deterministic (replacement character `U+FFFD` encodes as `b'\xef\xbf\xbd'`).
- `len()` is deterministic.
- `sha256` is deterministic over the same bytes.
- `classify()` is a pure function over bytes (§5).
- `compute_density()` is a pure function over bytes and input_type (§6).

No step reads the clock, generates random numbers, or performs I/O.

---

## 5. Input Type Classification (`classify`)

The `classify()` function determines the coarse format of the input. Rules are evaluated **in order**; the first match wins.

### 5.1 Rules Table

| Priority | Condition | Result | Rationale |
|---|---|---|---|
| 1 | `size == 0` | `"empty"` | No bytes to classify. |
| 2 | First 16 bytes start with `%PDF-` | `"pdf_text"` | Text extracted from a PDF (not raw PDF binary; raw PDF detection is V2). |
| 3 | First non-whitespace byte is `{` or `[` AND `json.loads()` succeeds | `"json"` | Valid JSON object or array. |
| 4 | First 5 bytes are `From ` (with trailing space) AND `Subject:` header present in first 4096 bytes | `"email"` | RFC 822 email format. |
| 5 | Contains `<html` or `<!DOCTYPE html` (case-insensitive, first 4096 bytes) | `"html"` | HTML document. |
| 6 | First non-whitespace line contains `,` more than 2 times | `"csv"` | Heuristic CSV detection (comma-separated values). |
| 7 | None of the above match | `"text"` | Default: treat as plain text. |
| 8 | Classification fails (e.g., binary garbage causes decode errors in rule evaluation) | `"unknown"` | Fallback for unclassifiable input. |

### 5.2 Notes

- **Rule 2 (PDF):** This detects *text-extracted* PDF content (e.g., output from `pdftotext`). Raw PDF binary (`%PDF-1.4` followed by binary streams) is V2. In V1, the `pdf_text` type signals that the input is already human-readable text extracted from a PDF.
- **Rule 3 (JSON):** `json.loads()` is called on the first 8192 bytes (or the full input if smaller) to avoid parsing a 100 MB JSON blob during classification. If parsing fails, the rule does not match.
- **Rule 4 (Email):** The `Subject:` header must appear in the first 4096 bytes to avoid scanning large inputs for email headers that may not exist.
- **Rule 5 (HTML):** Case-insensitive match on the first 4096 bytes. This catches `<!DOCTYPE HTML>`, `<HTML>`, and variations.
- **Rule 6 (CSV):** A simple heuristic. A line with 3+ commas is likely CSV. This is intentionally coarse; false positives for comma-heavy text are acceptable (the Planner can still use other heuristics).
- **Rule 8 (Unknown):** Reached only when the input contains binary data that causes errors in the classification rules (e.g., `UnicodeDecodeError` during HTML/JSON matching). Plain binary that passes all rules without matching falls through to `"text"`.

---

## 6. Density Computation (`compute_density`)

Density is a **heuristic signal** for the Planner, not a hard constraint. It answers: "what fraction of the input is non-whitespace content?"

### 6.1 Formula

```
function compute_density(normalized_bytes, input_type):
    if input_type in ("empty", "unknown"):
        return 0.0

    // Decode to text (UTF-8 with replacement)
    text = normalized_bytes.decode("utf-8", errors="replace")

    // Count non-whitespace characters
    non_ws = len(text.replace(" ", "").replace("\t", "").replace("\n", "").replace("\r", ""))

    // Density = non-whitespace chars / total bytes
    return non_ws / len(normalized_bytes) if len(normalized_bytes) > 0 else 0.0
```

### 6.2 Per-Input-Type Behavior

| `input_type` | Density computation |
|---|---|
| `"text"`, `"email"`, `"html"`, `"csv"`, `"json"`, `"pdf_text"` | `len(non_whitespace_text) / size` |
| `"empty"` | `0.0` (hardcoded) |
| `"unknown"` | `0.0` (hardcoded) |

### 6.3 Semantics

- **Range:** `0.0` (all whitespace or binary) to `1.0` (zero whitespace). Typical text inputs have density `0.7`–`0.9`.
- **Heuristic purpose:** The Planner uses density to short-circuit decisions like "is this a token-heavy LLM candidate?" A density near `0.0` suggests the input is mostly whitespace or binary; a density near `1.0` suggests dense text.
- **Not a hard signal:** Density does not determine capability selection directly. It is one input among many (alongside `input_type`, `size`, `is_empty`) that the Planner's heuristic chain considers.
- **V2 note:** Content-aware density (e.g., "how much of this HTML is actual content vs. tags?") is deferred to V2.

---

## 7. Worked Example

**Input:** `b"Hello, World!\n"`

### Step-by-step trace

| Step | Operation | Result |
|---|---|---|
| 1 | Normalize to bytes | `b"Hello, World!\n"` (already bytes) |
| 2 | `size = len(b"Hello, World!\n")` | `14` |
| 3 | `content_hash = sha256(b"Hello, World!\n").hexdigest()` | `"d9014c4624844aa5bac314773d6b689ad467fa4e1d1a50a1b8a99d5a95f72ff5"` (example; actual hash computed at impl time) |
| 4 | `is_empty = (14 == 0) or (b"Hello, World!\n".strip() == b"")` | `False` |
| 5 | `classify(b"Hello, World!\n")` | `"text"` (no JSON markers, no HTML, no CSV commas, no email headers, no PDF prefix) |
| 6 | `compute_density(b"Hello, World!\n", "text")` | Non-whitespace: `Hello,World!` = 12 chars. `12 / 14 = 0.857` |

### Result

```python
InputProfile(
    input_type="text",
    size=14,
    content_hash="d9014c4624844aa5bac314773d6b689ad467fa4e1d1a50a1b8a99d5a95f72ff5",
    density=0.857,
    is_empty=False,
)
```

---

## 8. Edge Cases

### EC1: Empty input

**Input:** `b""`

| Field | Value | Reasoning |
|---|---|---|
| `input_type` | `"empty"` | Rule 1: `size == 0` |
| `size` | `0` | `len(b"")` |
| `content_hash` | `"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"` | SHA-256 of empty bytes |
| `density` | `0.0` | Hardcoded for `"empty"` type |
| `is_empty` | `True` | `size == 0` |

**Planner behavior:** Short-circuits to `UNRESOLVED` for all fields.

### EC2: Whitespace-only input

**Input:** `b"   \n\t  "`

| Field | Value | Reasoning |
|---|---|---|
| `input_type` | `"text"` | No classification rule matches (not empty, no JSON/HTML/CSV/email/PDF markers) |
| `size` | `7` | `len(b"   \n\t  ")` |
| `content_hash` | SHA-256 of `b"   \n\t  "` | Deterministic |
| `density` | `0.0` | `0 non-whitespace chars / 7 = 0.0` |
| `is_empty` | `True` | `normalized_bytes.strip() == b""` |

**Planner behavior:** Same as EC1 — short-circuits to `UNRESOLVED`.

### EC3: Invalid UTF-8

**Input:** `b"\xff\xfe\x00\x01"` (raw binary, not valid UTF-8)

| Field | Value | Reasoning |
|---|---|---|
| `input_type` | `"unknown"` | Classification rules fail on binary input; fallback to `"unknown"` |
| `size` | `4` | `len(b"\xff\xfe\x00\x01")` |
| `content_hash` | SHA-256 of `b"\xff\xfe\x00\x01"` | Deterministic |
| `density` | `0.0` | Hardcoded for `"unknown"` type |
| `is_empty` | `False` | `size > 0` and `strip() != b""` |

**Planner behavior:** Treats as unclassifiable. May skip capabilities that require text input.

### EC4: Very large input

**Input:** 10 MB of text, or 100 MB of text.

| Aspect | Behavior |
|---|---|
| Algorithm complexity | O(input_size). No special handling. |
| 10 MB text | ~50 ms in CPython (SHA-256 dominates). |
| 100 MB text | ~500 ms in CPython. |
| Budget interaction | The Planner may reject large inputs via `Budget.max_input_size_bytes` (if configured). InputProfile construction itself has no size limit. |
| Memory | The full input is held in memory during construction. V2 may add streaming/chunked profiling. |

**No special handling in V1.** The caller is responsible for size gating before calling `paxman.normalize()`.

### EC5: `str` input with non-UTF-8 characters

**Input:** `"Hello \ud800 World"` (lone surrogate, invalid in UTF-8)

| Field | Value | Reasoning |
|---|---|---|
| Encoding | `b"Hello \xef\xbf\xbd World"` | UTF-8 with `errors="replace"` replaces lone surrogate with `U+FFFD` (encoded as `\xef\xbf\xbd`) |
| `content_hash` | SHA-256 of the replacement-encoded bytes | Deterministic per the replacement policy |
| All other fields | Computed normally from the replacement-encoded bytes | |

**Important:** The `content_hash` of a `str` input may differ from the hash of the "same" string encoded differently. This is by design — the hash reflects the actual bytes that were profiled.

### EC6: Mismatched `str`/`bytes` input

**Input:** A `dict` or `list` (already parsed JSON).

**Behavior:** `make_profile()` accepts `str | bytes` only. If the caller passes a `dict` or `list`, it is the caller's responsibility to serialize it first (e.g., `json.dumps(data).encode("utf-8")`). The `api.normalize()` function handles this serialization before calling `make_profile()`.

**Rationale:** InputProfile operates on bytes. It does not know about structured data. The API layer is the serialization boundary.

---

## 9. Out of Scope (V1)

The following features are explicitly **deferred to V2**:

| Feature | Reason | V2 Ticket |
|---|---|---|
| Content classification (financial doc, legal doc, invoice, etc.) | Requires capability invocation or ML model. Violates "no capability invocation" invariant. | — |
| Language detection | Requires a language model or heuristic dictionary. Out of scope for a lightweight classifier. | — |
| OCR confidence / image density | V1 supports `text/plain` and `text/html` only. Image/PDF binary inputs are V2. | — |
| Charset detection (chardet/charset-normalizer) | V1 assumes UTF-8 with replacement fallback. Charset detection adds a dependency and latency. | — |
| Caching across `paxman.normalize()` calls | The Planner builds InputProfile once per call. Cross-call caching is the caller's job via `content_hash`. | — |
| Streaming / chunked input profiling | V1 requires the full input in memory. Chunked profiling is V2 for large-file use cases. | — |

---

## 10. See Also

- [ARCHITECTURE.md §4.2](../../ARCHITECTURE.md) — Planner subsystem design, heuristic ordering, InputProfile's role in the planning pipeline.
- [PACKAGE_STRUCTURE.md §4.2](../../PACKAGE_STRUCTURE.md) — Module layout for `planner/`, including `input_profile.py`.
- [ADR-0002: Rule-Based Planner for V1](../adr/0002-rule-based-planner-v1.md) — Why the Planner is a pure function; InputProfile's purity requirement.
- [REPLAY_AND_DETERMINISM.md](../../REPLAY_AND_DETERMINISM.md) — How `content_hash` feeds into the replay hash and cache key.
