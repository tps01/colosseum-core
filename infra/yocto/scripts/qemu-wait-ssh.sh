#!/usr/bin/env bash
# Poll guest SSH until reachable or timeout.

set -euo pipefail

# shellcheck source=common.sh
source "$(dirname "$0")/common.sh"

TIMEOUT="${QEMU_SSH_TIMEOUT:-300}"
INTERVAL="${QEMU_SSH_INTERVAL:-2}"

echo "Waiting for SSH at ${QEMU_SSH_USER}@${QEMU_SSH_HOST}:${QEMU_SSH_PORT} (timeout ${TIMEOUT}s)..."

elapsed=0
while (( elapsed < TIMEOUT )); do
  if qemu_ssh true 2>/dev/null; then
    echo "SSH ready after ${elapsed}s"
    exit 0
  fi
  sleep "${INTERVAL}"
  elapsed=$((elapsed + INTERVAL))
done

echo "ERROR: SSH not reachable within ${TIMEOUT}s" >&2
exit 1
