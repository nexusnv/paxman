# How to Add a New Capability

> **Status:** V1
> **Audience:** Paxman users who want to add a new atomic
> extraction/validation operation (OCR, barcode decoding, custom
> regex library, …).
> **Related docs:** [EXTENDING.md §2](../reference/extending.md) (the full
> SPI walkthrough), [docs/concepts/capabilities.md](../concepts/capabilities.md)
> (what a capability is), [ADR-0005](../adr/0005-confidence-ownership.md)
> (why capabilities don't assign confidence).

This guide is a **focused quick-start** for adding a new capability
to Paxman. The full SPI walkthrough is in
[EXTENDING.md §2](../reference/extending.md); this document is a 5-minute
checklist.

---

## 1. When to add a new capability

Add a new capability when:

- You have a domain-specific extraction or validation step that
  doesn't fit the V1 surface.
- You want to ship a new algorithm (e.g. a custom regex library, a
  custom lookup table, a custom model wrapper).
- You are shipping a new field type that the V1 capabilities cannot
  handle.

Do **not** add a new capability when:

- The operation can be expressed as a V1 capability (e.g. don't add
  `phone_extraction` — use `regex_extraction` with a phone regex).
- The operation is a "policy" rather than an operation (use
  `ResolutionPolicy` or `ContractPolicy` instead).
- The operation needs to read the contract or the raw input directly
  (it must go through `CapabilityContext`).

---

## 2. The Capability SPI

```python
from typing import Protocol
from paxman.protocols import CapabilitySpec, CapabilityContext, CapabilityResult


class Capability(Protocol):
    """SPI: an atomic operation."""

    @property
    def spec(self) -> CapabilitySpec:
        """Metadata describing the capability."""
        ...

    def invoke(self, ctx: CapabilityContext) -> CapabilityResult:
        """Run the capability on the given context.

        Returns:
            CapabilityResult with candidates, evidence_refs, and diagnostics.
            MUST NOT include a `confidence` field.

        Raises:
            CapabilityError: if the capability fails to run.
        """
        ...
```

`CapabilityResult` is **frozen, slotted**; it has `candidates`,
`evidence_refs`, and `diagnostics` — and **no `confidence` field**
(per [ADR-0005](../adr/0005-confidence-ownership.md)).

---

## 3. Step-by-step

### 3.1 Pick a capability id and version

Choose a stable `id` (e.g. `"ocr"`, `"barcode"`, `"date_parser"`).
Choose a semver `version` (e.g. `"1.0"`, `"1.0.1"`). The registry
is keyed on `(id, version)`; the planner picks the highest
registered version.

### 3.2 Declare the CapabilitySpec

The `spec` tells the planner what the capability does, its
`FieldType` in/out, its tier, and its cost:

```python
import attrs
from decimal import Decimal

from paxman.capabilities.base import Capability, CapabilityContext
from paxman.capabilities.result import (
    CapabilityResult,
    Candidate,
    Diagnostic,
    DiagnosticCode,
    DiagnosticSeverity,
    EvidenceRef,
)
from paxman.capabilities.spec import CapabilitySpec, CapabilityTier, CostHint
from paxman.types import FieldType


@attrs.frozen(slots=True)
class DateParserCapability:
    """Parse a date string from a CapabilityContext."""

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            id="date_parser",
            version="1.0",
            input_type=FieldType.STRING,
            output_type=FieldType.DATE,
            tier=CapabilityTier.LOCAL_DETERMINISTIC,
            cost_estimate=CostHint(
                usd=Decimal("0.0"),
                ms=10,
                invocations=1,
                tokens=0,
            ),
            deterministic=True,
            required_providers=(),
        )

    def invoke(self, ctx: CapabilityContext) -> CapabilityResult:
        try:
            date_value = parse_date(ctx.raw_input)
        except ParseError as e:
            return CapabilityResult(
                candidates=(),
                evidence=(),
                diagnostics=(Diagnostic(
                    code=DiagnosticCode.PATTERN_NO_MATCH,
                    severity=DiagnosticSeverity.WARNING,
                    message=str(e),
                    context={"input": ctx.raw_input},
                ),),
            )

        return CapabilityResult(
            candidates=(Candidate(value=date_value, evidence_refs=(), diagnostics=()),),
            evidence=(
                EvidenceRef(
                    capability_id="date_parser",
                    capability_version="1.0",
                    span=ctx.span,
                    field_path=ctx.field_path,
                ),
            ),
            diagnostics=(),
        )
```

The `CostHint` is a **deterministic upper bound** for the
capability's cost. The Planner uses it to score the capability and
to pre-flight budget gates.

### 3.3 Be stateless

The capability **must** be stateless across invocations. Each call
must produce the same result for the same input (unless
`spec.deterministic=False`).

Tests:

```python
def test_date_parser_capability_is_stateless():
    cap = DateParserCapability()
    ctx = CapabilityContext(input_text="2026-01-15", ...)
    a = cap.invoke(ctx)
    b = cap.invoke(ctx)
    assert a.candidates == b.candidates
```

### 3.4 Capture external effects in evidence

If the capability calls an external service, record the call
(provider, model, prompt hash, completion hash) in evidence:

```python
evidence_refs=(
    EvidenceRef(
        capability_id="inference",
        capability_version="1.0",
        span=ctx.span,
        field_path=ctx.field_path,
        extras={"provider": "openai", "model": "gpt-5", "prompt_hash": "..."},
    ),
),
```

This is critical for **replay**: the recorded evidence is what
`paxman.replay()` rehydrates from. Without it, replay would have to
re-invoke the capability, breaking determinism.

### 3.5 Register the capability

```python
import paxman

paxman.register_capability(DateParserCapability())
```

Registering with an already-registered `(id, version)` raises
`InvalidContractError`.

### 3.6 Write tests

At minimum:

- **Happy path** — one test per `input_type` you support.
- **Edge cases** — empty input, malformed input, very long input.
- **Stateless** — same input → same output across calls.
- **Determinism flag** — `spec.deterministic=True` for any capability
  backed by a pure function.
- **Evidence** — `result.evidence` is non-empty when the
  capability produces a candidate.

```python
from datetime import date

from paxman.capabilities.base import CapabilityContext
from paxman.types import FieldType


def test_date_parser_capability_handles_iso_format():
    cap = DateParserCapability()
    ctx = CapabilityContext(
        raw_input=b"2026-01-15",
        field_path="issue_date",
        field_type_name=FieldType.DATE.value,
    )
    result = cap.invoke(ctx)
    assert len(result.candidates) == 1
    assert result.candidates[0].value == date(2026, 1, 15)
```

Use `paxman.testing.capability_contexts()` for property tests.

### 3.7 Distribute

If your capability is a **new public SPI surface** for the Paxman
core, you need an **ADR** (see [docs/adr/README.md](../adr/index.md)).
If you are publishing as a separate PyPI package
(`paxman-<your-capability>`), you do not need an ADR for the
Paxman core repo, but the extension should document its SPI
compliance.

---

## 4. What capabilities MUST do

- **Return `CapabilityResult`** with `candidates`, `evidence_refs`,
  and `diagnostics`.
- **Be stateless** — no mutable state across invocations.
- **Declare a `CapabilitySpec`** with input/output, cost,
  determinism, and required providers.
- **Capture external effects in evidence** — if the capability
  calls an external service, record the call as evidence.
- **Fail loudly** on unrecoverable errors via `CapabilityError`.

## 5. What capabilities MUST NOT do

- **Assign confidence.** Capabilities return candidates; the
  Reconciler assigns confidence. See
  [ADR-0005](../adr/0005-confidence-ownership.md).
- **Read the canonical contract directly** — capabilities receive a
  `CapabilityContext`.
- **Read the raw input directly** — they receive an opaque
  `InputData` handle via `CapabilityContext`.
- **Mutate the executor state.**

---

## 6. The full SPI walkthrough

For the full SPI walkthrough (including a longer example, the
`CostHint` semantics, and a worked inference-style capability), see
[EXTENDING.md §2](../reference/extending.md).

---

## 7. See also

- [EXTENDING.md §2](../reference/extending.md) — full SPI walkthrough.
- [docs/concepts/capabilities.md](../concepts/capabilities.md) —
  what a capability is in Paxman.
- [ADR-0005](../adr/0005-confidence-ownership.md) — confidence
  ownership (why capabilities don't assign confidence).
- [docs/specs/capability-cost-model.md](../specs/capability-cost-model.md) —
  the `CostHint` and the scoring formula.
- [paxman.capabilities.spec](../reference/extending.md) — the
  `CapabilitySpec` data model.
