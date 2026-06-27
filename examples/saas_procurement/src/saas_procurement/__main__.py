"""CLI entry point: ``python -m saas_procurement <manifest> <output_dir>``."""

from __future__ import annotations

import sys
from pathlib import Path

from saas_procurement import run_pipeline


def main() -> int:
    """Run the batch pipeline from the command line.

    Returns:
        Exit code: 0 on success, 2 on usage error.
    """
    if len(sys.argv) != 3:
        print(
            "Usage: python -m saas_procurement <manifest.csv> <output_dir>",
            file=sys.stderr,
        )
        return 2
    manifest = Path(sys.argv[1])
    output = Path(sys.argv[2])
    if not manifest.exists():
        print(f"Manifest not found: {manifest}", file=sys.stderr)
        return 2
    summary = run_pipeline(manifest, output)
    print(f"Processed {summary.total_rows} rows:")
    print(f"  Successful: {summary.successful}")
    print(f"  Unresolved: {summary.unresolved}")
    print(f"  Failed:     {summary.failed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
