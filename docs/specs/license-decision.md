# License Decision — Paxman V1

> **Status:** Accepted
> **Date:** 2026-06-22
> **Deciders:** Paxman core team
> **Related docs:** [README.md](../../README.md) §License, [DEPENDENCIES.md](../../DEPENDENCIES.md) §2, [ADR-0008](../adr/0008-license-decision.md)

---

## 1 Decision Summary

**MIT is chosen as the license for Paxman V1.** The project is a developer-focused Python library with a minimal dependency surface and no patent concerns. MIT's simplicity, ecosystem prevalence, and low downstream friction make it the right fit. The trade-off analysis and full rationale follow. The matching architectural decision is recorded in [ADR-0008](../adr/0008-license-decision.md).

---

## 2 Background

The license is one of four prerequisites for Sprint 1, which creates `pyproject.toml` and the `LICENSE` file at the repository root. Without a resolved license, the package cannot be built, published to PyPI, or included in downstream distributions.

`README.md` §License currently reads: *"MIT (or Apache-2.0 — final TBD by the team)."* This document resolves that TBD.

The decision must be made now because:

1. `pyproject.toml` requires a `license` field — the build backend (`hatchling`) will reject a missing or ambiguous license declaration.
2. PyPI metadata requires a license classifier — the `License :: OSI Approved :: MIT License` classifier is part of the package metadata that pip, pipx, and dependency resolvers display to users.
3. Downstream packagers (conda-forge, Debian, Gentoo) require a license file to exist before they will accept the package into their repositories. Conda-forge's review checklist explicitly flags missing or ambiguous licenses.
4. Contributors need to know the terms under which they are submitting code. Without a clear license, the default copyright applies — contributors retain all rights and grant no distribution permission.
5. The `DEPENDENCIES.md` §2 core dependency policy locks the legal review surface to 2 pure-Python packages. The project's own license must be resolved before its dependency tree can be fully audited.

The license decision is non-reversible without a new ADR. Once the `LICENSE` file is committed and the package is published to PyPI, changing the license requires a new major version, a deprecation cycle, and explicit contributor consent. Getting it right on the first commit matters.

### 2.1 Sprint dependencies

The license is a blocking prerequisite for the following Sprint 1 deliverables:

| Deliverable | Sprint | Why the license is needed |
|---|---|---|
| `LICENSE` file | Sprint 1 (D1.4) | The file contains the license text itself. |
| `pyproject.toml` | Sprint 1 | The `license` field is required metadata. |
| PyPI classifier | Sprint 9/10 | The `License :: OSI Approved :: MIT License` classifier is part of the package metadata. |
| Conda-forge recipe | Post-1.0 | Conda-forge review requires a clear license declaration. |

Without a resolved license, none of these can proceed. The license is not a "nice to have" — it is a hard blocker for the first usable release.

---

## 3 The Two Candidates

### 3.1 MIT License

The MIT License is a permissive open-source license originating from the Massachusetts Institute of Technology. It is the most widely used license in the Python ecosystem.

- **Permissions:** Use, copy, modify, merge, publish, distribute, sublicense, sell.
- **Conditions:** Include the copyright notice and permission notice in all copies or substantial portions.
- **Limitations:** No liability, no warranty.
- **Patent grant:** No explicit patent grant. Users rely on the implied license that accompanies the copyright grant.
- **NOTICE file:** Not required. No attribution chain to maintain.
- **Typical users:** The majority of Python libraries on PyPI; developer tools, web frameworks, CLI utilities, data processing libraries.
- **Ecosystem share:** ~70% of the top 400 PyPI packages by download count (2024). Used by Flask, Requests, NumPy, Pandas, scikit-learn, pip, and the Python standard library's ancillary tools.
- **SPDX identifier:** `MIT`.
- **OSI approved:** Yes.

### 3.2 Apache-2.0 License

The Apache License 2.0 is a permissive open-source license maintained by the Apache Software Foundation. It is the standard for corporate-backed and data/ML projects.

