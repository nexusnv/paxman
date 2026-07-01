"""``csv_extraction`` V1 capability — column-based CSV extraction.

Extracts one :class:`Candidate` per row of a CSV document for a named
column (or column index). The column spec is supplied via
:attr:`CapabilityContext.config` as the ``"column"`` key (a string
for a column name, or a non-negative int for a column index).

The capability owns CSV parsing and column resolution. The planner
does not need to know about CSV.

The parser uses :mod:`csv` with :class:`csv.Sniffer` autodetection of
delimiter and quoting, falling back to a comma / double-quote default.
The first row is treated as a header for column-name resolution;
column-index resolution skips that distinction.

V1 surface:

- ``input_types`` = ``("STRING", "HTML_TEXT", "MIXED")``
- ``output_type`` = ``"STRING"``
- ``deterministic`` = ``True``
- ``cost_estimate`` = ``(tokens=0, ms=1, usd=0.0)``
- ``tier`` = ``CapabilityTier.LOCAL_DETERMINISTIC``

Failure modes (each surfaces as a structured :class:`Diagnostic`):

- ``CAPABILITY_INVOKE_FAILED`` (ERROR) — ``config["column"]`` missing
  or wrong type.
- ``CAPABILITY_INVOKE_FAILED`` (ERROR) — input is not parseable as CSV.
- ``CAPABILITY_INVOKE_FAILED`` (ERROR) — column name is not in the
  header, or column index is out of range.
- ``PATTERN_NO_MATCH`` (INFO) — column exists but every row is empty.
  (Per-row empty cells are silently skipped to keep the result set
  honest.)

Per V1 capability convention (mirroring :mod:`regex_extraction`),
this module does **not** self-register. Callers must register it
explicitly via :func:`paxman.capabilities.registry.register` or
:func:`paxman.register_capability`. The :mod:`paxman.capabilities.v1`
package imports it for type resolution / importability only.

Examples:
    >>> cap = CsvExtractionCapability()
    >>> ctx = CapabilityContext(
    ...     raw_input=b"supplier,amount\\nACME,100\\nFoo,200\\n",
    ...     field_path="supplier_name",
    ...     field_type_name="STRING",
    ...     config={"column": "supplier"},
    ... )
    >>> result = cap.invoke(ctx)
    >>> [c.value for c in result.candidates]
    ['ACME', 'Foo']
"""

from __future__ import annotations

import csv
import io
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

__all__ = ["CsvExtractionCapability"]


#: Singleton spec for ``csv_extraction@1.0``. Reused across instances.
_CSV_EXTRACTION_SPEC: typing.Final[CapabilitySpec] = CapabilitySpec(
    id="csv_extraction",
    version="1.0",
    input_types=("STRING", "HTML_TEXT", "MIXED"),
    output_type="STRING",
    cost_estimate=CostHint(tokens=0, ms=1, usd=0.0),
    tier=CapabilityTier.LOCAL_DETERMINISTIC,
    deterministic=True,
    required_providers=(),
)


