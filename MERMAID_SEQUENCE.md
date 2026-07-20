# Money + Date Canonicalization — Full Runtime Object Interaction

This diagram shows the COMPLETE runtime object interaction inside `src/paxman/`
for two consecutive `paxman.canonicalize` calls in the same process: first
`Money(...)` (claimed by `MoneyCapability`), then `Date(...)` (claimed by
`DateCapability`). The **Date canonicalization runs after the Money
canonicalization in the same diagram**, reusing the already-frozen registry and
the shared orchestration / artifact / replay machinery. Every object, branch,
and edge below is taken from the actual source:

- Entry / orchestration: `src/paxman/_core/engine.py` (`canonicalize`)
- Registry / resolver: `src/paxman/_registry/capability_registry.py`
- Contract DSL: `src/paxman/_dsl/parser.py` (`parse_contract`)
- Engine / editions: `src/paxman/_core/engine_env.py` (`Engine`, `Authority`)
- Money capability: `src/paxman/_capabilities/money/canonicalizer.py`
- Money recognition + parsing: `src/paxman/_capabilities/money/grammar.py`
- Money rule manifest + evidence: `src/paxman/_capabilities/money/rules.py`
- Date capability: `src/paxman/_capabilities/date/canonicalizer.py`
- Date recognition: `src/paxman/_capabilities/date/grammar.py` (`recognize`)
- Date resolver pipeline: `src/paxman/_capabilities/date/canonicalizer.py`
  (`generate_interpretations` / `resolve_and_validate` / `classify`)
- Date rule manifest + evidence: `src/paxman/_capabilities/date/rules.py`
- Validation / classification: `src/paxman/_core/validation.py`, `src/paxman/_core/classification.py`
- Artifact: `src/paxman/_core/artifact.py` (`ExecutionArtifact`, `VersionStamp`)
- Replay: `src/paxman/_core/replay.py`

