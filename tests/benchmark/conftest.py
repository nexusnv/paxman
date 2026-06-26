"""Benchmark fixtures for ``paxman.normalize()`` — Sprint 9 D9.1.

Provides:

- A 20-field Dict DSL contract mixing STRING, INTEGER, DECIMAL,
  BOOLEAN, DATE, ENUM, MONEY, and ARRAY types.
- A ~100 KB synthetic text input representing a large procurement
  document.
- A ``Policy`` with ``allow_remote_inference=False`` to keep
  benchmarks deterministic and network-free.
"""

from __future__ import annotations

import pytest

import paxman.contract.adapters.dict_dsl  # noqa: F401 — triggers adapter self-registration
from paxman.budget import Policy

# ---------------------------------------------------------------------------
# 20-field Dict DSL contract
# ---------------------------------------------------------------------------

BENCHMARK_CONTRACT_20_FIELDS: dict[str, object] = {
    "id": "benchmark-procurement-v1",
    "version": "1",
    "fields": [
        # --- STRING (5 fields) ---
        {
            "name": "supplier_name",
            "type": "STRING",
            "required": True,
            "description": "Legal name of the supplier.",
            "tags": ["pii"],
            "constraints": [
                {"kind": "min_length", "params": {"min": 1}},
                {"kind": "max_length", "params": {"max": 500}},
            ],
        },
        {
            "name": "invoice_number",
            "type": "STRING",
            "required": True,
            "description": "Unique invoice identifier.",
            "constraints": [
                {"kind": "min_length", "params": {"min": 1}},
                {"kind": "max_length", "params": {"max": 100}},
            ],
        },
        {
            "name": "purchase_order",
            "type": "STRING",
            "required": True,
            "description": "Purchase order reference.",
        },
        {
            "name": "billing_address",
            "type": "STRING",
            "required": True,
            "description": "Billing address.",
        },
        {
            "name": "payment_terms",
            "type": "STRING",
            "required": False,
            "description": "Payment terms (e.g. Net 30, Net 60).",
        },
        # --- INTEGER (3 fields) ---
        {
            "name": "line_item_count",
            "type": "INTEGER",
            "required": True,
            "description": "Number of line items.",
            "constraints": [
                {"kind": "min_value", "params": {"min": 1}},
            ],
        },
        {
            "name": "po_revision",
            "type": "INTEGER",
            "required": False,
            "description": "Purchase order revision number.",
        },
        {
            "name": "approval_code",
            "type": "INTEGER",
            "required": False,
            "description": "Numeric approval code.",
        },
        # --- DECIMAL (3 fields) ---
        {
            "name": "subtotal",
            "type": "DECIMAL",
            "required": True,
            "description": "Subtotal before tax.",
            "constraints": [
                {"kind": "min_value", "params": {"min": 0}},
            ],
        },
        {
            "name": "tax_rate",
            "type": "DECIMAL",
            "required": False,
            "description": "Tax rate as a decimal (e.g. 0.0825).",
        },
        {
            "name": "discount_pct",
            "type": "DECIMAL",
            "required": False,
            "description": "Discount percentage.",
        },
        # --- BOOLEAN (2 fields) ---
        {
            "name": "paid",
            "type": "BOOLEAN",
            "required": False,
            "default": False,
            "description": "Whether the invoice has been paid.",
        },
        {
            "name": "approved",
            "type": "BOOLEAN",
            "required": False,
            "default": False,
            "description": "Whether the invoice has been approved.",
        },
        # --- DATE (3 fields) ---
        {
            "name": "invoice_date",
            "type": "DATE",
            "required": True,
            "description": "Date the invoice was issued.",
        },
        {
            "name": "due_date",
            "type": "DATE",
            "required": True,
            "description": "Payment due date.",
        },
        {
            "name": "delivery_date",
            "type": "DATE",
            "required": False,
            "description": "Date goods were delivered.",
        },
        # --- ENUM (2 fields) ---
        {
            "name": "currency_code",
            "type": "ENUM",
            "required": True,
            "description": "ISO-4217 currency code.",
            "tags": ["currency-sensitive"],
            "constraints": [
                {
                    "kind": "enum",
                    "params": {
                        "values": ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD"],
                    },
                },
                {"kind": "iso_4217", "params": {}},
            ],
        },
        {
            "name": "priority",
            "type": "ENUM",
            "required": False,
            "description": "Invoice processing priority.",
            "constraints": [
                {
                    "kind": "enum",
                    "params": {"values": ["low", "medium", "high", "urgent"]},
                },
            ],
        },
        # --- MONEY (1 field) ---
        {
            "name": "total_amount",
            "type": "MONEY",
            "required": True,
            "description": "Total invoice amount.",
            "tags": ["currency-sensitive", "high-stakes"],
            "constraints": [
                {"kind": "min_value", "params": {"min": 0}},
            ],
        },
        # --- ARRAY (1 field) ---
        {
            "name": "line_items",
            "type": "ARRAY",
            "required": False,
            "default": [],
            "description": "Individual line items on the invoice.",
        },
    ],
    "policy": {
        "confidence_floor": 0.80,
        "unresolved_acceptable": True,
    },
}