- **Permissions:** Same as MIT — use, copy, modify, merge, publish, distribute, sublicense, sell.
- **Conditions:** Include the copyright notice, the NOTICE file (if one exists), and a copy of the license. State significant changes to modified files.
- **Limitations:** No liability, no warranty. Trademark use not granted.
- **Patent grant:** Explicit patent grant from each contributor to the user. Automatic, royalty-free, perpetual.
- **NOTICE file:** Required if the upstream project ships one; attribution chain must be maintained across all derivative works and distributions.
- **Typical users:** Data/ML platforms (TensorFlow, PyTorch, Kubeflow), infrastructure (Kubernetes, Istio), corporate-backed projects, Apache Foundation projects.
- **Ecosystem share:** ~15% of the top 400 PyPI packages; dominant in the data/ML and cloud-native spaces.
- **SPDX identifier:** `Apache-2.0`.
- **OSI approved:** Yes.

### 3.3 Why not dual MIT/Apache-2.0?

Some projects (notably the Rust ecosystem) offer dual MIT/Apache-2.0 licensing, letting the user choose. This option was considered and rejected:

- It adds complexity to every distribution and attribution.
- It is confusing for users unfamiliar with dual licensing.
- It is overkill for a library with no patent risk.
- It doubles the license-related metadata in `pyproject.toml`, PyPI, and downstream packages.

---

## 4 Trade-off Analysis

| Axis | MIT | Apache-2.0 | Advantage |
|---|---|---|---|
| **Permission scope** | Use, modify, distribute, sublicense, sell | Identical | Tie |
| **Conditions (attribution)** | Copyright + permission notice in copies | Copyright + NOTICE file + license copy + change statements | MIT (fewer conditions) |
| **Patent protection for users** | None explicit; relies on implied license | Explicit, automatic, royalty-free patent grant from contributors | Apache-2.0 |
| **Patent retaliation clause** | None | License terminates if user sues contributor for patent infringement | Apache-2.0 |
| **Length / complexity** | ~200 lines, 3 clauses | ~400 lines, full legal text + appendix | MIT (simpler) |
| **NOTICE file maintenance** | Not required | Required; attribution chain must be maintained | MIT (less burden) |
| **Compatibility with permissive deps (BSD, MIT, Apache-2.0)** | Fully compatible | Fully compatible | Tie |
| **Compatibility with copyleft deps (GPL, AGPL)** | Compatible (MIT is GPL-compatible) | Compatible (Apache-2.0 is GPL-compatible since GPL-3.0; not compatible with GPL-2.0) | MIT (broader compatibility) |
| **Ecosystem fit** | Standard for Python developer libraries | Standard for data/ML and cloud-native projects | MIT for Paxman's category |
| **Trademark grant** | Implicit (no explicit clause) | Explicitly excluded | MIT (no confusion) |
| **Downstream packaging friction** | Low; universally recognized | Low; universally recognized | Tie |
| **CLAs / corporate contribution** | Not required | Not required, but corporate contributors often prefer Apache-2.0 | Tie |

### 4.1 Copyleft compatibility note

Paxman core cannot depend on copyleft packages per `DEPENDENCIES.md` §2. However, users may install Paxman in environments that include GPL-licensed dependencies. MIT is compatible with all GPL versions (GPL-2.0, GPL-3.0, AGPL-3.0). Apache-2.0 is compatible with GPL-3.0 and AGPL-3.0 but **not** with GPL-2.0. Since Paxman cannot control its downstream environment, MIT's broader compatibility is a practical advantage.

---

## 5 Decision Criteria

The following factors specific to Paxman influenced the choice:

1. **Project type.** Paxman is a developer library, not a data/ML platform or infrastructure project. MIT is the default for this category. The PRD (§2) defines Paxman as a "contract-driven, deterministic normalization engine" — a library, not a service.

2. **Target users.** Backend engineers, AI engineers, SaaS teams, and platform teams (PRD §6.1). These users expect permissive, friction-free licensing. None of the four primary personas (backend developer, AI engineer, SaaS team, platform team) require patent protection.

