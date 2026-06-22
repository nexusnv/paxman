#!/usr/bin/env python3
"""fetch_test_data.py — Vendor the V1 test data corpus for Paxman.

This script is the single entry point for downloading, verifying, and
updating the vendored test data under `tests/fixtures/`.

See docs/TEST_DATA.md for the full test data policy and the dataset catalog.

Usage:
    python scripts/fetch_test_data.py                          # vendor everything
    python scripts/fetch_test_data.py --dataset cord           # vendor one dataset
    python scripts/fetch_test_data.py --update                 # update all
    python scripts/fetch_test_data.py --list                   # list datasets
    python scripts/fetch_test_data.py --verify                 # verify integrity (CI)
    python scripts/fetch_test_data.py --validate-licenses      # validate license catalog (CI)
    python scripts/fetch_test_data.py --dev-only sroie         # download research-only (dev only)

The script NEVER downloads non-allowed-license datasets unless --dev-only
is passed. It refuses to vendor anything that is not in the catalog.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"
LICENSES_FILE = FIXTURES_DIR / "DATASET_LICENSES.md"
LOG_FILE = FIXTURES_DIR / "DOWNLOAD_LOG.md"


ALLOWED_LICENSES = {
    "MIT",
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "CC0",
    "CC-BY-3.0",
    "CC-BY-4.0",
}


DEV_ONLY_LICENSES = {
    "CC-BY-NC-3.0",
    "CC-BY-NC-4.0",
    "CC-BY-NC-SA-4.0",
    "research-only",
    "Research",
    "Research-only",
    "(research)",
}

logger = logging.getLogger("fetch_test_data")


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    source_url: str
    license: str
    v1_use: str
    target_subdir: Path
    file_count: int
    needs_hf_token: bool = False
    needs_manual_download: bool = False
    notes: str = ""


DATASETS: dict[str, DatasetSpec] = {
    "cord": DatasetSpec(
        name="CORD (Consolidated Receipt Dataset)",
        source_url="https://huggingface.co/datasets/naver-clova-ix/cord-v1",
        license="CC-BY-4.0",
        v1_use="Receipt-parsing end-to-end tests, OCR noise tests",
        target_subdir=Path("inputs/invoices/cord"),
        file_count=100,
        needs_hf_token=False,
    ),
    "invoicebench": DatasetSpec(
        name="jngb-labs/InvoiceBenchmark",
        source_url="https://huggingface.co/datasets/jngb-labs/InvoiceBenchmark",
        license="MIT",
        v1_use="MONEY tests, multi-currency tests, deterministic ground truth",
        target_subdir=Path("inputs/invoices/invoicebench"),
        file_count=200,
        needs_hf_token=False,
    ),
    "alamgirqazi": DatasetSpec(
        name="alamgirqazi/invoice-ocr-synthetic",
        source_url="https://huggingface.co/datasets/alamgirqazi/invoice-ocr-synthetic",
        license="Apache-2.0",
        v1_use="Broad coverage of field labels, line items, multiple currencies",
        target_subdir=Path("inputs/invoices/alamgirqazi"),
        file_count=500,
        needs_hf_token=False,
    ),
    "wildreceipt": DatasetSpec(
        name="kaydee/wildreceipt",
        source_url="https://huggingface.co/datasets/kaydee/wildreceipt",
        license="Apache-2.0",
        v1_use="In-the-wild receipt tests, harder-than-CORD layout tests",
        target_subdir=Path("inputs/receipts/wildreceipt"),
        file_count=200,
        needs_hf_token=False,
    ),
    "oqo": DatasetSpec(
        name="OQO (Open-Quote Object)",
        source_url="https://github.com/APH123614/oqo",
        license="CC-BY-4.0",
        v1_use="Quotation use case, Open-Quote-Object JSON Schema validation",
        target_subdir=Path("inputs/quotations/oqo"),
        file_count=72,
        needs_hf_token=False,
    ),
    "petstore_3_0": DatasetSpec(
        name="OpenAPI Petstore (v3.0)",
        source_url="https://raw.githubusercontent.com/OAI/OpenAPI-Specification/main/examples/v3.0/petstore.yaml",
        license="MIT",
        v1_use="OpenAPI adapter smoke test",
        target_subdir=Path("contracts/openapi"),
        file_count=1,
        needs_hf_token=False,
    ),
    "petstore_3_1": DatasetSpec(
        name="OpenAPI Petstore (v3.1)",
        source_url="https://raw.githubusercontent.com/swagger-api/swagger-petstore/master/src/main/resources/openapi.yaml",
        license="MIT",
        v1_use="OpenAPI 3.1 adapter smoke test, $ref and oneOf exercise",
        target_subdir=Path("contracts/openapi"),
        file_count=1,
        needs_hf_token=False,
    ),
    "json_schema_test_suite": DatasetSpec(
        name="JSON-Schema-Test-Suite",
        source_url="https://github.com/json-schema-org/JSON-Schema-Test-Suite",
        license="BSD-3-Clause",
        v1_use="JSON Schema adapter validation, every draft",
        target_subdir=Path("contracts/json_schema/drafts"),
        file_count=200,
        needs_hf_token=False,
    ),
    "ted_sample": DatasetSpec(
        name="TED (Tenders Electronic Daily) sample",
        source_url="https://huggingface.co/datasets/OpenMLDatasets/ted_2025_07_sample",
        license="CC0",
        v1_use="Procurement use case, structured procurement metadata",
        target_subdir=Path("inputs/procurement/ted_sample"),
        file_count=100,
        needs_hf_token=False,
    ),
    "polish_tenders": DatasetSpec(
        name="atlasprzetargow/polish-tenders-dataset",
        source_url="https://github.com/atlasprzetargow/polish-tenders-dataset",
        license="CC-BY-4.0",
        v1_use="Multi-currency procurement tests, EU procurement structure",
        target_subdir=Path("inputs/procurement/polish_tenders"),
        file_count=1000,
        needs_hf_token=False,
    ),
    "sroie": DatasetSpec(
        name="ICDAR 2019 SROIE",
        source_url="https://rrc.cvc.uab.es/?ch=13",
        license="research-only",
        v1_use="Real scanned-receipt OCR noise tests (DEV ONLY)",
        target_subdir=Path("inputs/receipts/sroie"),
        file_count=100,
        needs_hf_token=False,
        needs_manual_download=True,
        notes="Research-only license. Use --dev-only to download. NEVER vendored in repo.",
    ),
    "inv_cdip": DatasetSpec(
        name="salesforce/inv-cdip",
        source_url="https://github.com/salesforce/inv-cdip",
        license="CC-BY-NC-4.0",
        v1_use="Real-invoice tests (DEV ONLY)",
        target_subdir=Path("inputs/invoices/inv_cdip"),
        file_count=350,
        needs_hf_token=False,
        notes="Non-commercial license. Use --dev-only to download. NEVER vendored in repo.",
    ),
    "fatura": DatasetSpec(
        name="mathieu1256/FATURA",
        source_url="https://zenodo.org/record/8261508",
        license="CC-BY-NC-4.0",
        v1_use="Multi-layout invoice tests (V2 ONLY)",
        target_subdir=Path("inputs/invoices/fatura"),
        file_count=1000,
        needs_hf_token=False,
        notes="Non-commercial license. V2 only.",
    ),
}


def cmd_list(_: argparse.Namespace) -> int:
    print(f"{'Name':<30} {'License':<20} {'V1?':<6} {'Files':<8} Use")
    print("-" * 110)
    for key, spec in DATASETS.items():
        is_v1 = spec.license in ALLOWED_LICENSES
        marker = "✅" if is_v1 else "⚠️ "
        print(
            f"{key:<30} {spec.license:<20} {marker}      {spec.file_count:<8} {spec.v1_use}"
        )
    return 0


def cmd_vendor(args: argparse.Namespace) -> int:
    if args.dataset:
        names = [args.dataset]
    else:
        names = [k for k, v in DATASETS.items() if v.license in ALLOWED_LICENSES]

    failed: list[str] = []
    for name in names:
        if name not in DATASETS:
            logger.error("Unknown dataset: %s", name)
            failed.append(name)
            continue

        spec = DATASETS[name]
        if spec.license not in ALLOWED_LICENSES and not args.dev_only:
            logger.warning(
                "Skipping %s: license '%s' is not in the allowed list. "
                "Use --dev-only to download for personal development.",
                name,
                spec.license,
            )
            continue

        if spec.license in DEV_ONLY_LICENSES and not args.dev_only:
            logger.warning("Skipping %s: dev-only license.", name)
            continue

        if spec.license not in ALLOWED_LICENSES:
            continue

        target = FIXTURES_DIR / spec.target_subdir
        target.mkdir(parents=True, exist_ok=True)

        try:
            vendor_one(spec, target, update=args.update)
            log_success(name, spec)
        except Exception as e:
            logger.error("Failed to vendor %s: %s", name, e)
            failed.append(name)

    if failed:
        logger.error("Failed datasets: %s", ", ".join(failed))
        return 1
    return 0


def vendor_one(spec: DatasetSpec, target: Path, update: bool) -> None:
    marker_file = target / ".VENDORED"
    if marker_file.exists() and not update:
        logger.info("Already vendored: %s (use --update to re-fetch)", spec.name)
        return

    if spec.needs_manual_download:
        logger.info(
            "Manual download required for %s.\n"
            "  1. Visit: %s\n"
            "  2. Download to: %s\n"
            "  3. Re-run this script.",
            spec.name,
            spec.source_url,
            target,
        )
        return

    logger.info("Vendoring %s...", spec.name)
    logger.info("  Source: %s", spec.source_url)
    logger.info("  Target: %s", target)
    logger.info("  License: %s", spec.license)

    raise NotImplementedError(
        f"Download logic for {spec.name} not yet implemented. "
        f"See docs/TEST_DATA.md §6 for the implementation contract: "
        f"download files to {target}, verify checksums, write a .VENDORED "
        f"marker, and update DATASET_LICENSES.md. Use "
        f"huggingface_hub.snapshot_download for HF datasets, "
        f"gh release download for GitHub, urllib.request for direct URLs."
    )


def log_success(name: str, spec: DatasetSpec) -> None:
    from datetime import datetime, timezone

    timestamp = datetime.now(timezone.utc).isoformat()
    entry = f"\n## {timestamp} — {name}\n\n"
    entry += f"- Source: {spec.source_url}\n"
    entry += f"- Target: `tests/fixtures/{spec.target_subdir}/`\n"
    entry += f"- License: {spec.license}\n"
    entry += f"- Files: {spec.file_count}\n"

    if LOG_FILE.exists():
        existing = LOG_FILE.read_text(encoding="utf-8")
    else:
        existing = "# Paxman Test Data Download Log\n\n"
        existing += "> Auto-generated by `scripts/fetch_test_data.py`. Do not edit by hand.\n"

    LOG_FILE.write_text(existing + entry, encoding="utf-8")


def cmd_verify(_: argparse.Namespace) -> int:
    errors: list[str] = []

    for key, spec in DATASETS.items():
        if spec.license not in ALLOWED_LICENSES:
            continue  # research-only datasets not vendored

        target = FIXTURES_DIR / spec.target_subdir
        marker = target / ".VENDORED"

        if not target.exists() or not marker.exists():
            errors.append(
                f"Missing vendored data for {key}: expected {target}/.VENDORED"
            )

    if errors:
        logger.error("Verification failed:")
        for e in errors:
            logger.error("  - %s", e)
        return 1

    logger.info("All vendored datasets verified.")
    return 0


def cmd_validate_licenses(_: argparse.Namespace) -> int:
    if not LICENSES_FILE.exists():
        logger.error("Missing %s", LICENSES_FILE)
        return 1

    text = LICENSES_FILE.read_text(encoding="utf-8")
    catalog_entries = set()
    for line in text.splitlines():
        if line.startswith("### "):
            catalog_entries.add(line[4:].strip().lower())

    known_safe_files = {"README.md", ".gitignore", "DATASET_LICENSES.md", "DOWNLOAD_LOG.md"}
    errors: list[str] = []

    for path in FIXTURES_DIR.rglob("*"):
        if not path.is_file():
            continue
        if path.name in known_safe_files:
            continue
        rel = path.relative_to(FIXTURES_DIR)
        matched = False
        for entry in catalog_entries:
            if any(token.lower() in rel.as_posix().lower() for token in entry.split()):
                matched = True
                break
        if not matched:
            errors.append(f"Unattributed file: {rel}")

    if errors:
        logger.error("Found %d unattributed files:", len(errors))
        for e in errors:
            logger.error("  - %s", e)
        return 1

    logger.info("All vendored files are attributed in %s.", LICENSES_FILE.name)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Vendor and verify Paxman test data.",
    )
    parser.add_argument(
        "--dataset",
        help="Vendor only this dataset (by short name)",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Re-vendor even if already present",
    )
    parser.add_argument(
        "--dev-only",
        action="store_true",
        help="Allow downloading research-only / non-commercial datasets for personal development",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List known datasets and licenses",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify that vendored data is present (CI use)",
    )
    parser.add_argument(
        "--validate-licenses",
        action="store_true",
        help="Validate that every file is attributed in DATASET_LICENSES.md (CI use)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if args.list:
        return cmd_list(args)
    if args.verify:
        return cmd_verify(args)
    if args.validate_licenses:
        return cmd_validate_licenses(args)
    return cmd_vendor(args)


if __name__ == "__main__":
    sys.exit(main())
