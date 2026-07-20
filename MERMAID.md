# Money Canonicalization — Runtime Object Interaction

This diagram traces the full runtime object flow when a caller invokes
`paxman.canonicalize(input, Money(...))` and the `MoneyCapability` claims the
contract. It reflects the actual code paths in `src/paxman/` (engine dispatch in
`_core/engine.py`, capability in `_capabilities/money/canonicalizer.py`,
recognition/parsing in `_capabilities/money/grammar.py`).

```mermaid
sequenceDiagram
    autonumber
    actor Caller
    participant API as paxman.canonicalize()<br/>_core/engine.py
    participant ORT as _orchestrator_runtime<br/>default_registry
    participant REG as CapabilityRegistry
    participant DSL as parse_contract()<br/>_dsl/parser.py
    participant ENG as Engine<br/>_core/engine_env.py
    participant CAP as MoneyCapability<br/>_capabilities/money/canonicalizer.py
    participant GR as recognize_money()<br/>_capabilities/money/grammar.py
    participant PA as parse_amount()<br/>_capabilities/money/grammar.py
    participant RULES as rules.py _evidence()<br/>+ _RULE_AUTHORITIES
    participant VAL as validate_value()<br/>_core/validation.py
    participant CLS as classify()<br/>_core/classification.py
    participant ART as ExecutionArtifact<br/>_core/artifact.py

    Caller->>API: canonicalize(input, Money(currency=...))

    Note over API,ORT: Lazy built-in load + freeze (once per process)
    API->>ORT: default_registry
    API->>REG: load_builtins(builtin_capabilities())
    API->>REG: freeze()
    API->>ENG: Engine.default()  (if engine is None)

    Note over API,DSL: Stage 1 — inspect (parse contract)
    API->>DSL: parse_contract(Money(...))
    DSL-->>API: CanonicalMoneyContract (parsed_contract)

    Note over API,ENG: Stage 1.5 — authority override
    API->>API: override = parsed_contract.authority_override
    API->>ENG: engine.override(name, selector) per pin

    Note over API,REG: Stage 2 — resolve claimants
    API->>REG: resolve_all(parsed_contract, input)
    REG-->>API: [MoneyCapability]  (exactly one claimant)

    Note over API,CAP: Stage 3+4 — execute + canonicalize
    API->>CAP: canonicalize(input, parsed_contract, engine)

    alt not a CanonicalMoneyContract / not str
        CAP-->>RULES: _evidence("not_a_money_contract" / "not_a_string_value")
        RULES-->>CAP: Evidence(authority=None)
        CAP-->>API: CapabilityResult(status=INVALID, evidence=...)
    else missing / whitespace-only value
        CAP-->>RULES: _evidence("missing_value")
        RULES-->>CAP: Evidence(authority=None)
        CAP-->>API: CapabilityResult(status=INVALID, evidence=...)
    else strip_spaces policy trims input
        CAP-->>RULES: _evidence("trimmed_whitespace")
        RULES-->>CAP: Evidence(authority=None)
    end

    Note over CAP,GR: Layer 1 — recognition (shape + symbol/code validation)
    CAP->>GR: recognize_money(value, contract)
    GR->>GR: _strip_amount_text()  (whitespace / empty)
    GR->>GR: _split_sign()  (outer +/-, trailing -, parens)
    GR->>GR: _detect_symbol()  (validate vs contract.currency)
    GR->>GR: _detect_code()  (validate vs contract.currency; detect ":" canonical)
    GR->>GR: _split_sign()  (inner sign; reject contradictory signs)
    alt ContractError raised (malformed / mismatch)
        GR-->>CAP: raise ContractError
        CAP-->>RULES: _evidence("unrecognized_format")
        RULES-->>CAP: Evidence(authority=None)
        CAP-->>API: CapabilityResult(status=INVALID, evidence=...)
    else recognized
        GR-->>CAP: MoneyParts(currency, amount, symbol, code, sign, canonical)
    end

    Note over CAP,PA: Parse amount → canonical decimal string (F1/Q1/Q2/Q3)
    CAP->>PA: parse_amount(amount, contract.currency, parts.canonical)
    PA->>PA: apply separator convention (comma vs dot decimal)
    PA->>PA: _validate_thousands()  (reject ambiguous grouping)
    PA->>PA: Decimal(...) exact; preserve literal decimals (F1); normalize sci-notation (Q3)
    alt ContractError raised (bad amount)
        PA-->>CAP: raise ContractError
        CAP-->>RULES: _evidence("unrecognized_format")
        RULES-->>CAP: Evidence(authority=None)
        CAP-->>API: CapabilityResult(status=INVALID, evidence=...)
    else parsed
        PA-->>CAP: canonical decimal string
    end

    Note over CAP,RULES: Compose canonical form + evidence
    CAP->>CAP: canonical = f"{currency}:{sign}{parsed}"
    CAP->>RULES: _evidence("currency_from_contract", "symbol_validated" |<br/>"code_validated", "preserved_sign", "parsed_decimal",<br/>"preserved_decimals", "canonical_form")
    RULES-->>CAP: Evidence(rule, authority from _RULE_AUTHORITIES)
    CAP-->>API: CapabilityResult(status=CANONICALIZED, value=canonical, evidence=...)

    Note over API,CLS: Stage 5 — validate + Stage 6 — classify
    API->>VAL: validate_value(canonical, parsed_contract)
    VAL-->>API: ValidationResult(is_valid=True)
    API->>CLS: classify(capability_result, validation)
    CLS-->>API: Status.CANONICALIZED

    Note over API,ART: Build artifact
    API->>ART: _build_artifact(registry, engine, parsed_contract,<br/>status, value, evidence, candidates)
    ART->>ART: collect authorities cited in evidence (Law 12)
    ART->>ART: VersionStamp(paxman_version, contract_version, capabilities_hash)
    ART-->>Caller: ExecutionArtifact(status, value="ISO4217:amount", evidence, contract, authorities, version_stamp)

    Note over Caller,ART: Replay (determinism invariant)
    Caller->>API: replay(artifact, contract)
    API->>ART: reconstruct engine from recorded authorities
    API->>ART: re-canonicalize → byte-for-byte identical artifact
```

## Notes

- **Single claimant contract**: the registry resolves exactly one capability
  (`MoneyCapability`) for a `CanonicalMoneyContract`. Multiple claimants →
  `Status.AMBIGUOUS`; no claimants → `Status.UNSUPPORTED`.
- **Currency is never guessed** (Law 3): `Money(...)` requires `currency`; the
  grammar only validates that any symbol/code present matches the contract
  currency, never infers it.
- **Determinism / idempotence**: `parts.canonical` (set when the input is the
  capability's own `"ISO4217:amount"` output) makes `parse_amount` skip the
  currency separator convention, so `canonicalize(canonicalize(x)) == canonicalize(x)`.
- **Evidence authority**: every fired rule resolves from the capability's
  `_RULE_AUTHORITIES` manifest (mandate Law 14); routing/dispatch failures carry
  `authority=None`.
