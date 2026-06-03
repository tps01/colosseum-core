#!/usr/bin/env bash
# Shared paths and SSH settings for Colosseum QEMU regression scripts.

YOCTO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "${YOCTO_ROOT}/../.." && pwd)"
ARTIFACTS="${YOCTO_ROOT}/artifacts"
SCRIPTS="${YOCTO_ROOT}/scripts"

QEMU_SSH_HOST="${QEMU_SSH_HOST:-127.0.0.1}"
QEMU_SSH_PORT="${QEMU_SSH_PORT:-2222}"
QEMU_SSH_USER="${QEMU_SSH_USER:-root}"
QEMU_PID_FILE="${ARTIFACTS}/qemu.pid"
QEMU_LOG_FILE="${ARTIFACTS}/qemu.log"

COLOSSEUM_VENV="/opt/colosseum-venv"
COLOSSEUM_BIN="${COLOSSEUM_VENV}/bin/colosseum"

SSH_OPTS=(
  -p "${QEMU_SSH_PORT}"
  -o StrictHostKeyChecking=no
  -o UserKnownHostsFile=/dev/null
  -o LogLevel=ERROR
)

SCP_OPTS=(
  -P "${QEMU_SSH_PORT}"
  -o StrictHostKeyChecking=no
  -o UserKnownHostsFile=/dev/null
  -o LogLevel=ERROR
)

qemu_ssh() {
  ssh "${SSH_OPTS[@]}" "${QEMU_SSH_USER}@${QEMU_SSH_HOST}" "$@"
}

qemu_scp() {
  scp "${SCP_OPTS[@]}" "$@"
}

ensure_artifacts_dir() {
  mkdir -p "${ARTIFACTS}"
}
