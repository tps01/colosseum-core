#!/usr/bin/env bash
# Run QEMU up + full Tier 4C regression (host-side driver).
set -eo pipefail

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export PATH="${HOME}/colosseum-venv/bin:${PATH}"
export QEMU_SSH_TIMEOUT="${QEMU_SSH_TIMEOUT:-300}"

POKY="${POKY:-${HOME}/poky-kirkstone}"
BUILD="${BUILD:-${HOME}/colosseum-yocto/build}"
YOCTO="$(cd "$(dirname "$0")/.." && pwd)"

# shellcheck disable=SC1091
source "${POKY}/oe-init-build-env" "${BUILD}"

"${YOCTO}/scripts/qemu-up.sh"
exec "${YOCTO}/run_all_regression.sh" "$@"
