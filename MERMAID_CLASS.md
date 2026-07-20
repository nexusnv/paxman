# Money Canonicalization — Class Diagram

Class diagram of every class involved in **Money canonicalization**, extracted
from the actual `src/` code (verified against the on-disk source). The diagram
covers the Money capability package (`src/paxman/_capabilities/money/`), the
shared capability scaffolds (`src/paxman/_capabilities/_shared/`), the core
types it consumes (`src/paxman/_core/`), and the provenance model
(`src/paxman/_provenance/`).

Runtime flow (control surface only; see `MERMAID.md` for the sequence view):

- `MoneyCapability.canonicalize(value, contract, engine)` is the entry point.
- It delegates recognition to `grammar.recognize_money` → returns `MoneyParts`.
- It delegates amount parsing to `grammar.parse_amount` → canonical decimal `str`.
- It emits `Evidence` (each carrying an `Authority`) via the engine-aware
  `_evidence` closure built in `rules.py` (`make_evidence_for`).
- It returns a `CapabilityResult(status, value, evidence, candidates)`.
- `CanonicalMoneyContract` satisfies the `Contract` Protocol structurally and is
  the value object the capability operates on.

```mermaid
classDiagram
    %% ===== Money capability package (src/paxman/_capabilities/money/) =====

    class MoneyCapability {
        +str name = "money_canonicalization"
        +can_handle(contract, value) bool
        +canonicalize(value, contract, engine) CapabilityResult
    }

    class CanonicalMoneyContract {
        <<@attrs.frozen>>
        +str currency
        +bool allow_symbol
        +bool allow_code
        +bool strip_spaces
        +str kind
        +int version
        +int version_field
        +Any authority_override
        +as_dict() dict~str,Any~
    }

    class MoneyParts {
        <<@attrs.frozen>>
        +str currency
        +str amount
        +str|None symbol
        +str|None code
        +str sign
        +bool canonical
    }

    %% Module-level functions in money/grammar.py (callables, not classes)
    class MoneyGrammar {
        <<module functions>>
        +recognize_money(raw, contract) MoneyParts
        +parse_amount(amount, currency, canonical) str
        +_detect_symbol(text, contract) tuple
        +_detect_code(text, contract) tuple
        +_split_sign(text) tuple
        +_validate_thousands(segments, sep_name, raw) void
    }

    %% rules.py: authority manifest + evidence closure (module-level)
    class MoneyRules {
        <<module-level>>
        -_RULE_AUTHORITIES : Mapping~str, Authority|None~
        -_ISO_4217_RULES : frozenset~str~
        -_evidence : Callable (engine-aware closure)
        +get_money_rules(contract) list~dict~
    }

    %% ===== Shared capability scaffold (src/paxman/_capabilities/_shared/) =====

    class CapabilityBase {
        <<abstract base>>
        +str name
        +CanHandle can_handle
        +canonicalize(value, contract, engine) object
        +validate(value, contract) ValidationResult
    }

    class CanHandle {
        <<type alias: Callable[[Any, Any], bool]>>
    }

    class EvidenceHelper {
        <<module functions in _shared/evidence.py>>
        +make_evidence(manifest) Callable
        +make_evidence_for(manifest, authority_name, registry_rules) Callable
        +rule_authorities(mapping) Callable
    }

    %% ===== Core contract Protocol (src/paxman/_core/contracts.py) =====

    class Contract {
        <<@runtime_checkable Protocol>>
        +kind: str   «property»
        +version_field: int   «property»
        +authority_override: Any|None   «property»
        +as_dict() dict~str,Any~
    }

    class _StubContract {
        +str _kind
        +int _version_field
        +Any|None _authority_override
        +kind: str   «property»
        +version_field: int   «property»
        +authority_override: Any|None   «property»
        +as_dict() dict~str,object~
    }

    %% ===== Capability Protocol (src/paxman/_capabilities/protocol.py) =====

    class Capability {
        <<@runtime_checkable Protocol>>
        +str name
        +CanHandle can_handle
        +canonicalize(value, contract, engine) CapabilityResult
    }

    %% ===== Core result / status (src/paxman/_core/) =====

    class CapabilityResult {
        <<@attrs.frozen>>
        +Status status
        +str|None value
        +tuple~Evidence,...~ evidence
        +tuple~str,...~|None candidates
    }

    class VersionStamp {
        <<@attrs.frozen>>
        +str paxman_version
        +int contract_version
        +str capabilities_hash
        +str configuration_version
    }

    class Status {
        <<enum.Enum>>
        CANONICALIZED
        INVALID
        MISSING
        AMBIGUOUS
        UNSUPPORTED
    }

    %% ===== Engine (src/paxman/_core/engine_env.py) =====

    class Engine {
        -dict~str,Authority~ _authorities
        +default() Engine$
        +from_artifact(authorities) Engine$
        +authority(name) Authority
        +override(name, selector) Engine
        +authorities() tuple~Authority,...~
    }

    %% ===== Provenance model (src/paxman/_provenance/) =====

    class Evidence {
        <<@attrs.frozen>>
        +str rule
        +str detail
        +Authority|None authority
    }

    class Authority {
        <<@attrs.frozen>>
        +str name
        +str edition
        +AuthorityKind kind
        +str version
        +str|None publisher
        +str|None released_on
        +AuthorityLifecycle lifecycle
        +str|None checksum
        +str|None retrieved_at
        +bool supports_multiple_editions
        +Any dataset
        +section(section) Authority
        +retrieved(retrieved_at) Authority
    }

    class AuthorityKind {
        <<Literal type>>
        "grammar"
        "registry"
        "normative_standard"
        "taxonomy"
        "platform-behaviour"
        "policy"
    }

    %% ===== Relationships =====

    %% MoneyCapability structurally satisfies the Capability Protocol
    MoneyCapability ..|> Capability : satisfies (structural)

    %% CapabilityBase is the shared base (MoneyCapability subclasses it in v2)
    MoneyCapability --|> CapabilityBase : subclasses

    %% Capability protocol references core types
    Capability ..> Contract : consumes
    Capability ..> Engine : consumes
    Capability ..> CapabilityResult : returns

    %% CanonicalMoneyContract satisfies the Contract Protocol structurally
    CanonicalMoneyContract ..|> Contract : satisfies (structural)

    %% MoneyCapability uses the contract, grammar, and rules
    MoneyCapability --> CanonicalMoneyContract : operates on
    MoneyCapability --> MoneyGrammar : recognize_money / parse_amount
    MoneyCapability --> MoneyRules : _evidence closure

    %% Grammar returns MoneyParts; grammar validates against the contract
    MoneyGrammar ..> MoneyParts : returns
    MoneyGrammar ..> CanonicalMoneyContract : validates currency/symbol/code

    %% canonicalize returns a CapabilityResult carrying Status + Evidence
    MoneyCapability ..> CapabilityResult : returns
    CapabilityResult --> Status : status
    CapabilityResult --> Evidence : evidence (tuple)

    %% Engine-aware evidence resolves Authority from the engine
    MoneyRules ..> Engine : re-resolves edition
    MoneyRules ..> Authority : manifest values
    MoneyRules ..> EvidenceHelper : make_evidence_for

    %% Evidence carries an Authority
    Evidence --> Authority : authority (|None)

    %% CapabilityBase wires the shared CanHandle type
    CapabilityBase --> CanHandle : can_handle attribute
    Capability ..> CanHandle : can_handle type

    %% AuthorityKind is the kind field of Authority
    Authority --> AuthorityKind : kind
```