3. **Use cases.** Invoice/quotation/procurement normalization (PRD §7). No domain-specific patent exposure. The use cases involve document parsing, regex extraction, and inference orchestration — none of which are patent-encumbered.

4. **Dependency policy.** Core dependencies are limited to 2 pure-Python packages (`attrs`, `typing-extensions`) with no copyleft or patent-encumbered transitive dependencies (DEPENDENCIES.md §2). The legal review surface is tiny. Both core dependencies are MIT-licensed.

5. **No patent concerns.** Paxman does not implement patented algorithms. Normalization, regex extraction, and inference orchestration are not patent-encumbered domains. The project does not hold patents and does not plan to file any.

6. **Simplicity.** A 200-line license is easier to review, embed, and reference than a 400-line one. Contributors can read and understand it in seconds. Downstream legal teams can approve it without escalation.

7. **Ecosystem convention.** The Python packaging ecosystem (PyPI, conda-forge, pip) defaults to MIT. Deviating requires justification. Choosing MIT means Paxman matches the licensing expectations of 70% of the packages its users already depend on.

8. **No NOTICE file burden.** MIT does not require maintaining a NOTICE file. Apache-2.0 does. For a library with a small team and no corporate attribution requirements, the NOTICE file is pure overhead.

---

## 6 Rationale

Paxman is a developer library consumed by engineers integrating it into their own services. It is not a platform, not a service, and not a user-facing product. The primary interaction model is `pip install paxman` followed by a few lines of Python. MIT is the standard license for this category, and there is no compelling reason to deviate.

The patent landscape around document normalization, regex extraction, and inference orchestration is not a concern for Paxman. The project does not implement patented algorithms, does not hold patents, and does not operate in a patent-litigious domain (biotech, telecom, finance-specific methods). Apache-2.0's explicit patent grant is a valuable feature for projects where contributor patents are a real risk — Paxman is not one of those projects. If this changes, the decision can be revisited (see §7).

MIT's simplicity is a practical advantage. The full license text is 200 lines. Contributors, downstream packagers, and legal reviewers can assess it in minutes. Apache-2.0 is twice as long, requires maintaining a NOTICE file for attribution, and imposes change-statement obligations on derivative works. For a library with a two-package core and no corporate CLA requirement, this additional complexity is not justified.

Ecosystem fit matters. The majority of Python libraries on PyPI use MIT. Conda-forge, Debian, and Gentoo package MIT-licensed projects routinely. Adopting MIT means Paxman fits the default expectations of every downstream distribution channel without special handling. A conda-forge reviewer seeing "MIT" in the recipe does not need to check for NOTICE files or patent clauses — the review is a formality.

The 2-package core dependency policy (DEPENDENCIES.md §2) keeps the legal review surface minimal. Both `attrs` and `typing-extensions` are MIT-licensed. There are no copyleft, patent-encumbered, or ambiguously licensed transitive dependencies to worry about. A more complex license would add overhead disproportionate to the risk it mitigates. The entire dependency tree (core + all optional extras) can be audited in under an hour.

Finally, MIT is the most recognizable permissive license in the Python ecosystem. When a developer sees "MIT" in a `pyproject.toml` or on PyPI, they know exactly what it means. There is no ambiguity, no hidden conditions, and no need to read a NOTICE file or track attribution chains. This clarity aligns with Paxman's design philosophy: small, predictable, learnable-in-minutes.

The contributor experience also favors MIT. Contributors do not need to read a 400-line license to understand what they are agreeing to. They do not need to maintain a NOTICE file in their fork. They do not need to add change statements to every modified file. The contribution barrier is as low as possible — which matters for a project that hopes to attract community contributions as it matures.

### 6.1 Why Apache-2.0's patent grant does not matter for Paxman

Apache-2.0's defining feature is its explicit patent grant: every contributor automatically grants users a royalty-free, perpetual patent license for any patents that cover their contribution. This is valuable for projects in patent-heavy domains — operating systems, compilers, networking protocols, cryptography. It is not valuable for Paxman.

