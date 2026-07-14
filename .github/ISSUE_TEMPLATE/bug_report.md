---
name: Bug report
about: Report a bug in Paxman
title: '[bug] '
labels: bug, needs-triage
assignees: ''
---

## Summary

<!-- One-paragraph description of the bug. -->

## Paxman version

<!-- Run `uv run python -c "import paxman; print(paxman.__version__)"` and paste the output. -->

`paxman == <version>`

## Python version

<!-- Run `python --version` and paste the output. -->

`Python <version>`

## Operating system

<!-- macOS, Linux (Ubuntu 22.04), Windows 11, … -->

## Minimal reproducer

```python
# Smallest possible code that triggers the bug.
import paxman

# ...
```

## Expected behavior

<!-- What you expected to happen. -->

## Actual behavior

<!-- What actually happened. Include the full traceback if any. -->

## Additional context

<!-- Links to relevant docs, the source file, or related code paths. -->

- `paxman/` source file: `src/paxman/_<module>/<file>.py`
- Relevant doc page: `docs/<section>/<page>.md`

## Checklist

- [ ] I have searched the existing issues and found no duplicate.
- [ ] I have read [`CONTRIBUTING.md`](../../CONTRIBUTING.md) and
      [`SECURITY.md`](../../SECURITY.md).
- [ ] I have included the Paxman version, the Python version, and the
      operating system.
- [ ] I have included a minimal reproducer.
- [ ] I have included the actual behavior (with traceback if any).
- [ ] This is **not** a security vulnerability (security reports go
      to the address in `SECURITY.md`, **not** a public issue).
