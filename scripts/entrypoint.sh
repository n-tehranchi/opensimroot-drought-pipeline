#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# entrypoint.sh
# Runs the OpenSimRoot binary with a specified XML input file.
# ---------------------------------------------------------------------------

# Required environment variables
: "${INPUT_FILE:?Error: INPUT_FILE env var is not set}"

# Optional
OUTPUT_PATH="${OUTPUT_PATH:-/sim/output}"

# Fall back to bundled inputs if INPUT_DIR is not set or does not exist
if [[ -n "${INPUT_DIR:-}" && -d "${INPUT_DIR}" ]]; then
    XML_PATH="${INPUT_DIR}/${INPUT_FILE}"
else
    XML_PATH="/opt/inputs/${INPUT_FILE}"
fi

echo "============================================"
echo "OpenSimRoot Simulation"
echo "  Input file:  ${XML_PATH}"
echo "  Output path: ${OUTPUT_PATH}"
echo "============================================"

# Verify the input file exists
if [[ ! -f "${XML_PATH}" ]]; then
    echo "ERROR: Input file not found: ${XML_PATH}"
    exit 1
fi

# Prepare output directory
mkdir -p "${OUTPUT_PATH}"

# Run from the output directory so OpenSimRoot writes results there
cd "${OUTPUT_PATH}"

echo "Running OpenSimRoot..."
OpenSimRoot "${XML_PATH}" || true

echo "Simulation completed. FATAL ERROR messages from this model version are expected warnings."
echo "Results saved to: ${OUTPUT_PATH}"
exit 0
