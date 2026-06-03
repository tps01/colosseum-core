#!/usr/bin/env bash
# Build offline bundle, copy to guest, and install colosseum into /opt/colosseum-venv.
#
# Usage:
#   ./infra/yocto/scripts/install-offline-bundle.sh
#   SKIP_PACKAGE=1 ./infra/yocto/scripts/install-offline-bundle.sh   # reuse latest tarball
#
# Note: run package_offline.py on Linux when building for the qemux86-64 guest.

set -euo pipefail

# shellcheck source=common.sh
source "$(dirname "$0")/common.sh"

SKIP_PACKAGE="${SKIP_PACKAGE:-0}"
ARCHIVE="${OFFLINE_ARCHIVE:-}"
# Yocto guest image ships Python 3.10; resolve wheels for that runtime.
export COLOSSEUM_OFFLINE_PYTHON_VERSION="${COLOSSEUM_OFFLINE_PYTHON_VERSION:-3.10}"

cd "${REPO_ROOT}"

if [[ "${SKIP_PACKAGE}" != "1" ]]; then
  python scripts/package_offline.py
fi

if [[ -z "${ARCHIVE}" ]]; then
  ARCHIVE="$(ls -1t colosseum-*-offline-*.tar.gz 2>/dev/null | head -1 || true)"
fi

if [[ -z "${ARCHIVE}" || ! -f "${ARCHIVE}" ]]; then
  echo "ERROR: offline bundle tarball not found under ${REPO_ROOT}" >&2
  exit 1
fi

echo "Using bundle: ${ARCHIVE}"
qemu_scp "${ARCHIVE}" "${QEMU_SSH_USER}@${QEMU_SSH_HOST}:/tmp/colosseum-offline.tar.gz"

qemu_ssh sh -s <<'REMOTE'
set -eu
cd /tmp
rm -rf offline-bundle
tar xzf colosseum-offline.tar.gz
python3 -m venv /opt/colosseum-venv
/opt/colosseum-venv/bin/pip install --no-index --find-links=offline-bundle/wheels colosseum
/opt/colosseum-venv/bin/colosseum --help
REMOTE

echo "Offline install complete: ${COLOSSEUM_BIN}"
