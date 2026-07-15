"""Deterministic mapping from (capability result, validation) to Status.

Mandate Law 8 + §1.3: status values are outcomes, not exceptions. The
classifier is a pure function. It never raises on a well-typed input.
"""

from __future__ import annotations

import attrs

from paxman._core.result import CapabilityResult
from paxman._core.status import Status


@attrs.frozen
class ValidationResult:
    """The verdict of the post-capability validation step."""

    is_valid: bool


def classify(capability_result: CapabilityResult, validation: ValidationResult) -> Status:
    """Map a (capability result, validation) pair onto a Status.

    The only case where the capability's status is overridden is when the
    capability said CANONICALIZED but the post-validation step rejected
    the value. Every other capability status is preserved as-is.
    """
    if capability_result.status is Status.CANONICALIZED and not validation.is_valid:
        return Status.INVALID
    return capability_result.status