Paxman's codebase consists of:

- A rule-based planner (pure Python, no algorithms of patentable novelty).
- Regex extraction (standard library `re` module).
- Text extraction (delegating to external libraries).
- Lookup/retrieval (dictionary and table lookups).
- Inference (delegating to external LLM providers — the provider owns the IP, not Paxman).
- Validation (schema checking against caller-provided contracts).

None of these areas have active patent litigation or known patent claims. The risk of a contributor unknowingly infringing a patent with a Paxman contribution is negligible. If this risk changes — for example, if Paxman adds a novel normalization algorithm — the license can be revisited (see §7).

---

## 7 When MIT Would Be Wrong

The project owners should reconsider this decision and adopt Apache-2.0 if any of the following conditions arise:

1. **Patent-litigious adoption.** If Paxman is adopted inside a domain where patent grants materially matter — biotech, telecom, finance-specific methods — and users explicitly request patent protection. This would be signaled by GitHub issues or direct requests from adopters.

2. **Corporate sponsor requirement.** If a corporate sponsor or major contributor requires Apache-2.0 for compatibility with their internal open-source policy. Many enterprise legal teams have blanket policies that prefer Apache-2.0 for any project they contribute to or depend on.

3. **Contributor patent claims.** If a contributor joins with patent claims they want to share under an explicit patent grant rather than an implied license. This is unlikely for a normalization library but cannot be ruled out if Paxman is adopted in patent-heavy industries.

4. **Inference provider patents.** If a future inference provider integration involves patented methods and the provider requires Apache-2.0 compatibility. V1 ships a stub provider, but V2 will integrate real inference APIs — if those APIs have patent implications, the license may need to change.

5. **GPL-2.0-only downstream.** If a significant downstream consumer requires GPL-2.0 compatibility specifically. Apache-2.0 is incompatible with GPL-2.0, but MIT is compatible. This scenario favors MIT, not Apache-2.0 — but it is worth noting as a constraint on the reverse decision.

In any of these cases: write a new ADR (ADR-0008-supersede) marking this one Superseded, adopt Apache-2.0, and update `README.md`, `pyproject.toml`, and `DEPENDENCIES.md` accordingly. The new ADR must document the specific trigger and the rationale for the change.

---

## 8 Next Steps

1. **Add `LICENSE` file** to the repository root containing the standard MIT license text with the copyright line `Copyright (c) 2026 Paxman contributors`. (Sprint 1 deliverable per `sprint-01-foundation.md` D1.4.)
2. **Update `README.md` §License** to: `MIT. See [LICENSE](./LICENSE).` — removing the TBD.
3. **Update `pyproject.toml`** (when created in Sprint 1) to declare `license = { text = "MIT" }`.
4. **Update `DEPENDENCIES.md`** §2 if it references the license decision.
5. **Configure PyPI metadata** (Sprint 9/10) to use the `License :: OSI Approved :: MIT License` classifier.
6. **Verify the LICENSE file** matches the [choosealicense.com MIT template](https://choosealicense.com/licenses/mit/) verbatim, with only the copyright line customized.

---

## 9 References

- [ADR-0008: License Decision](../adr/0008-license-decision.md) — the matching MADR-format ADR.
- [README.md §License](../../README.md#license) — the TBD being resolved.
- [DEPENDENCIES.md §2](../../DEPENDENCIES.md#2-core-dependencies) — core dependency policy (2 packages, no copyleft).
- [PRD.md §6.1](../../PRD.md#61-primary-personas) — target users (backend engineers, AI engineers, SaaS teams, platform teams).
- [PRD.md §7](../../PRD.md#7-primary-use-cases) — primary use cases (invoice, quotation, procurement normalization).
- [SPDX License List](https://spdx.org/licenses/) — MIT identifier: `MIT`.
- [choosealicense.com](https://choosealicense.com/licenses/mit/) — MIT summary and comparison.
- [OpenSource.org — MIT License](https://opensource.org/licenses/MIT) — OSI approval.