Every `alt` block below lists ALL branches the source can take (no single-state
`alt` without its complement). The Money branch and the Date branch share Stages
0-2 (lazy builtin load + freeze, engine binding, contract parse, authority
override, claimant resolution) and the replay stage; Stage 3+4 (the
capability's own execute + canonicalize) differs per capability, and the
contract-specific evidence rules differ — notably, only Money's `code_validated`
rule is engine-aware (re-resolves ISO 4217), whereas every Date rule carries a
static grammar/policy `Authority`.

```mermaid
sequenceDiagram
    autonumber
    actor Caller
    participant API as paxman.canonicalize (engine.py)
    participant ORT as default_registry (orchestrator_runtime)
    participant REG as CapabilityRegistry (capability_registry.py)
    participant DISCOVERY as builtin_capabilities (discovery.py)
    participant DSL as parse_contract (dsl/parser.py)
    participant STUB as _StubContract (engine.py)
    participant ENG as Engine (engine_env.py)
    participant AUTH as Authority (provenance/authority.py)
    participant CAP as MoneyCapability (money/canonicalizer.py)
    participant GR as recognize_money (money/grammar.py)
    participant PA as parse_amount (money/grammar.py)
    participant RULES as money/rules.py _evidence + _RULE_AUTHORITIES
    participant DCAP as DateCapability (date/canonicalizer.py)
    participant DGR as recognize (date/grammar.py)
    participant DRES as date resolver pipeline (date/canonicalizer.py)
    participant DRULES as date/rules.py _evidence + _RULE_AUTHORITIES
    participant VAL as validate_value (core/validation.py)
    participant VRES as ValidationResult (core/classification.py)
    participant CLS as classify (core/classification.py)
    participant ART as ExecutionArtifact + VersionStamp (core/artifact.py)
    participant REPLAY as replay (core/replay.py)

    Caller->>API: canonicalize(input, Money(currency=...))

    Note over API,REG: Stage 0 - lazy builtin load + freeze (once per process)
    API->>ORT: read default_registry
    API->>REG: is_frozen ?
    alt registry not yet frozen
        API->>DISCOVERY: builtin_capabilities()
        DISCOVERY-->>API: list of 10 Capability objects
        API->>REG: load_builtins(list)
        REG->>REG: for each cap skip if name taken else register
        API->>REG: freeze()
        REG->>REG: _frozen = True (immutable capability set)
    else registry already frozen
        REG-->>API: skip load_builtins and freeze (no-op)
        Note over REG: capability set already fixed from first canonicalize
        Note over REG: any later register_capability raises FrozenRegistryError
    end

    alt engine argument is None
        API->>ENG: Engine.default()
        ENG->>ENG: bind every authority to its latest edition
        ENG-->>API: Engine with concrete Authority editions
    else engine argument provided
        API->>API: use the caller supplied Engine unchanged
    end

    Note over API,DSL: Stage 1 - inspect (parse contract DSL)
    API->>DSL: parse_contract(Money(...))
    alt parse_contract raises ContractError
        DSL-->>API: raise ContractError
        API->>STUB: _StubContract(contract)
        API->>ART: _build_artifact UNSUPPORTED unparseable_contract authority None
        ART-->>Caller: ExecutionArtifact status UNSUPPORTED
    else parsed successfully
        DSL-->>API: CanonicalMoneyContract (parsed_contract)

        Note over API,ENG: Stage 1.5 - per-contract authority override
        API->>API: override = parsed_contract.authority_override
        alt override is not empty
            loop for each name, selector in override
                API->>ENG: engine.override(name, selector)
                ENG->>ENG: resolve selector to concrete Authority edition
                ENG-->>API: new Engine with name re-bound
            end
        else override is empty
            API->>API: keep engine as is (no re-bind)
        end

        Note over API,REG: Stage 2 - resolve claimants
        API->>REG: resolve_all(parsed_contract, input)
        REG->>REG: for each cap in _capabilities.values()
        REG->>CAP: cap.can_handle(contract, value)
        CAP-->>REG: True if CanonicalMoneyContract and value None or str
        REG->>REG: collect claimants then sort by cap.name
        REG-->>API: list of claimant Capabilities sorted by name

        alt no claimants (empty list)
            API->>ART: _build_artifact UNSUPPORTED no_capability_claims
            ART-->>Caller: ExecutionArtifact status UNSUPPORTED
        else more than one claimant
            API->>ART: _build_artifact AMBIGUOUS multiple_claimants
            ART-->>Caller: ExecutionArtifact status AMBIGUOUS
        else exactly one claimant
            REG-->>API: [MoneyCapability]
            API->>CAP: canonicalize(input, parsed_contract, engine)

            Note over CAP,RULES: Stage 3+4 (Money) - execute + canonicalize (sequential guards)

            alt contract is not a CanonicalMoneyContract
                CAP-->>RULES: _evidence("not_a_money_contract", engine)
                RULES-->>CAP: Evidence(rule, authority=None)
                CAP-->>API: CapabilityResult(status=INVALID)
            else contract is a CanonicalMoneyContract
                alt value is not None and not a str
                    CAP-->>RULES: _evidence("not_a_string_value", engine)
                    RULES-->>CAP: Evidence(authority=None)
                    CAP-->>API: CapabilityResult(status=INVALID)
                else value is None or a str
                    alt value is None or whitespace only
                        CAP-->>RULES: _evidence("missing_value", engine)
                        RULES-->>CAP: Evidence(rule, authority=STATIC policy Authority, NOT engine-resolved)
                        CAP-->>API: CapabilityResult(status=INVALID)
                    else value is a non-empty str
                        alt contract.strip_spaces is True and value changed after strip
                            CAP->>CAP: value = value.strip()
                            CAP-->>RULES: _evidence("trimmed_whitespace", engine)
                            RULES-->>CAP: Evidence(authority=None)
                        else no whitespace trimming applied
                            CAP->>CAP: value unchanged (no trimmed_whitespace evidence)
                        end

                        CAP->>GR: recognize_money(value, contract)
                        GR->>GR: _strip_amount_text trims empty rejected
                        GR->>GR: _split_sign outer sign trailing minus parens
                        GR->>GR: _detect_symbol validates vs contract.currency
                        GR->>GR: _detect_code validates code detects ":" canonical
                        GR->>GR: _split_sign inner sign rejects contradictory

                        alt recognize_money raises ContractError
                            GR-->>CAP: raise ContractError
                            CAP-->>RULES: _evidence("unrecognized_format", engine)
                            RULES-->>CAP: Evidence(authority=None)
                            CAP-->>API: CapabilityResult(status=INVALID)
                        else recognized
                            GR-->>CAP: MoneyParts(currency, amount, symbol, code, sign, canonical)

                            CAP->>PA: parse_amount(amount, contract.currency, parts.canonical)
                            PA->>PA: choose separator convention from currency
                            PA->>PA: _validate_thousands rejects ambiguous grouping
                            PA->>PA: Decimal exact preserves literal decimals normalizes sci notation

                            alt parse_amount raises ContractError
                                PA-->>CAP: raise ContractError
                                CAP-->>RULES: _evidence("unrecognized_format", engine)
                                RULES-->>CAP: Evidence(authority=None)
                                CAP-->>API: CapabilityResult(status=INVALID)
                            else parsed
                                PA-->>CAP: canonical decimal string
                                CAP->>CAP: compose canonical = currency + ":" + sign + parsed
                                CAP->>RULES: _evidence("currency_from_contract" / "symbol_validated" / "preserved_sign" / "parsed_decimal" / "preserved_decimals" / "canonical_form", engine)
                                RULES-->>CAP: Evidence(rule, authority=STATIC manifest Authority, NOT engine-resolved)
                                CAP->>RULES: _evidence("code_validated", engine)
                                RULES->>ENG: ONLY this rule re-resolves Authority edition for ISO 4217 (registry_rules={code_validated})
                                RULES-->>CAP: Evidence("code_validated", authority=engine-resolved ISO 4217 edition)
                                CAP-->>API: CapabilityResult(status=CANONICALIZED, value=canonical, evidence)
                            end
                        end
                    end
                end
            end
        end

        Note over Caller,ART: Second call - paxman.canonicalize(input2, Date(...))
        Caller->>API: canonicalize("03/04/2025", Date(locale="US"))

        Note over API,REG: Stages 0-2 SHORT-CIRCUITED (registry already frozen from 1st call)
        API->>REG: is_frozen ?
        REG-->>API: True (no builtin reload, no re-freeze)
        API->>ENG: Engine.default() (or caller-supplied Engine reused)
        ENG-->>API: Engine with concrete Authority editions
        API->>DSL: parse_contract(Date(...))
        DSL-->>API: CanonicalDateContract (parsed_contract2)

        Note over API,ENG: Stage 1.5 - per-contract authority override (Date path)
        API->>API: override = parsed_contract2.authority_override
        alt override is not empty
            loop for each name, selector in override
                API->>ENG: engine.override(name, selector)
                ENG->>ENG: resolve selector to concrete Authority edition
                ENG-->>API: new Engine with name re-bound
            end
        else override is empty
            API->>API: keep engine as is (no re-bind)
        end

        API->>REG: resolve_all(parsed_contract2, input2)
        REG->>REG: for each cap in _capabilities.values()
        REG->>DCAP: cap.can_handle(contract, value)
        DCAP-->>REG: True if CanonicalDateContract and value None or str
        REG->>REG: collect claimants then sort by cap.name
        REG-->>API: list of claimant Capabilities sorted by name

        alt no claimants (empty list)
            API->>ART: _build_artifact UNSUPPORTED no_capability_claims
            ART-->>Caller: ExecutionArtifact status UNSUPPORTED
        else more than one claimant
            API->>ART: _build_artifact AMBIGUOUS multiple_claimants
            ART-->>Caller: ExecutionArtifact status AMBIGUOUS
        else exactly one claimant
            REG-->>API: [DateCapability]
            API->>DCAP: canonicalize("03/04/2025", parsed_contract2, engine)

            Note over DCAP,DRULES: Stage 3+4 (Date) - execute + canonicalize (sequential guards)

            alt contract is not a CanonicalDateContract
                DCAP-->>DRULES: _evidence("not_a_date_contract")
                DRULES-->>DCAP: Evidence(rule, authority=None)
                DCAP-->>API: CapabilityResult(status=INVALID)
            else contract is a CanonicalDateContract
                alt value is not None and not a str
                    DCAP-->>DRULES: _evidence("not_a_string_value")
                    DRULES-->>DCAP: Evidence(authority=None)
                    DCAP-->>API: CapabilityResult(status=INVALID)
                else value is None or a str
                    alt value is None or whitespace only
                        DCAP-->>DRULES: _evidence("empty_value")
                        DRULES-->>DCAP: Evidence(authority=None)
                        DCAP-->>API: CapabilityResult(status=MISSING)
                    else value is a non-empty str
                        DCAP->>DCAP: reject_contract / reject_non_string pass, value not empty
                        Note over DCAP: deterministic dispatch (every branch a predicate, never a guess)
                        alt _is_epoch(value)  (Unix seconds since 1970-01-01T00:00:00Z)
                            DCAP->>DCAP: datetime.fromtimestamp(ts, tz=UTC)
                            alt overflow / unrepresentable
                                DCAP-->>DRULES: _evidence("invalid_epoch_value")
                                DRULES-->>DCAP: Evidence(authority=None)
                                DCAP-->>API: CapabilityResult(status=INVALID)
                            else parsed
                                DCAP->>DRULES: _evidence("parsed_unix_timestamp") + _evidence("normalized_to_utc")
                                DRULES-->>DCAP: Evidence(rule, authority=STATIC grammar/policy Authority, NOT engine-aware)
                                DCAP-->>API: CapabilityResult(status=CANONICALIZED, value=RFC3339 UTC, evidence)
                            end
                        else _ISO_DATE_RE matches (YYYY-MM-DD)
                            DCAP->>DCAP: datetime.strptime(value, "%Y-%m-%d")
                            alt invalid calendar date
                                DCAP-->>DRULES: _evidence("invalid_calendar_date")
                                DRULES-->>DCAP: Evidence(authority=None)
                                DCAP-->>API: CapabilityResult(status=INVALID)
                            else valid
                                DCAP->>DRULES: _evidence("parsed_iso_date")
                                DRULES-->>DCAP: Evidence(rule, authority=STATIC Authority, NOT engine-aware)
                                DCAP-->>API: CapabilityResult(status=CANONICALIZED, value=YYYY-MM-DD, evidence)
                            end
                        else _ISO_DATETIME_RE matches (with Z or offset)
                            DCAP->>DCAP: datetime.fromisoformat(value.replace("Z","+00:00"))
                            alt invalid iso format
                                DCAP-->>DRULES: _evidence("invalid_iso_format")
                                DRULES-->>DCAP: Evidence(authority=None)
                                DCAP-->>API: CapabilityResult(status=INVALID)
                            else parsed
                                DCAP->>DRULES: _evidence("parsed_iso_datetime") [+ "normalized_to_utc" if not already canonical]
                                DRULES-->>DCAP: Evidence(rule, authority=STATIC Authority, NOT engine-aware)
                                DCAP-->>API: CapabilityResult(status=CANONICALIZED, value=YYYY-MM-DDTHH:MM:SSZ, evidence)
                            end
                        else _ISO_NAIVE_DATETIME_RE matches (no timezone)
                            DCAP-->>DRULES: _evidence("ambiguous_naive_datetime")
                            DRULES-->>DCAP: Evidence(rule, authority=STATIC Authority, NOT engine-aware)
                            DCAP-->>API: CapabilityResult(status=AMBIGUOUS)
                        else locale in (US, EU) and numeric slash form
                            DCAP->>DCAP: apply MM/DD or DD/MM ordering per locale, validate month/day
                            alt impossible month/day
                                DCAP-->>DRULES: _evidence("invalid_calendar_date")
                                DRULES-->>DCAP: Evidence(authority=None)
                                DCAP-->>API: CapabilityResult(status=INVALID)
                            else 2-digit year + two_digit_year="reject"/"require_four_digit_year"
                                DCAP-->>DRULES: _evidence("rejected_two_digit_year")
                                DRULES-->>DCAP: Evidence(authority=None)
                                DCAP-->>API: CapabilityResult(status=INVALID)
                            else 2-digit year + pivot:YYYY -> single resolved century
                                DCAP->>DCAP: _resolve_pivot_year
                                alt invalid calendar date
                                    DCAP-->>DRULES: _evidence("invalid_calendar_date")
                                    DRULES-->>DCAP: Evidence(authority=None)
                                    DCAP-->>API: CapabilityResult(status=INVALID)
                                else valid
                                    DCAP->>DRULES: _evidence("parsed_us_numeric" / "parsed_eu_numeric")
                                    DRULES-->>DCAP: Evidence(rule, authority=STATIC Authority, NOT engine-aware)
                                    DCAP-->>API: CapabilityResult(status=CANONICALIZED, value=YYYY-MM-DD, evidence)
                                end
                            else 2-digit year + no policy -> century ambiguous (Don't Guess)
                                DCAP->>DCAP: expand across 1900/2000/2100 centuries
                                DCAP-->>DRULES: _evidence("ambiguous_two_digit_year")
                                DRULES-->>DCAP: Evidence(rule, authority=STATIC Authority, NOT engine-aware)
                                DCAP-->>API: CapabilityResult(status=AMBIGUOUS, candidates=tuple of YYYY-MM-DD)
                            else 4-digit year numeric
                                DCAP->>DCAP: _valid_calendar_date check
                                alt invalid
                                    DCAP-->>DRULES: _evidence("invalid_calendar_date")
                                    DRULES-->>DCAP: Evidence(authority=None)
                                    DCAP-->>API: CapabilityResult(status=INVALID)
                                else valid
                                    DCAP->>DRULES: _evidence("parsed_us_numeric" / "parsed_eu_numeric")
                                    DRULES-->>DCAP: Evidence(rule, authority=STATIC Authority, NOT engine-aware)
                                    DCAP-->>API: CapabilityResult(status=CANONICALIZED, value=YYYY-MM-DD, evidence)
                                end
                            end
                        else _RFC2822_RE matches ("1 Jan 2025" / "Tue, 01 Jan 2025 12:00 +0000")
                            DCAP->>DCAP: _parse_rfc2822_date_only OR parsedate_to_datetime
                            alt parse fails / invalid calendar date
                                DCAP-->>DRULES: _evidence("invalid_calendar_date")
                                DRULES-->>DCAP: Evidence(authority=None)
                                DCAP-->>API: CapabilityResult(status=INVALID)
                            else parsed with timezone
                                DCAP->>DRULES: _evidence("parsed_rfc2822") + _evidence("normalized_to_utc")
                                DRULES-->>DCAP: Evidence(rule, authority=STATIC Authority, NOT engine-aware)
                                DCAP-->>API: CapabilityResult(status=CANONICALIZED, value=YYYY-MM-DD[THH:MM:SSZ], evidence)
                            else parsed naive (no tz)
                                DCAP-->>DRULES: _evidence("ambiguous_naive_datetime")
                                DRULES-->>DCAP: Evidence(rule, authority=STATIC Authority, NOT engine-aware)
                                DCAP-->>API: CapabilityResult(status=AMBIGUOUS)
                            end
                        else enumeration pipeline (text-month + numeric slash forms)
                            DCAP->>DGR: recognize(value, contract)
                            DGR->>DGR: compile each Grammar for contract.language
                            DGR->>DGR: fullmatch input against every Grammar in GRAMMARS
                            DGR-->>DCAP: list[RecognizedRep] (raw captures, no meaning)
                            DCAP->>DRES: generate_interpretations(value, contract)
                            DRES->>DRES: _interpretations_from_reps -> enumerate _Candidate readings
                            DRES->>DRES: resolve_and_validate -> _valid_calendar_date, _weekday_of_date
                            DRES->>DRES: collapse duplicate calendar days, collect drop_reasons
                            DRES-->>DCAP: (survivors, drop_reasons)
                            DCAP->>DRES: classify(candidates, survivors, drop_reasons)
                            alt no candidate recognized (grammar returned nothing)
                                DRES-->>DCAP: (INVALID, None, _evidence("unrecognized_format"), None)
                                DCAP-->>API: CapabilityResult(status=INVALID)
                            else recognized but no calendar-day survivor
                                alt rejected_two_digit_year in drop_reasons
                                    DRES-->>DCAP: (INVALID, None, _evidence("rejected_two_digit_year"), None)
                                else weekday_contradicts_date in drop_reasons
                                    DRES-->>DCAP: (INVALID, None, _evidence("weekday_contradicts_date"), None)
                                else invalid_calendar_date
                                    DRES-->>DCAP: (INVALID, None, _evidence("invalid_calendar_date"), None)
                                end
                                DCAP-->>API: CapabilityResult(status=INVALID)
                            else exactly one survivor
                                DRES-->>DCAP: (CANONICALIZED, _format_date(year,month,day), _evidence(rule), None)
                                DCAP->>DRULES: _evidence(rule) (grammar/policy Authority, NOT engine-aware)
                                DRULES-->>DCAP: Evidence(rule, authority=STATIC Authority, NOT engine-aware)
                                DCAP-->>API: CapabilityResult(status=CANONICALIZED, value=YYYY-MM-DD, evidence)
                            else more than one survivor (Don't Guess)
                                DRES-->>DCAP: (AMBIGUOUS, None, _evidence("ambiguous_ordering" / "ambiguous_two_digit_year"), rendered candidates)
                                DCAP->>DRULES: _evidence("ambiguous_ordering" / "ambiguous_two_digit_year")
                                DRULES-->>DCAP: Evidence(rule, authority=STATIC Authority, NOT engine-aware)
                                DCAP-->>API: CapabilityResult(status=AMBIGUOUS, candidates=tuple of YYYY-MM-DD)
                            end
                        end
                    end
                end
            end
        end

        Note over API,ART: Stage 5 - validate then Stage 6 - classify (shared by both calls)
        alt capability_result.status is CANONICALIZED
            API->>VAL: validate_value(canonical, parsed_contract)
            alt validate_value raises UnsupportedContractError
                VAL-->>API: raise UnsupportedContractError
                API->>ART: _build_artifact UNSUPPORTED validation_unsupported_contract
                ART-->>Caller: ExecutionArtifact status UNSUPPORTED
            else validate_value returns normally
                VAL-->>VRES: ValidationResult(is_valid=True)
            end
        else capability_result.status is not CANONICALIZED
            API->>VRES: ValidationResult(is_valid=True)
        end

        API->>CLS: classify(capability_result, VRES)
        alt classify returns CANONICALIZED
            CLS-->>API: Status CANONICALIZED
        else classify returns AMBIGUOUS
            CLS-->>API: Status AMBIGUOUS (carries candidates)
        else classify returns INVALID
            CLS-->>API: Status INVALID
        else classify returns MISSING
            CLS-->>API: Status MISSING
        else classify returns UNSUPPORTED
            CLS-->>API: Status UNSUPPORTED
        end

        API->>ART: _build_artifact(registry, engine, parsed_contract, status, value, evidence, candidates)
        ART->>ART: for each evidence read ev.authority
        ART->>ART: collect distinct Authority editions cited (Law 12)
        ART->>ART: version_stamp = VersionStamp(paxman_version, contract_version, registry.capabilities_hash(), configuration_version)
        ART->>ART: candidates only when status is AMBIGUOUS else None
        ART-->>Caller: ExecutionArtifact(status, value, evidence, contract, authorities, version_stamp)
    end

    Note over Caller,REPLAY: Replay - verification + rehydration (no re-canonicalize)
    Caller->>REPLAY: replay(artifact, contract)
    REPLAY->>DSL: parse_contract(contract)
    alt parse_contract raises ContractError
        DSL-->>REPLAY: raise ContractError
        REPLAY-->>Caller: raise VersionMismatchError
    else parsed successfully
        REPLAY->>REPLAY: compare version_stamp.paxman_version with current paxman version
        alt paxman version mismatch
            REPLAY-->>Caller: raise VersionMismatchError
        else paxman version matches
            REPLAY->>REPLAY: compare version_stamp.contract_version with parsed.version_field
            alt contract version mismatch
                REPLAY-->>Caller: raise VersionMismatchError
            else contract version matches
                REPLAY->>REG: capabilities_hash()
                REG-->>REPLAY: sha256 of sorted capability names
                REPLAY->>REPLAY: compare version_stamp.capabilities_hash with registry hash
                alt capabilities hash mismatch
                    REPLAY-->>Caller: raise VersionMismatchError
                else capabilities hash matches
                    REPLAY->>REPLAY: compare artifact.replay_hash with sha256(canonical_bytes())
                    alt replay_hash mismatch
                        REPLAY-->>Caller: raise CanonicalizationError
                    else replay_hash matches
                        REPLAY->>ENG: Engine.from_artifact(artifact.authorities)
                        ENG->>ENG: merge recorded editions over default roster
                        ENG-->>REPLAY: reconstructed production Engine
                        REPLAY->>ENG: _verify_recorded_authorities(artifact.authorities)
                        alt a recorded edition is unknown or retired
                            ENG-->>REPLAY: raise UnknownAuthorityEdition (surfaces as replay failure)
                            REPLAY-->>Caller: raise UnknownAuthorityEdition
                        else all recorded editions known
                            REPLAY-->>Caller: return artifact unchanged byte for byte
                        end
                    end
                end
            end
        end
    end
```

## Object reference (every participant and what it really is)

- **paxman.canonicalize (engine.py)**: the single public entry point. Owns the pipeline (stages 0-6), the only place that freezes the registry, and the only place that builds the `ExecutionArtifact`.
- **default_registry / orchestrator_runtime**: module-level `CapabilityRegistry` singleton; frozen on first canonicalize.
- **CapabilityRegistry (capability_registry.py)**: the resolver. `resolve_all` iterates `cap.can_handle(contract, value)` over all registered capabilities, then **sorts claimants by name** so registration order cannot leak into the replay hash (Law 1). `capabilities_hash()` is `sha256` of the sorted capability names — recorded in the `VersionStamp`.
- **builtin_capabilities (discovery.py)**: returns the 10 built-in `Capability` objects (including `MoneyCapability`) loaded once before freeze.
- **parse_contract (dsl/parser.py)**: turns the `Money(...)` value object / dict DSL into a `CanonicalMoneyContract`. Raises `ContractError` on malformed input (mapped to `UNSUPPORTED` via `_StubContract`).
- **_StubContract (engine.py)**: a minimal contract stand-in used only when `parse_contract` fails, so the resulting artifact still carries a serializable contract.
- **Engine (engine_env.py)**: an immutable binding of authority names to concrete `Authority` editions. `Engine.default()` binds every authority to its latest edition; `engine.override()` re-binds one name per the contract's `authority_override`; `Engine.from_artifact()` rebuilds the exact production engine at replay time.
- **Authority (provenance/authority.py)**: a concrete cited source (a spec, dataset, or documented policy). Every non-routing `Evidence` carries one; routing/dispatch guards carry `None`.
- **MoneyCapability (money/canonicalizer.py)**: pure `(value, contract, engine) -> CapabilityResult` transform. Guards are sequential early-returns in this order: contract type -> value type -> missing -> strip -> recognize -> parse -> compose.
- **recognize_money / parse_amount (money/grammar.py)**: Layer 1 recognition (sign/symbol/code validation, never guesses currency) and Layer 2 amount parsing (separator convention by currency, thousands validation, exact `Decimal`, F1/Q1/Q2/Q3 rules). Both raise `ContractError` on failure, caught as `INVALID unrecognized_format`.
- **money/rules.py (_evidence + _RULE_AUTHORITIES)**: wraps the shared `_evidence` helper via `make_evidence_for`. Only ONE rule — `code_validated` — is engine-aware: `_ISO_4217_RULES = frozenset({"code_validated"})`, so only it re-resolves its `Authority` from the engine's bound ISO 4217 edition. All other rules (`missing_value`, `currency_from_contract`, `symbol_validated`, `preserved_sign`, `parsed_decimal`, `preserved_decimals`, `canonical_form`) carry STATIC `Authority` values from the manifest and are NOT engine-resolved. `not_a_money_contract`, `not_a_string_value`, `trimmed_whitespace`, `unrecognized_format` are routing guards with `authority=None`.
- **validate_value (core/validation.py)**: validates the canonical string against the contract; may raise `UnsupportedContractError` (defensive -> `UNSUPPORTED`).
- **ValidationResult (core/classification.py)**: the validation outcome object consumed by `classify`.
- **classify (core/classification.py)**: maps the `CapabilityResult` + `ValidationResult` to the final `Status` (CANONICALIZED / AMBIGUOUS / INVALID / MISSING / UNSUPPORTED).
- **ExecutionArtifact + VersionStamp (core/artifact.py)**: the returned artifact. `_build_artifact` collects the distinct `Authority` editions cited in the evidence (Law 12) and stamps `paxman_version`, `contract_version`, `capabilities_hash`, `configuration_version`.
- **replay (core/replay.py)**: re-parses the contract, verifies the `VersionStamp` (paxman + contract version), verifies `capabilities_hash` against the live registry, verifies `replay_hash == sha256(canonical_bytes())`, reconstructs the engine via `Engine.from_artifact`, then returns the artifact **unchanged**. It never re-runs `canonicalize`. Any mismatch raises `VersionMismatchError` (version/hash) or `CanonicalizationError` (replay_hash) or `UnknownAuthorityEdition` (retired edition).

## Notes

- Single claimant contract: the registry resolves exactly one capability (`MoneyCapability`) for a `CanonicalMoneyContract`. Zero claimants -> `UNSUPPORTED`; more than one -> `AMBIGUOUS`; an unparseable contract -> `UNSUPPORTED` via `_StubContract`, before any capability runs.
- Currency is never guessed (Law 3): `Money` requires `currency`; the grammar only validates that any symbol/code present matches the contract currency.
- Determinism / idempotence: `parts.canonical` (set when the input is the capability's own `"ISO4217:amount"` output) makes `parse_amount` skip the currency separator convention, so `canonicalize(canonicalize(x)) == canonicalize(x)`.
- Evidence authority (Law 14): routing/dispatch guards (`not_a_*_contract`, `not_a_string_value`, `trimmed_whitespace`, `unrecognized_format`) and the `MISSING`/`empty_value` outcomes carry `authority=None`; `missing_value` and the six canonical-form Money rules carry a STATIC `Authority` from the manifest. Only Money's `code_validated` is engine-aware (re-resolves the ISO 4217 edition from the bound `Engine`). Date rules are grammar/policy-sourced and never engine-resolved.
- Date dispatch order (deterministic predicates, never a guess): Unix epoch -> ISO 8601 date -> ISO 8601 datetime (with tz) -> naive datetime (AMBIGUOUS) -> US/EU numeric slash (MM/DD vs DD/MM per locale; 2-digit-year century policy) -> RFC 2822 -> enumeration pipeline (text-month + numeric-slash forms via `recognize` -> `generate_interpretations` -> `resolve_and_validate` -> `classify`). Earlier branches return directly; only text-month/numeric-slash inputs reach the grammar `recognize` layer.
- Replay does NOT re-canonicalize — it verifies and rehydrates. A paxman-version, contract-version, or capabilities-hash mismatch raises `VersionMismatchError`; a replay-hash mismatch raises `CanonicalizationError`; a retired/unknown recorded edition raises `UnknownAuthorityEdition`.
