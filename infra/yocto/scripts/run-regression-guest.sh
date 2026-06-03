#!/usr/bin/env bash
# Run Tier 4C regression phases against an already-running QEMU guest.
set -eo pipefail

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export PATH="${HOME}/colosseum-venv/bin:${PATH}"

YOCTO="$(cd "$(dirname "$0")/.." && pwd)"
LOG="${YOCTO}/artifacts/regression-run-$(date -u +%Y%m%dT%H%M%SZ).log"
exec > >(tee -a "${LOG}") 2>&1

echo "=== Colosseum regression (guest already up) ==="
echo "Log: ${LOG}"

"${YOCTO}/scripts/qemu-wait-ssh.sh"

echo "=== Phase 1: offline install + guest smoke (R-OFFLINE-01) ==="
"${YOCTO}/run_offline_regression.sh"

echo "=== Phase 2: SSH endpoint from host (R-EMU-01/02/03) ==="
"${YOCTO}/run_ssh_regression.sh" --all

echo "=== Phase 3: GUI headless ==="
"${YOCTO}/run_gui_regression.sh" --headless

echo "=== Regression complete ==="
