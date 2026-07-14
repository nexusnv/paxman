---
name: Feature request
about: Suggest a feature for Paxman
title: '[feature] '
labels: enhancement, needs-triage
assignees: ''
---

## Summary

<!-- One-paragraph description of the feature. -->

## Motivation

<!-- Why is this feature needed? What problem does it solve? -->

## Proposed API

<!-- A sketch of the proposed API or usage pattern. -->

```python
# Sketch of the proposed API.
import paxman

# ...
```

## Alternatives considered

<!-- What other approaches did you consider? Why is this one better? -->

## Is this within Paxman's identity?

<!-- Paxman is a deterministic canonicalization engine. Features that
     turn it into a normalizer, a parser framework, a workflow engine,
     or an AI extraction system are outside its identity boundary. -->

- [ ] This adds a new built-in capability (e.g. a new canonical type)
- [ ] This adds a new contract kind
- [ ] This adds a new public symbol to `paxman.__all__`
- [ ] This changes artifact immutability or the `VersionStamp` shape
- [ ] This changes the `Capability` protocol (the SPI)
- [ ] This changes the five `Status` outcomes
- [ ] None of the above — this is a small enhancement

If any of the above is checked, the change requires a brief
explanation of how it preserves the three invariants (identity,
determinism, replay) and the artifact immutability rule.

## Additional context

<!-- Links to relevant docs, the source file, or related code paths. -->

- Relevant doc page: `docs/<section>/<page>.md`
- Related source file: `src/paxman/_<module>/<file>.py`

## Checklist

- [ ] I have searched the existing issues and found no duplicate.
- [ ] I have read [`CONTRIBUTING.md`](../../CONTRIBUTING.md).
- [ ] I have included a sketch of the proposed API.
- [ ] I have identified whether the change is within Paxman's identity
      boundary.