def _build_large_input(target_bytes: int = 100_000) -> str:
    """Build a ~target_bytes synthetic procurement text.

    Strategy: compose a realistic procurement document with many
    line items, repeated sections, and structured metadata until the
    output reaches the target size.
    """
    base_section = (
        "==========================================================\n"
        " PROCUREMENT INVOICE\n"
        "==========================================================\n"
        "\n"
        "Supplier: Acme Industrial Solutions LLC\n"
        "Address: 1200 Commerce Boulevard, Suite 400\n"
        "         Springfield, IL 62704, United States\n"
        "Phone: +1 (555) 867-5309  |  Fax: +1 (555) 867-5310\n"
        "Email: accounts@acme-industrial.example.com\n"
        "Tax ID: 36-1234567\n"
        "\n"
        "Invoice Number: INV-2026-001234\n"
        "Purchase Order: PO-98765-REV3\n"
        "Invoice Date: 2026-01-15\n"
        "Due Date: 2026-02-15\n"
        "Delivery Date: 2026-01-10\n"
        "Payment Terms: Net 30\n"
        "Currency: USD\n"
        "Priority: high\n"
        "\n"
        "Bill To:\n"
        "  Globex Industries International\n"
        "  456 Commerce Blvd, Floor 12\n"
        "  Chicago, IL 60601, United States\n"
        "  Attn: Accounts Payable Department\n"
        "\n"
        "Ship To:\n"
        "  Globex Warehouse North\n"
        "  789 Distribution Drive\n"
        "  Naperville, IL 60563, United States\n"
        "\n"
        "----------------------------------------------------------\n"
        " LINE ITEMS\n"
        "----------------------------------------------------------\n"
        "Item  Description                    Qty    Unit Price    Extended\n"
        "----  ----------------------------   ---    ----------    --------\n"
        " 1    Industrial Widget Pro X100      100      $50.00    $5,000.00\n"
        " 2    Heavy-Duty Gadget Plus G200      50      $30.00    $1,500.00\n"
        " 3    Precision Bearing Set BS-42      200      $12.50    $2,500.00\n"
        " 4    Hydraulic Cylinder HC-500        10     $450.00    $4,500.00\n"
        " 5    Control Valve Assembly CV-3      25     $180.00    $4,500.00\n"
        " 6    Stainless Steel Pipe 4in         50      $85.00    $4,250.00\n"
        " 7    Electrical Conduit Fitting       300       $3.50    $1,050.00\n"
        " 8    Safety Valve SV-200               15     $320.00    $4,800.00\n"
        " 9    Pressure Gauge PG-100             40      $65.00    $2,600.00\n"
        "10    Thermal Insulation Wrap          100      $22.00    $2,200.00\n"
        "11    Copper Wire 10AWG (ft)          1000       $0.85      $850.00\n"
        "12    Junction Box NEMA 4X              20      $95.00    $1,900.00\n"
        "13    LED Panel Light 2x4               30     $120.00    $3,600.00\n"
        "14    Air Filter HEPA H13               25     $200.00    $5,000.00\n"
        "15    Lubricant Synthetic 5L            40      $45.00    $1,800.00\n"
        "\n"
        "Subtotal:                                  $42,050.00\n"
        "Tax (8.25%):                                $3,469.13\n"
        "Discount (2%):                                -$841.00\n"
        "==========================================================\n"
        " TOTAL DUE:                               $44,678.13 USD\n"
        "==========================================================\n"
        "\n"
        "Notes:\n"
        "- All items shipped FOB destination.\n"
        "- Returns accepted within 30 days with RMA number.\n"
        "- Late payments subject to 1.5% monthly interest.\n"
        "- Please reference PO number on all remittances.\n"
        "\n"
        "Authorized by: J. Smith, Procurement Manager\n"
        "Approval Code: 20260115-001\n"
        "Approved: Yes\n"
        "Paid: No\n"
        "\n"
    )

    # Build up the text by repeating the base section with variations
    # until we reach the target size.
    parts: list[str] = []
    total_bytes = 0
    section_idx = 0
    while total_bytes < target_bytes:
        # Vary the section header slightly to avoid overly compressible text.
        header = f"{'=' * 58}\n SECTION {section_idx + 1:04d} — PROCUREMENT RECORD\n{'=' * 58}\n\n"
        parts.append(header)
        parts.append(base_section)
        section_idx += 1
        total_bytes = sum(len(p.encode("utf-8")) for p in parts)

    return "".join(parts)


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def benchmark_contract_20_fields() -> dict[str, object]:
    """A 20-field Dict DSL contract covering all V1 types except OBJECT."""
    return BENCHMARK_CONTRACT_20_FIELDS


@pytest.fixture(scope="session")
def benchmark_input_100kb() -> str:
    """A ~100 KB synthetic procurement text input."""
    text = _build_large_input(target_bytes=100_000)
    # Sanity check: at least 90 KB, at most 200 KB.
    size = len(text.encode("utf-8"))
    assert size >= 90_000, f"Input too small: {size:,} bytes"
    assert size <= 200_000, f"Input too large: {size:,} bytes"
    return text


@pytest.fixture(scope="session")
def benchmark_input_small() -> str:
    """A small ~300-byte invoice input for baseline comparison."""
    return (
        "ACME Corp\n"
        "Invoice #INV-2026-12345\n"
        "PO: PO-9876\n"
        "Date: 2026-01-15\n"
        "Due: 2026-02-15\n"
        "Bill To: Globex Industries\n"
        "Items:\n"
        "  1. Widget Pro       10 x $50.00  = $500.00\n"
        "  2. Gadget Plus       5 x $30.00  = $150.00\n"
        "  3. Service Fee       1 x $100.00 = $100.00\n"
        "Subtotal: $750.00\n"
        "Tax (8.25%): $61.88\n"
        "Total: $811.88 USD\n"
        "Payment Terms: Net 30\n"
        "Paid: No\n"
        "Approved: Yes\n"
    )


@pytest.fixture(scope="session")
def benchmark_policy() -> Policy:
    """Policy with remote inference disabled for deterministic benchmarks."""
    return Policy(
        allow_remote_inference=False,
        allow_local_inference=True,
    )
