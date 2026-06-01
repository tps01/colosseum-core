#!/usr/bin/env bash
# Stop the background runqemu instance started by qemu-up.sh.

set -euo pipefail

# shellcheck source=common.sh
source "$(dirname "$0")/common.sh"

if [[ ! -f "${QEMU_PID_FILE}" ]]; then
  echo "No PID file at ${QEMU_PID_FILE}"
  exit 0
fi

PID="$(cat "${QEMU_PID_FILE}")"
if kill -0 "${PID}" 2>/dev/null; then
  kill "${PID}" || true
  sleep 1
  if kill -0 "${PID}" 2>/dev/null; then
    kill -9 "${PID}" || true
  fi
  echo "Stopped QEMU (pid ${PID})"
else
  echo "QEMU pid ${PID} not running"
  pkill -f 'qemu-system-x86_64.*colosseum-qemu-image-qemux86-64' 2>/dev/null || true
fi

rm -f "${QEMU_PID_FILE}"
