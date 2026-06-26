# Paxman Maintainers

> **Status:** Single-maintainer project (NexusNV). Last updated 2026-06-26.
> **Audience:** Contributors, users, and downstream maintainers.

This document lists the active maintainers of the Paxman project and their contact
preferences. For contribution workflow, see [`CONTRIBUTING.md`](../CONTRIBUTING.md). For
security disclosures, see [`SECURITY.md`](../SECURITY.md).

## Active Maintainers

| Name | Role | GitHub | Contact | Areas of Responsibility |
|------|------|--------|---------|--------------------------|
| NexusNV | Project owner & sole maintainer | [@nexusnv](https://github.com/nexusnv) | security@nexusnv.net | All areas: design, code, release, security, docs |

> The project is currently maintained by a single individual. As the project grows,
> this list will expand to include additional maintainers with clearly defined roles.

## Areas of Responsibility (current single-maintainer model)

- **Architecture & ADRs:** @nexusnv — all architecture decisions documented in
  [`docs/adr/`](adr/)
- **Code review:** @nexusnv — all changes to `src/paxman/` require explicit approval
- **Release & publishing:** @nexusnv — all releases follow
  [`DEVELOPMENT.md`](../DEVELOPMENT.md)
- **Security & disclosures:** `security@nexusnv.net` — see
  [`SECURITY.md`](../SECURITY.md)
- **Documentation:** @nexusnv — all docs in `docs/`, `*.md` at repo root

## How to Reach the Maintainers

| Channel | When to use |
|---------|-------------|
| **GitHub issue** | Bug reports, feature requests, general questions |
| **`security@nexusnv.net`** | **Security vulnerabilities only** (per [`SECURITY.md`](../SECURITY.md)) |
| **Pull request review** | Contributing code, docs, or tests |
| **GitHub Discussions** | Design questions, brainstorming (TBD — not yet enabled) |

## Becoming a Maintainer

Paxman is currently a single-maintainer project. As it grows, additional maintainers
will be added based on:

1. **Sustained contribution quality** — multiple merged PRs demonstrating design
   judgment and code quality
2. **Domain expertise** — familiarity with the relevant subsystem (contract, planner,
   executor, reconciler, artifact)
3. **Community trust** — respectful engagement in issues, reviews, and discussions
4. **Time commitment** — realistic capacity to respond to issues and review PRs

The current maintainer will reach out to high-quality contributors directly. If you
believe you meet the criteria and would like to be considered, open an issue or
email `security@nexusnv.net`.

## Maintainer Emeritus

None yet.

## See also

- [`CONTRIBUTING.md`](../CONTRIBUTING.md) — contribution workflow
- [`SECURITY.md`](../SECURITY.md) — security policy and disclosure process
- [`DEVELOPMENT.md`](../DEVELOPMENT.md) — local dev setup, release process
- [`docs/adr/`](adr/) — architecture decision records
