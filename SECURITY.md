# Security and PII

> **Status:** Draft v1.
> **Audience:** Paxman users (especially those in regulated industries) and Paxman contributors.
> **Related docs:** [PRD.md §15 Compliance and Data Privacy Notes](./PRD.md), [ARCHITECTURE.md §13 Security and PII Model](./ARCHITECTURE.md), [GLOSSARY.md](./GLOSSARY.md)

This document is Paxman's **threat model** and PII handling policy. It is non-normative: the **caller** is responsible for their own compliance posture, but Paxman's defaults are designed to make compliance easier.

---

## 1. Threat Model

### 1.1 What Paxman assumes about its environment

- Paxman runs in the caller's process. The caller controls the process boundary, OS, file system, and network.
- Paxman has no built-in network server; it does not bind to a port.
- The caller is responsible for transport (TLS, mTLS, etc.) if Paxman is wrapped in a service.
- The caller is responsible for storage (encryption at rest, access control) of artifacts.

### 1.2 What Paxman does NOT defend against

- **Compromise of the caller's process.** If the caller is compromised, Paxman's secrets and inputs are exposed.
- **Compromise of inference providers.** If a remote LLM provider is compromised, prompts and completions may leak. Callers are responsible for provider selection and contracts.
- **Storage compromise.** Paxman does not store artifacts; the caller is responsible for their security.
- **Side-channel attacks on the caller's process.** Paxman does not protect against memory dumps, swap, core dumps, etc.

### 1.3 What Paxman DOES defend against (V1)

- **Accidental leakage of raw input to logs.** Default: no raw input in logs. Caller opt-in via `Policy.log_raw_input`.
- **Accidental embedding of inference I/O in artifacts.** Default: prompts and completions are not in artifacts. Caller opt-in via `Policy.record_inference_io`.
- **Artifact tampering.** The `replay_hash` detects any modification to a stored artifact.
- **Hardcoding of provider secrets.** Secrets are passed by reference (env var name or secret store handle), never embedded in artifacts.
- **Cross-tenant confusion (when wrapped in a multi-tenant service).** The caller is responsible; Paxman provides no tenant context.

---

## 2. PII Handling Defaults

Paxman's defaults are designed to **minimize** PII leakage. The defaults are:

| Data type | Default behavior | Override |
|---|---|---|
| Raw input | Held in memory only. Never written to logs, telemetry, or artifacts. | `Policy.log_raw_input: bool = False` (default) |
| Inference prompts | Held in memory only. Not in artifacts. | `Policy.record_inference_io: bool = False` (default) |
| Inference completions | Same as prompts. | Same. |
| Resolved values | Stored in the artifact. The caller controls artifact storage. | No override. |
| Evidence payloads | Stored as references (capability id, span offsets, source identifier). Payload content not embedded. | `Policy.embed_evidence_payload: bool = False` (default) |
| PII in resolved values | Caller is responsible for sanitizing input or scrubbing artifacts. | No override. |

### 2.1 What "evidence reference" means

When the `validation` capability verifies a candidate value `1234.56` against an invoice, the evidence reference contains:

- Capability id and version (`validation@1.0`)
- Source span (e.g., `input[124:131]`)
- Field path (`line_items[0].price`)
- Timestamp of capture (NOT included in the replay hash; included in the artifact for human inspection)

It does **not** contain the value itself (which is in `field_results[].value`).

### 2.2 Caller responsibilities for PII

Paxman does not auto-redact PII in V1. The caller is responsible for:

- **Pre-processing** input to remove PII before normalization (e.g., redacting names, addresses).
- **Post-processing** artifacts to scrub PII before storage.
- **Access control** on stored artifacts.
- **Retention policy** on stored artifacts.
- **Right-to-erasure compliance** (GDPR Art. 17) — Paxman has no data store, so erasure is the caller's job.

---

## 3. Provider Secrets

### 3.1 How secrets are passed

Paxman does not embed provider secrets in artifacts. The caller is expected to:

1. Store the secret in an environment variable, a secret manager (AWS Secrets Manager, HashiCorp Vault, etc.), or a Kubernetes secret.
2. Pass a **reference** to Paxman, e.g., `{"OPENAI_API_KEY": "env:OPENAI_API_KEY"}` or `{"OPENAI_API_KEY": "vault:secret/openai#api_key"}`.
3. Paxman resolves the reference at the time of the capability invocation.

### 3.2 What the artifact contains

