#!/usr/bin/env bash
# R-GUI-QEMU-01: launch colosseum --gui on guest with X11 forwarding (manual sign-off).
# R-GUI-QEMU-01b: optional headless probe via xvfb-run when --headless is passed.
#
# Usage:
#   ./infra/yocto/run_gui_regression.sh
#   ./infra/yocto/run_gui_regression.sh --headless

set -euo pipefail

# shellcheck source=scripts/common.sh
source "$(dirname "$0")/scripts/common.sh"
ensure_artifacts_dir

HEADLESS="${1:-}"
LOG="${ARTIFACTS}/gui-regression-$(date -u +%Y%m%dT%H%M%SZ).log"
exec > >(tee -a "${LOG}") 2>&1

echo "=== R-GUI-QEMU GUI regression ==="
echo "Log: ${LOG}"

"$(dirname "$0")/scripts/install-offline-bundle.sh"

if [[ "${HEADLESS}" == "--headless" ]]; then
  echo "--- R-GUI-QEMU-01b (xvfb headless probe) ---"
  if ! qemu_ssh "command -v xvfb-run >/dev/null 2>&1"; then
    echo "WARNING: xvfb-run not on guest; skipping headless probe" >&2
    exit 0
  fi
  qemu_ssh "xvfb-run -a ${COLOSSEUM_BIN} --help"
  echo "Headless probe complete (does not validate X11 forwarding)."
  exit 0
fi

if [[ -z "${DISPLAY:-}" ]]; then
  echo "ERROR: DISPLAY is not set on the host." >&2
  echo "Start an X server (VcXsrv, X410, WSLg, native X) and export DISPLAY before ssh -X." >&2
  echo "For automated headless probe only, use: $0 --headless" >&2
  exit 1
fi

echo "--- R-GUI-QEMU-01 (interactive X11 forward) ---"
echo "Launching GUI on guest; window should appear on host DISPLAY=${DISPLAY}"
echo "Verify manually: pick smoke script, run test, confirm log output."
ssh -X "${SSH_OPTS[@]}" "${QEMU_SSH_USER}@${QEMU_SSH_HOST}" "${COLOSSEUM_BIN}" --gui

echo "=== R-GUI-QEMU-01 complete (manual sign-off) ==="
