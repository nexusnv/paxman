"""``json_path_extraction`` V1 capability — JSON-Pointer / limited JSONPath.

Extracts one or more values from a JSON document using a
JSON-Pointer (RFC 6901) path or a documented subset of JSONPath.
The path is supplied via :attr:`CapabilityContext.config` as the
``"pointer"`` key (a string).

The capability owns JSON parsing and the path resolver. The planner
does not need to know about JSON.

Supported path vocabulary (intentionally narrower than full JSONPath):

- JSON Pointer: ``/foo/bar/0`` (RFC 6901; the primary form).
- JSONPath subset: ``$.foo.bar[0]`` and ``$.foo.*`` for convenience.

Anything outside the supported subset returns a clear diagnostic,
never a silent miss.

V1 surface:

- ``input_types`` = ``("STRING", "HTML_TEXT", "MIXED")``
- ``output_type`` = ``"STRING"``
- ``deterministic`` = ``True``
- ``cost_estimate`` = ``(tokens=0, ms=1, usd=0.0)``
- ``tier`` = ``CapabilityTier.LOCAL_DETERMINISTIC``

Failure modes (each surfaces as a structured :class:`Diagnostic`,
never raises):

- ``CAPABILITY_INVOKE_FAILED`` (ERROR) — ``config["pointer"]`` missing
  / not a non-empty string.
- ``CAPABILITY_INVOKE_FAILED`` (ERROR) — input does not parse as JSON.
- ``CAPABILITY_INVOKE_FAILED`` (ERROR) — pointer syntax is outside
  the supported subset.
- ``PATTERN_NO_MATCH`` (INFO) — pointer resolves to nothing.
- ``CAPABILITY_INVOKE_FAILED`` (ERROR) — resolved value's type
  cannot be coerced to a string ``Candidate``.

Per V1 capability convention (mirroring :mod:`regex_extraction`),
this module does **not** self-register. Callers must register it
explicitly via :func:`paxman.capabilities.registry.register` or
:func:`paxman.register_capability`. The :mod:`paxman.capabilities.v1`
package imports it for type resolution / importability only.

Examples:
    >>> cap = JsonPathExtractionCapability()
    >>> ctx = CapabilityContext(
    ...     raw_input=b'{"supplier": "ACME Corp"}',
    ...     field_path="supplier_name",
    ...     field_type_name="STRING",
    ...     config={"pointer": "/supplier"},
    ... )
    >>> result = cap.invoke(ctx)
    >>> [c.value for c in result.candidates]
    ['ACME Corp']
"""

from __future__ import annotations

import json
import typing

from paxman.capabilities.base import CapabilityContext
from paxman.capabilities.result import (
    Candidate,
    CapabilityResult,
    Diagnostic,
    DiagnosticCode,
    DiagnosticSeverity,
    EvidenceRef,
)
from paxman.capabilities.spec import CapabilitySpec, CapabilityTier, CostHint

__all__ = ["JsonPathExtractionCapability"]


#: Singleton spec for ``json_path_extraction@1.0``. Reused across instances.
_JSON_PATH_EXTRACTION_SPEC: typing.Final[CapabilitySpec] = CapabilitySpec(
    id="json_path_extraction",
    version="1.0",
    input_types=("STRING", "HTML_TEXT", "MIXED"),
    output_type="STRING",
    cost_estimate=CostHint(tokens=0, ms=1, usd=0.0),
    tier=CapabilityTier.LOCAL_DETERMINISTIC,
    deterministic=True,
    required_providers=(),
)


