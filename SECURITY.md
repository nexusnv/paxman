# Security

Paxman is a deterministic canonicalization engine. Its security profile
is small: no network I/O, no subprocess execution, no environment-variable
reads, no filesystem access. The library is a pure function of
`(input, contract, registered capabilities, configuration, Paxman version)`.

## Reporting a vulnerability

If you have found a security vulnerability in Paxman, please report it
privately. Do not open a public issue.

Open a private security advisory on the project's security tab:

- Go to the project's main page on its source-hosting platform.
- Click the **Security** tab.
- Click **Report a vulnerability**.
- Fill in the form with the details described below.

If private advisory reporting is unavailable, contact the project
maintainers through the channel listed in `pyproject.toml`
(`[project] authors`) or the source-hosting platform's owner contact.

## What to include

A useful security report includes:

- A short description of the vulnerability and its impact.
- The Paxman version affected (run
  `uv run python -c "import paxman; print(paxman.__version__)"`).
- The Python version and the operating system.
- A minimal reproducer (the smallest code that triggers the issue).
- Whether the issue is exploitable in the default configuration
  (no custom capabilities registered, no `register_capability` calls
  in the reproducer).

## What to expect

- **Acknowledgement** within 7 days of the report.
- **A status update** within 30 days describing the planned fix or the
  reason for declining.
- **A fix and a release** for confirmed vulnerabilities, with a CVE
  identifier when applicable.

## Threat model

Paxman's threat model is the threat model of a pure function:

- **Inputs that control canonicalization are user-controlled.** A caller
  who passes an untrusted input to `paxman.canonicalize()` is trusting
  the canonicalization pipeline not to do anything beyond rewriting the
  input. The pipeline does not call out to the network, the filesystem,
  subprocesses, or any other side-effecting system. An untrusted input
  cannot cause Paxman to do anything beyond producing an
  `ExecutionArtifact`.
- **Registered capabilities are user-controlled.** A caller who calls
  `paxman.register_capability()` is trusting the capability they
  registered. The capability SPI is narrow on purpose (no
  `execute()`, no `pipeline`, no `stage`), but Paxman does not prevent
  a capability from making network calls or reading files. A
  capability is the caller's responsibility; Paxman enforces purity
  only by convention and by the rule that a capability must depend
  only on inputs that are part of the artifact's `VersionStamp`.
- **Determinism is a security property, not a performance one.** An
  artifact whose `replay_hash` does not match its content indicates
  tampering. The replay check in `paxman.replay()` is the trust
  boundary; treat a failed replay as a security event.

## What Paxman does not protect against

- Vulnerabilities in the runtime dependency `attrs`. Report those
  upstream.
- Vulnerabilities introduced by a custom capability the caller
  registered. Paxman does not sandbox capabilities.
- Denial of service from extremely large inputs. The library does
  not currently enforce input size limits; a caller is expected to
  validate input size at the application boundary.
