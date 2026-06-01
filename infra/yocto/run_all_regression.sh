#!/usr/bin/env bash
# Run full Tier 4C Yocto/QEMU regression matrix (manual).
#
# Usage:
#   ./infra/yocto/run_all_regression.sh
#   ./infra/yocto/run_all_regression.sh --skip-gui-interactive

set -euo pipefail

# shellcheck source=scripts/common.sh
source "$(dirname "$0")/scripts/common.sh"
ensure_artifacts_dir

SKIP_GUI="${1:-}"
LOG="${ARTIFACTS}/full-regression-$(date -u +%Y%m%dT%H%M%SZ).log"
exec > >(tee -a "${LOG}") 2>&1

YOCTO_DIR="$(dirname "$0")"

echo "=== Colosseum Yocto/QEMU full regression ==="
echo "Log: ${LOG}"

"${YOCTO_DIR}/scripts/qemu-wait-ssh.sh"

echo "=== Phase 1: offline install + guest smoke (R-OFFLINE-01) ==="
"${YOCTO_DIR}/run_offline_regression.sh"

echo "=== Phase 2: SSH endpoint from host (R-EMU-01/02/03) ==="
"${YOCTO_DIR}/run_ssh_regression.sh" --all

echo "=== Phase 3: GUI ==="
if [[ "${SKIP_GUI}" == "--skip-gui-interactive" ]]; then
  "${YOCTO_DIR}/run_gui_regression.sh" --headless
else
  echo "Run GUI interactively if desired:"
  echo "  ${YOCTO_DIR}/run_gui_regression.sh"
  echo "Or headless probe:"
  echo "  ${YOCTO_DIR}/run_gui_regression.sh --headless"
fi

echo "=== Full regression orchestration complete ==="
