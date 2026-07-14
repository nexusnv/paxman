"""Grep-zero gate for 'Capability' outside the Extending Paxman section.

Spec §4.6 + issue criterion 6: the word 'Capability' (case-sensitive)
appears in README.md ONLY within the '## Extending Paxman' section. This
makes criterion 6 a hard CI gate.
"""

from __future__ import annotations

import pathlib


def test_capability_appears_only_in_extending_section() -> None:
    readme = pathlib.Path("README.md").read_text(encoding="utf-8")
    marker = "## Extending Paxman"
    extending_start = readme.find(marker)
    assert extending_start != -1, "README.md has no '## Extending Paxman' section"

    before = readme[:extending_start]
    after = readme[extending_start:]

    # Case-sensitive substring 'Capability' must NOT appear before the
    # Extending Paxman section.
    assert "Capability" not in before, (
        "the word 'Capability' appears in README.md outside the "
        "'## Extending Paxman' section; this violates criterion 6. "
        f"Offending prefix:\n{before[-200:]}"
    )

    # Case-sensitive substring 'Capability' MUST appear inside the
    # Extending Paxman section (otherwise the SPI doc is missing).
    assert "Capability" in after, (
        "the word 'Capability' does not appear inside '## Extending "
        "Paxman'; the SPI documentation is missing."
    )