class CsvExtractionCapability:
    """V1 ``csv_extraction`` capability.

    Extracts one value per non-empty row from a CSV document for a
    named column (string) or column index (non-negative int).

    Behavior:

    - ``config["column"]`` is the column spec (str or int).
    - The first row of the input is treated as the header for
      column-name resolution. Column-index resolution uses the
      first row only to determine the number of columns.
    - One :class:`Candidate` is emitted per row whose named column
      is non-empty. Per-row empty cells are silently skipped.
    - On any failure mode the capability returns a
      :class:`CapabilityResult` with an empty ``candidates`` list
      and a single structured :class:`Diagnostic`; it never raises.
    """

    @property
    def spec(self) -> CapabilitySpec:
        """The :class:`CapabilitySpec` for ``csv_extraction@1.0``."""
        return _CSV_EXTRACTION_SPEC

    # --- Result builders --------------------------------------------------
    #
    # The capability's failure modes all produce a CapabilityResult
    # with no candidates, exactly one Diagnostic, and a context that
    # includes ``field_path``. These two helpers keep the call sites
    # short and consistent.

    @staticmethod
    def _failed(message: str, field_path: str, **ctx: object) -> CapabilityResult:
        """Build a ``CAPABILITY_INVOKE_FAILED`` result with one Diagnostic."""
        return CapabilityResult(
            candidates=(),
            diagnostics=(
                Diagnostic(
                    code=DiagnosticCode.CAPABILITY_INVOKE_FAILED,
                    severity=DiagnosticSeverity.ERROR,
                    message=f"csv_extraction: {message}",
                    context={"field_path": field_path, **ctx},
                ),
            ),
        )

    @staticmethod
    def _no_match(message: str, field_path: str, **ctx: object) -> CapabilityResult:
        """Build a ``PATTERN_NO_MATCH`` result with one Diagnostic.

        The ``candidates`` and ``evidence`` tuples are both empty
        (no matches; nothing to attach evidence to).
        """
        return CapabilityResult(
            candidates=(),
            evidence=(),
            diagnostics=(
                Diagnostic(
                    code=DiagnosticCode.PATTERN_NO_MATCH,
                    severity=DiagnosticSeverity.INFO,
                    message=f"csv_extraction: {message}",
                    context={"field_path": field_path, **ctx},
                ),
            ),
        )

    # --- Column validation ------------------------------------------------

    @staticmethod
    def _validate_column(
        column: object, field_path: str
    ) -> tuple[str | int | None, CapabilityResult | None]:
        """Validate ``config['column']`` and return ``(resolved, error_result)``.

        ``resolved`` is the column as a string (name) or non-negative
        int (index). ``error_result`` is non-None if validation failed.
        """
        # Reject bool explicitly: ``isinstance(True, int)`` is True.
        if isinstance(column, bool):
            return None, CsvExtractionCapability._failed(
                "config['column'] must be a non-empty str or a non-negative int, got bool",
                field_path,
            )
        if isinstance(column, str):
            if not column:
                return None, CsvExtractionCapability._failed(
                    "config['column'] is an empty string", field_path
                )
            return column, None
        if isinstance(column, int):
            if column < 0:
                return None, CsvExtractionCapability._failed(
                    f"config['column'] must be non-negative, got {column}",
                    field_path,
                    column=column,
                )
            return column, None
        return None, CsvExtractionCapability._failed(
            "config['column'] must be a non-empty str "
            f"or a non-negative int, got {type(column).__name__}",
            field_path,
        )

    # --- Parsing ----------------------------------------------------------

    @staticmethod
    def _parse_csv(raw: bytes) -> list[list[str]] | CapabilityResult:
        """Parse *raw* as CSV, sniffing the dialect. Returns rows on success.

        A leading UTF-8 BOM (``\\xef\\xbb\\xbf``) is stripped before parsing so
        that BOM-prefixed CSVs (common from Excel-on-Windows exports)
        do not leak into the first column header.
        """
        text = raw.decode("utf-8-sig", errors="replace")
        try:
            sample = text[:4096]
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
            except csv.Error:
                dialect = csv.excel
            reader = csv.reader(io.StringIO(text), dialect=dialect)
            return list(reader)
        except csv.Error as exc:
            return CsvExtractionCapability._failed(
                f"input is not valid CSV: {exc}",
                "<resolved-by-caller>",
            )

    # --- Main entry point -------------------------------------------------

    def invoke(self, ctx: CapabilityContext) -> CapabilityResult:
        """Parse the input as CSV and emit one candidate per row.

        Args:
            ctx: The :class:`CapabilityContext`. ``ctx.config["column"]``
                must be a non-empty string (column name) or a
                non-negative int (column index).

        Returns:
            A :class:`CapabilityResult` with one :class:`Candidate` per
            non-empty row cell, in row order.
        """
        column_obj = ctx.config.get("column")
        column, err = self._validate_column(column_obj, ctx.field_path)
        if err is not None:
            return err

        if not ctx.raw_input:
            return self._failed("raw_input is empty", ctx.field_path)

        parsed = self._parse_csv(ctx.raw_input)
        if isinstance(parsed, CapabilityResult):
            # Parse-time error doesn't yet know field_path; rebuild the
            # diagnostic with the correct field_path.
            old = parsed.diagnostics[0]
            return self._failed(old.message.removeprefix("csv_extraction: "), ctx.field_path)

        rows = parsed
        if not rows:
            return self._failed("input has no rows", ctx.field_path)

        header = rows[0]
        if isinstance(column, int):
            if column >= len(header):
                return self._failed(
                    f"column index {column} out of range (header has {len(header)} columns)",
                    ctx.field_path,
                    column_index=column,
                    header_width=len(header),
                )
            resolved_name: str = header[column]
            col_index: int = column
        elif column not in header:
            return self._failed(
                f"column {column!r} not found in header",
                ctx.field_path,
                column_name=column,
                header=list(header),
            )
        else:
            resolved_name = column
            col_index = header.index(column)

        # Emit one candidate per non-empty cell in the data rows.
        candidates: list[Candidate] = []
        evidence: list[EvidenceRef] = []
        for row_index, row in enumerate(rows[1:], start=1):
            if col_index >= len(row):
                # Short row — treat as empty cell, skip silently.
                continue
            cell = row[col_index]
            if not cell:
                continue
            ev = EvidenceRef(
                capability_id="csv_extraction",
                capability_version="1.0",
                field_path=ctx.field_path,
                context={
                    "csv_column": resolved_name,
                    "row_index": row_index,
                    "header": list(header),
                },
            )
            evidence.append(ev)
            candidates.append(Candidate(value=cell, evidence_refs=(ev,)))

        if not candidates:
            return self._no_match(
                f"column {resolved_name!r} has no non-empty values",
                ctx.field_path,
                csv_column=resolved_name,
                rows_scanned=len(rows) - 1,
            )

        return CapabilityResult(
            candidates=tuple(candidates),
            evidence=tuple(evidence),
        )
