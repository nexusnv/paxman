#!/usr/bin/env python3
"""
validate_quote.py – Validate a quote JSON file against the OQO schema.

Usage:
    python validate_quote.py <quote.json> <schema.json>

Requires the `jsonschema` package (install via `pip install jsonschema`).
"""
import json
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:
    print("Error: The 'jsonschema' package is required. Install it via 'pip install jsonschema'.")
    sys.exit(1)


def load_json(path: Path):
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    quote_path = Path(sys.argv[1])
    schema_path = Path(sys.argv[2])
    if not quote_path.exists() or not schema_path.exists():
        print(f"Error: File(s) not found: {quote_path}, {schema_path}")
        sys.exit(1)
    quote_data = load_json(quote_path)
    schema_data = load_json(schema_path)
    validator = Draft202012Validator(schema_data)
    errors = sorted(validator.iter_errors(quote_data), key=lambda e: e.path)
    if not errors:
        print("PASS: Quote is valid according to the schema.")
    else:
        print(f"FAIL: Quote is invalid. Found {len(errors)} error(s):")
        for idx, error in enumerate(errors, 1):
            path = '.'.join(str(p) for p in error.path) or 'root'
            print(f" {idx}. [{path}] {error.message}")
        sys.exit(1)


if __name__ == '__main__':
    main()