class JsonPathExtractionCapability:
    """V1 ``json_path_extraction`` capability.

    Extracts one or more values from a JSON document using a
    JSON-Pointer or a documented subset of JSONPath. The pointer
    is supplied via :attr:`CapabilityContext.config`
    (``ctx.config["pointer"]``).

    Behavior:

    - If the pointer is a JSON-Pointer (``/foo/bar/0``), the value
      at that path is returned. If the path traverses through an
      array, integer segments index into the list.
    - If the pointer is a supported JSONPath (``$.foo.*``), every
      value at that level is returned (one ``Candidate`` per match,
      in document order).
    - On parse failure, missing path, unsupported syntax, or
      uncoercible resolved value, the capability returns a
      :class:`CapabilityResult` with an empty ``candidates`` list
      and a single :class:`Diagnostic`. It never raises.
    """

    @property
    def spec(self) -> CapabilitySpec:
        """The :class:`CapabilitySpec` for ``json_path_extraction@1.0``."""
        return _JSON_PATH_EXTRACTION_SPEC

    @staticmethod
    def _coerce_to_string(value: object) -> str:
        """Coerce a JSON-decoded value to a string ``Candidate`` value.

        Strings, ints, floats, and bools coerce via ``str()``. ``None``
        becomes the literal ``"null"``. Lists and dicts at the leaf
        raise :class:`TypeError` so the caller can emit a diagnostic.
        """
        if isinstance(value, bool):
            # bool is an int subclass; check before int.
            return "true" if value else "false"
        if isinstance(value, str):
            return value
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float):
            return str(value)
        if value is None:
            return "null"
        msg = f"cannot coerce JSON value of type {type(value).__name__} to string"
        raise TypeError(msg)

    @staticmethod
    def _resolve_json_pointer(
        document: object, pointer: str
    ) -> tuple[object, tuple[str, ...]]:
        """Walk a JSON-Pointer against *document*.

        Returns ``(value, matched_path)`` where ``matched_path`` is a
        tuple of segment labels (with the ``"root"`` prefix) describing
        the location. Raises :class:`KeyError` / :class:`IndexError`
        on a miss so the caller can emit a ``PATTERN_NO_MATCH`` diagnostic.
        """
        if pointer == "/":
            return document, ("root",)
        parts = pointer.split("/")[1:]
        current: object = document
        for raw in parts:
            token = raw.replace("~1", "/").replace("~0", "~")
            if isinstance(current, list):
                current = current[int(token)]
            else:
                current = current[token]  # type: ignore[index]
        return current, ("root", *parts)

    @staticmethod
    def _walk_jsonpath(
        current: object,
        segments: list[str],
        path: tuple[str, ...],
        out: list[tuple[object, tuple[str, ...]]],
    ) -> None:
        """Recursively expand a supported JSONPath against *current*."""
        if not segments:
            out.append((current, path))
            return
        head, *tail = segments
        if head in ("*", "[*]"):
            if isinstance(current, list):
                for i, item in enumerate(current):
                    JsonPathExtractionCapability._walk_jsonpath(
                        item, tail, (*path, f"[{i}]"), out
                    )
            elif isinstance(current, dict):
                for k, v in current.items():
                    JsonPathExtractionCapability._walk_jsonpath(
                        v, tail, (*path, k), out
                    )
            else:
                msg = f"cannot expand '*' on non-container at {path}"
                raise ValueError(msg)
        elif "[" in head and head.endswith("]"):
            key, idx = head[:-1].split("[", 1)
            if isinstance(current, dict):
                container: object = current[key]
            elif isinstance(current, list):
                container = current[int(key)]
            else:
                msg = f"cannot index non-container at {path}"
                raise ValueError(msg)
            if not isinstance(container, list):
                msg = f"expected list at {key!r}, got {type(container).__name__}"
                raise ValueError(msg)
            value = container[int(idx)]
            JsonPathExtractionCapability._walk_jsonpath(
                value, tail, (*path, f"{key}[{idx}]"), out
            )
        else:
            if isinstance(current, dict):
                value = current[head]
            elif isinstance(current, list):
                value = current[int(head)]
            else:
                msg = f"cannot index non-container at {path}"
                raise ValueError(msg)
            JsonPathExtractionCapability._walk_jsonpath(
                value, tail, (*path, head), out
            )

    @classmethod
    def _resolve_jsonpath(
        cls, document: object, pointer: str
    ) -> list[tuple[object, tuple[str, ...]]]:
        """Resolve a documented JSONPath subset. Raises ``ValueError`` on unsupported syntax."""
        if not pointer.startswith("$"):
            msg = f"JSONPath must start with '$', got {pointer!r}"
            raise ValueError(msg)
        rest = pointer[1:]
        if rest == "":
            return [(document, ("root",))]
        if not rest.startswith("."):
            msg = f"unsupported JSONPath syntax: {pointer!r}"
            raise ValueError(msg)
        # ``$.foo.bar`` → ["foo", "bar"]; drop any empty strings.
        segments = [s for s in rest.split(".") if s]
        out: list[tuple[object, tuple[str, ...]]] = []
        cls._walk_jsonpath(document, segments, ("root",), out)
        return out

    @classmethod
    def _resolve_pointer(
        cls, document: object, pointer: str
    ) -> list[tuple[object, tuple[str, ...]]]:
        """Resolve a JSON-Pointer or supported JSONPath against *document*.

        Returns a list of ``(value, path)`` pairs — one per match. For a
        JSON-Pointer, the list has exactly one element.

        Raises:
            ValueError: If the pointer syntax is outside the supported
                subset (caller emits a diagnostic).
        """
        if not isinstance(pointer, str) or not pointer:
            msg = "pointer must be a non-empty string"
            raise ValueError(msg)
        if pointer.startswith("$"):
            return cls._resolve_jsonpath(document, pointer)
        if pointer.startswith("/"):
            value, path = cls._resolve_json_pointer(document, pointer)
            return [(value, path)]
        msg = (
            f"unsupported pointer syntax: {pointer!r} "
            "(must start with '/' for JSON-Pointer or '$' for JSONPath)"
        )
        raise ValueError(msg)

    def invoke(self, ctx: CapabilityContext) -> CapabilityResult:
        """Parse the input as JSON and resolve the pointer.

        Args:
            ctx: The :class:`CapabilityContext`. ``ctx.config["pointer"]``
                must be a non-empty string.

        Returns:
            A :class:`CapabilityResult` with one :class:`Candidate` per
            match (or empty if no match). On every failure mode the
            capability returns an empty ``candidates`` list and a single
            structured :class:`Diagnostic`; it never raises.
        """
        pointer = ctx.config.get("pointer")
        if not isinstance(pointer, str) or not pointer:
            return CapabilityResult(
                candidates=(),
                diagnostics=(
                    Diagnostic(
                        code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                        severity=DiagnosticSeverity.ERROR,
                        message=(
                            "json_path_extraction: config['pointer'] must be a non-empty string"
                        ),
                        context={"field_path": ctx.field_path},
                    ),
                ),
            )

        if not ctx.raw_input:
            return CapabilityResult(
                candidates=(),
                diagnostics=(
                    Diagnostic(
                        code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                        severity=DiagnosticSeverity.ERROR,
                        message="json_path_extraction: raw_input is empty",
                        context={"field_path": ctx.field_path, "pointer": pointer},
                    ),
                ),
            )

        text = ctx.raw_input.decode("utf-8", errors="replace")
        try:
            document = json.loads(text)
        except json.JSONDecodeError as exc:
            return CapabilityResult(
                candidates=(),
                diagnostics=(
                    Diagnostic(
                        code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                        severity=DiagnosticSeverity.ERROR,
                        message=f"json_path_extraction: input is not valid JSON: {exc.msg}",
                        context={
                            "field_path": ctx.field_path,
                            "pointer": pointer,
                            "line": exc.lineno,
                            "column": exc.colno,
                        },
                    ),
                ),
            )

        try:
            matches = self._resolve_pointer(document, pointer)
        except (KeyError, IndexError) as exc:
            return CapabilityResult(
                candidates=(),
                diagnostics=(
                    Diagnostic(
                        code=DiagnosticCode.PATTERN_NO_MATCH,
                        severity=DiagnosticSeverity.INFO,
                        message=f"json_path_extraction: pointer did not match: {exc}",
                        context={"field_path": ctx.field_path, "pointer": pointer},
                    ),
                ),
            )
        except ValueError as exc:
            return CapabilityResult(
                candidates=(),
                diagnostics=(
                    Diagnostic(
                        code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                        severity=DiagnosticSeverity.ERROR,
                        message=f"json_path_extraction: unsupported pointer syntax: {exc}",
                        context={"field_path": ctx.field_path, "pointer": pointer},
                    ),
                ),
            )

        candidates: list[Candidate] = []
        evidence: list[EvidenceRef] = []
        for value, matched_path in matches:
            try:
                coerced = self._coerce_to_string(value)
            except TypeError as exc:
                return CapabilityResult(
                    candidates=(),
                    diagnostics=(
                        Diagnostic(
                            code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                            severity=DiagnosticSeverity.ERROR,
                            message=(
                                f"json_path_extraction: cannot coerce resolved value to string: {exc}"
                            ),
                            context={
                                "field_path": ctx.field_path,
                                "pointer": pointer,
                                "value_type": type(value).__name__,
                            },
                        ),
                    ),
                )
            ev = EvidenceRef(
                capability_id="json_path_extraction",
                capability_version="1.0",
                field_path=ctx.field_path,
                context={
                    "json_pointer": pointer,
                    "matched_path": list(matched_path),
                    "value_type": type(value).__name__,
                },
            )
            evidence.append(ev)
            candidates.append(Candidate(value=coerced, evidence_refs=(ev,)))

        if not candidates:
            return CapabilityResult(
                candidates=(),
                evidence=(),
                diagnostics=(
                    Diagnostic(
                        code=DiagnosticCode.PATTERN_NO_MATCH,
                        severity=DiagnosticSeverity.INFO,
                        message="json_path_extraction: pointer resolved to no values",
                        context={"field_path": ctx.field_path, "pointer": pointer},
                    ),
                ),
            )

        return CapabilityResult(
            candidates=tuple(candidates),
            evidence=tuple(evidence),
        )
