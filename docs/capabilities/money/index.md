# Money Capability

The money capability is a built-in capability shipped with Paxman v2.0.0. It canonicalizes strings into money representations. It is built on the recognition Layer 1 architecture: a `grammar.py` recognition layer feeds a resolver/validator/classifier pipeline.

**Capability name:** `money_canonicalization`

**Contract kind:** `canonical_money`

**Contract factory:** `Money(currency="USD")`

## What It Does

The money capability rewrites a string into a single canonical form. The capability is governed by the contract you pass to `paxman.canonicalize()`. The contract is a frozen value object built with `Money(currency=...)`. See [Contracts](../../reference/contracts.md) for the full factory signature.

## The Rules

Every transformation the capability performs is recorded as an `Evidence` entry on the artifact. Each entry has a `rule` name, a `detail` string, and a `provenance` citation.

### Evidence Rules

| Rule | Citation |
|---|---|
| `not_a_money_contract` | (dispatch invariant) |\n| `not_a_string_value` | (dispatch invariant) |\n| `missing_value` | money design spec (empty input rejected — Law 3 Never Guess) |\n| `currency_from_contract` | MANDATE Law 3 (Never Guess) + Law 7 (Explicit Over Clever) |\n| `canonical_form` | money design spec M2 ('<ISO4217>:<amount>') |\n| `symbol_validated` | money design spec Q-symbol (symbol must match contract currency) |\n| `code_validated` | money design spec Q-code (ISO code must match contract currency) |\n| `trimmed_whitespace` | money design spec (strip_spaces policy) |\n| `preserved_sign` | money design spec Q2=A (negatives preserved) |\n| `parsed_decimal` | money design spec Q1=A (Decimal, comma-decimal per currency) |\n| `preserved_decimals` | money design spec F1/Q3=A (no quantization; sci-notation normalized) |\n| `unrecognized_format` | money design spec (rejected: empty, malformed, or symbol/code mismatch — Law 3 Never Guess) |

## Recognition Layer 1

Before any rewriting, the capability runs `grammar.recognize` over the input. Recognition assigns **no meaning** — it returns only raw captures. The resolver then assigns meaning to the captures and maps the survivors to a `Status`.

## Status Outcomes

- **CANONICALIZED:** The input was successfully matched and canonicalized.
- **INVALID:** The input was rejected due to an unrecognized format or policy restriction.
- **MISSING:** The input was empty or purely whitespace.
- **AMBIGUOUS:** (where applicable) The input could not be definitively resolved.
- **UNSUPPORTED:** (where applicable) The input format is known but explicitly not supported.

## Quickstart

```python
import paxman
from paxman import Money, Status

result = paxman.canonicalize("USD 12.34", Money(currency="USD"))
```

## References

- **Source Module:** [`src/paxman/_capabilities/money`](../../../src/paxman/_capabilities/money)
- **Contracts Reference:** [Contracts](../../reference/contracts.md)
