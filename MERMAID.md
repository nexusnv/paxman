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
    participant API as paxman.canonicalize()
    participant ORT as default_registry
    participant REG as CapabilityRegistry
    participant DSL as parse_contract()
    participant ENG as Engine
    participant CAP as MoneyCapability
    participant GR as recognize_money()
    participant PA as parse_amount()
    participant RULES as rules _evidence()
    participant VAL as validate_value()
    participant CLS as classify()
    participant ART as ExecutionArtifact

    Caller->>API: canonicalize(input, Money(currency=...))
    API->>ORT: default_registry
    API->>REG: load_builtins(); freeze()
    API->>ENG: Engine.default() if engine is None
    API->>DSL: parse_contract(Money(...))
    DSL-->>API: CanonicalMoneyContract
    API->>ENG: engine.override() per authority_override pin
    API->>REG: resolve_all(parsed_contract, input)
    REG-->>API: [MoneyCapability] single claimant
    API->>CAP: canonicalize(input, parsed_contract, engine)

    alt not a CanonicalMoneyContract or not str
        CAP-->>RULES: _evidence("not_a_money_contract" / "not_a_string_value")
        RULES-->>CAP: Evidence(authority=None)
        CAP-->>API: CapabilityResult(INVALID)
    else missing or whitespace-only value
        CAP-->>RULES: _evidence("missing_value")
        RULES-->>CAP: Evidence(authority=None)
        CAP-->>API: CapabilityResult(INVALID)
    else strip_spaces policy trims input
        CAP-->>RULES: _evidence("trimmed_whitespace")
        RULES-->>CAP: Evidence(authority=None)
    end

    CAP->>GR: recognize_money(value, contract)
    GR->>GR: _strip_amount_text() trims whitespace, rejects empty
    GR->>GR: _split_sign() outer +/-, trailing minus, parens
    GR->>GR: _detect_symbol() validates vs contract.currency
    GR->>GR: _detect_code() validates code, detects ":" canonical
    GR->>GR: _split_sign() inner sign, rejects contradictory signs

    alt ContractError raised by recognition
        GR-->>CAP: raise ContractError
        CAP-->>RULES: _evidence("unrecognized_format")
        RULES-->>CAP: Evidence(authority=None)
        CAP-->>API: CapabilityResult(INVALID)
    else recognized
        GR-->>CAP: MoneyParts(currency, amount, symbol, code, sign, canonical)
    end

    CAP->>PA: parse_amount(amount, contract.currency, parts.canonical)
    PA->>PA: apply separator convention (comma vs dot decimal)
    PA->>PA: _validate_thousands() rejects ambiguous grouping
    PA->>PA: Decimal exact, preserve literal decimals (F1), sci-notation (Q3)

    alt ContractError raised by parse
        PA-->>CAP: raise ContractError
        CAP-->>RULES: _evidence("unrecognized_format")
        RULES-->>CAP: Evidence(authority=None)
        CAP-->>API: CapabilityResult(INVALID)
    else parsed
        PA-->>CAP: canonical decimal string
    end

    CAP->>CAP: compose canonical = currency + ":" + sign + parsed
    CAP->>RULES: _evidence currency_from_contract, symbol/code_validated, preserved_sign, parsed_decimal, preserved_decimals, canonical_form
    RULES-->>CAP: Evidence(rule, authority from _RULE_AUTHORITIES)
    CAP-->>API: CapabilityResult(CANONICALIZED, value=canonical, evidence)

    API->>VAL: validate_value(canonical, parsed_contract)
    VAL-->>API: ValidationResult(is_valid=True)
    API->>CLS: classify(capability_result, validation)
    CLS-->>API: Status.CANONICALIZED
    API->>ART: _build_artifact(registry, engine, parsed_contract, status, value, evidence)
    ART->>ART: collect authorities cited in evidence (Law 12)
    ART->>ART: VersionStamp(paxman_version, contract_version, capabilities_hash)
    ART-->>Caller: ExecutionArtifact(status, value, evidence, contract, authorities, version_stamp)

    Caller->>API: replay(artifact, contract)
    API->>ART: reconstruct engine from recorded authorities
    API->>ART: re-canonicalize to byte-for-byte identical artifact
```

## Notes

- Single claimant contract: the registry resolves exactly one capability (MoneyCapability) for a CanonicalMoneyContract. Multiple claimants produce Status.AMBIGUOUS; no claimants produce Status.UNSUPPORTED.
- Currency is never guessed (Law 3): Money(...) requires currency; the grammar only validates that any symbol/code present matches the contract currency, never infers it.
- Determinism / idempotence: parts.canonical (set when the input is the capability's own "ISO4217:amount" output) makes parse_amount skip the currency separator convention, so canonicalize(canonicalize(x)) == canonicalize(x).
- Evidence authority: every fired rule resolves from the capability's _RULE_AUTHORITIES manifest (mandate Law 14); routing/dispatch failures carry authority=None.