## Notes on the evidence

- `MoneyCapability` (canonicalizer.py:24) is the only capability class; it
  subclasses `CapabilityBase` (`_shared/base.py:128`) and structurally satisfies
  the `Capability` Protocol (`protocol.py:26`).
- `CanonicalMoneyContract` (contract.py:247) is an `@attrs.frozen` value object
  that satisfies the `Contract` Protocol (`_core/contracts.py:15`) structurally.
- Recognition produces `MoneyParts` (grammar.py:171), an `@attrs.frozen` value
  object. `recognize_money` and `parse_amount` are module-level functions.
- The Law-14 rule→authority manifest (`_RULE_AUTHORITIES`) and the engine-aware
  `_evidence` closure live in `rules.py`; the closure is produced by
  `make_evidence_for` (`_shared/evidence.py:51`).
- `CapabilityResult` (`result.py:33`) carries `Status` (`status.py:8`) and a
  tuple of `Evidence` (`_provenance/evidence.py:15`), each of which carries an
  `Authority` (`_provenance/authority.py:63`).
- `Engine` (`engine_env.py:77`) is the immutable authority-edition binding the
  capability reads via the engine-aware evidence closure (Concern 3 — replay is
  deterministic against the pinned edition).
- `Money()`, `_build_money()`, `_validate_currency()`, etc. are module-level
  helper functions/validators in `contract.py`, not classes, so they are omitted
  from the class diagram (they back the `CanonicalMoneyContract` value object).
