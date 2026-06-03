#!/usr/bin/env bash
# Start QEMU with slirp and wait for guest SSH (smoke test driver).
set -eo pipefail

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export QEMU_SSH_TIMEOUT="${QEMU_SSH_TIMEOUT:-300}"

POKY="${POKY:-${HOME}/poky-kirkstone}"
BUILD="${BUILD:-${HOME}/colosseum-yocto/build}"
YOCTO="$(cd "$(dirname "$0")/.." && pwd)"

rm -f "${YOCTO}/artifacts/qemu.pid"
pkill -f 'qemu-system-x86_64.*colosseum-qemu-image' 2>/dev/null || true

# shellcheck disable=SC1091
source "${POKY}/oe-init-build-env" "${BUILD}"

"${YOCTO}/scripts/qemu-up.sh"
for _ in $(seq 1 30); do
  if pgrep -f 'qemu-system-x86_64.*colosseum-qemu-image-qemux86-64' >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
if ! pgrep -f 'qemu-system-x86_64.*colosseum-qemu-image-qemux86-64' >/dev/null 2>&1; then
  echo "ERROR: qemu-system-x86_64 exited early; see ${YOCTO}/artifacts/qemu.log" >&2
  tail -20 "${YOCTO}/artifacts/qemu.log" >&2 || true
  exit 1
fi

exec "${YOCTO}/scripts/qemu-wait-ssh.sh"