The artifact contains the **reference**, not the secret. For example, the inference evidence might include `provider: "openai"`, `model: "gpt-5"`, but not the API key.

### 3.3 What the caller must do

- Use a secret manager.
- Rotate secrets regularly.
- Audit secret access.
- Never log the artifact if `Policy.embed_evidence_payload=True` and an evidence payload contains a secret.

---

## 4. Prompt Injection

The `inference` capability accepts a prompt and returns a completion. Paxman treats inference output as **untrusted** until validated.

### 4.1 Default posture

- All inference candidates pass through the `validation` capability (or a downstream `ValidationPolicy`).
- The Reconciler rejects any candidate that fails validation.
- No inference output is ever accepted as a final value without validation.

### 4.2 What the caller must do

- Use the `validation` capability to enforce domain rules (e.g., "supplier_name must not be empty").
- Use a `ValidationPolicy` to enforce cross-field rules (e.g., "total = sum(line_items[].price) ± 0.01").
- Treat any field that depends on inference as **adversarial input** and validate strictly.

### 4.3 What V1 does NOT do

- V1 does not sandbox inference prompts.
- V1 does not detect prompt-injection attacks in the input.
- V1 does not limit the size of inference prompts or completions.

These are V2 features (or caller's responsibility via capability policy).

---

## 5. Multi-Tenancy

Paxman is a library. It has no concept of tenants. If a caller wraps Paxman in a multi-tenant service, the caller is responsible for:

- Routing the right `input_data` and `contract` to the right tenant's Paxman call.
- Storing the right artifact in the right tenant's storage.
- Enforcing tenant isolation at the storage layer.
- Enforcing tenant isolation at the inference provider (per-tenant API keys, per-tenant rate limits).

Paxman does not provide a `tenant_id` parameter in V1. If a future version does, it will be opt-in.

---

## 6. Audit Trail

Paxman's `ExecutionArtifact` is designed to be auditable. Each resolved value carries:

- `evidence_refs[]` — pointers to the evidence.
- `confidence` — the Reconciler's trust in the value.
- `value` — the resolved value.

This is sufficient for most audit needs. For regulated industries (finance, healthcare), the caller may also need:

- **Tamper-evident storage** — Paxman provides `replay_hash`; the caller stores the hash in a write-once store.
- **Cryptographic signing** — Paxman does not sign artifacts in V1. The caller can sign the artifact externally (e.g., with a PAdES signature or an HMAC).
- **Provenance standards** — Paxman's evidence model is inspired by [W3C PROV](https://www.w3.org/TR/prov-overview/) but is not a strict implementation. A future V2 may add a W3C-PROV-compatible serializer.

---

## 7. Vulnerability Reporting

If you find a security vulnerability in Paxman:

1. **Do not** open a public GitHub issue.
2. Email `security@paxman.example` (placeholder — replace with the actual security email when the project is hosted).
3. Include a description of the vulnerability, the impact, and a reproducer.
4. Allow up to 90 days for a fix before public disclosure.

The Paxman team commits to:

- Acknowledging reports within 3 business days.
- Providing a fix timeline within 14 days.
- Crediting the reporter in the security advisory (unless they prefer anonymity).

---

## 8. Compliance Notes

Paxman is a library. The caller is responsible for their own compliance posture. The following notes are non-binding.

### 8.1 GDPR

- **Data minimization:** Paxman's defaults store evidence references, not raw input.
- **Right to erasure:** The caller is responsible for deleting stored artifacts.
- **Data residency:** Inference provider selection is the caller's responsibility.

### 8.2 HIPAA

- Paxman does not store Protected Health Information (PHI).
- The caller is responsible for ensuring their storage and transport meet HIPAA requirements.
- Inference providers used with PHI must be on a BAA.

### 8.3 PCI-DSS

- Paxman does not store credit card numbers as `MONEY`. The caller is responsible for tokenizing PAN before passing it to Paxman.
- Inference providers used with PCI data must be PCI-compliant.

### 8.4 SOC 2

- Paxman's `ExecutionArtifact` is auditable; the `replay_hash` provides tamper detection.
- The caller is responsible for logging, access control, and monitoring.

---

## 9. See also

- [PRD.md §15 Compliance and Data Privacy Notes](./PRD.md)
- [ARCHITECTURE.md §13 Security and PII Model](./ARCHITECTURE.md)
- [GLOSSARY.md](./GLOSSARY.md)
- [DEPENDENCIES.md](./DEPENDENCIES.md)
- [EXTENDING.md](./EXTENDING.md) — adding new inference providers
