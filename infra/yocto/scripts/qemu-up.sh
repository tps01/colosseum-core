#!/usr/bin/env bash
# Start colosseum-qemu-image via runqemu in the background.
#
# Preconditions:
#   - Image built (bitbake colosseum-qemu-image)
#   - runqemu available in PATH (after sourcing oe-init-build-env)
#
# Usage:
#   source poky/oe-init-build-env infra/yocto/build
#   ./infra/yocto/scripts/qemu-up.sh

set -euo pipefail

# shellcheck source=common.sh
source "$(dirname "$0")/common.sh"
ensure_artifacts_dir

if [[ -f "${QEMU_PID_FILE}" ]] && kill -0 "$(cat "${QEMU_PID_FILE}")" 2>/dev/null; then
  echo "QEMU already running (pid $(cat "${QEMU_PID_FILE}"))"
  exit 0
fi

if ! command -v runqemu >/dev/null 2>&1; then
  echo "ERROR: runqemu not in PATH. Source oe-init-build-env first." >&2
  exit 1
fi

if command -v setsid >/dev/null 2>&1; then
  setsid -w runqemu colosseum-qemu-image nographic slirp >>"${QEMU_LOG_FILE}" 2>&1 </dev/null &
else
  nohup runqemu colosseum-qemu-image nographic slirp >>"${QEMU_LOG_FILE}" 2>&1 </dev/null &
  disown || true
fi

qemu_pid=""
for _ in $(seq 1 60); do
  qemu_pid="$(pgrep -f 'qemu-system-x86_64.*colosseum-qemu-image-qemux86-64' | head -1 || true)"
  if [[ -n "${qemu_pid}" ]]; then
    break
  fi
  sleep 1
done

if [[ -z "${qemu_pid}" ]]; then
  echo "ERROR: qemu-system-x86_64 did not start; see ${QEMU_LOG_FILE}" >&2
  tail -20 "${QEMU_LOG_FILE}" >&2 || true
  exit 1
fi

echo "${qemu_pid}" >"${QEMU_PID_FILE}"
echo "Started qemu-system-x86_64 (pid ${qemu_pid}); log: ${QEMU_LOG_FILE}"
echo "Wait for SSH: ./infra/yocto/scripts/qemu-wait-ssh.sh"
