#!/bin/bash
# ------------------------------------------------------------------
# run_notebooks.sh — Execute all playground notebooks headlessly
#
# Usage:
#   From inside the running container:
#     bash /path/to/run_notebooks.sh
#
#   From the host (with 'jupyter nbconvert' on PATH and the venv
#   containing paxman active):
#     bash playground/tooling/run_notebooks.sh
#
# The script runs each .ipynb in the configured NOTEBOOK_DIR and
# reports pass/fail.  Returns exit code 0 if all pass, 1 otherwise.
#
# Each notebook gets a TIMEOUT_SEC (default 300) to complete; if it
# hangs past that bound the script treats it as a failure.
# ------------------------------------------------------------------
set -euo pipefail

NOTEBOOK_DIR="${1:-/home/jovyan/playground/notebooks}"
TIMEOUT_SEC="${2:-300}"
PASS=0
FAIL=0
FAILED_LIST=""

if [ ! -d "$NOTEBOOK_DIR" ]; then
    echo "ERROR: notebook directory not found: $NOTEBOOK_DIR" >&2
    echo "Pass the correct path as the first argument, e.g." >&2
    echo "  bash $0 /path/to/notebooks" >&2
    exit 1
fi

echo "Notebook directory: $NOTEBOOK_DIR"
echo ""

for nb in "$NOTEBOOK_DIR"/*.ipynb; do
    [ -f "$nb" ] || continue
    name=$(basename "$nb")
    echo "=== Running: $name ==="
    out_json=$(mktemp /tmp/nb-exec-XXXXXX.ipynb)
    err_log=$(mktemp /tmp/nb-err-XXXXXX.txt)

    if timeout "$TIMEOUT_SEC" jupyter nbconvert --execute --to notebook --output "$out_json" "$nb" 2>"$err_log"; then
        echo "  PASS: $name"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $name"
        sed 's/^/    /' "$err_log"
        FAIL=$((FAIL + 1))
        FAILED_LIST="$FAILED_LIST $name"
    fi

    rm -f "$out_json" "$err_log"
    echo ""
done

echo "=============================="
echo "Results: $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then
    echo "Failed notebooks:$FAILED_LIST"
    exit 1
fi
echo "All notebooks pass!"
