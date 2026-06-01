#!/usr/bin/env bash
# Bootstrap Yocto build for colosseum-qemu-image (WSL/Linux).
set -eo pipefail

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

REPO="${REPO:-/mnt/c/Users/tomlocal/colloseum}"
LAYER="${REPO}/infra/yocto/meta-colosseum-test"
POKY="${POKY:-${HOME}/poky-kirkstone}"
BUILD="${BUILD:-${HOME}/colosseum-yocto/build}"

if [[ ! -d "${POKY}" ]]; then
  echo "ERROR: Poky not found at ${POKY}. Clone kirkstone first." >&2
  exit 1
fi

mkdir -p "${HOME}/colosseum-yocto/cache/downloads" "${HOME}/colosseum-yocto/cache/sstate"

# shellcheck disable=SC1091
source "${POKY}/oe-init-build-env" "${BUILD}"

bitbake-layers add-layer "${LAYER}" 2>/dev/null || true

cp "${LAYER}/conf/local.conf.sample" conf/local.conf

cat >>conf/local.conf <<EOF

# Bootstrap overrides (Linux filesystem for performance).
DL_DIR = "\${HOME}/colosseum-yocto/cache/downloads"
SSTATE_DIR = "\${HOME}/colosseum-yocto/cache/sstate"
EOF

echo "Build directory: ${PWD}"

if [[ "${1:-}" == "--build" ]]; then
  exec bitbake colosseum-qemu-image
fi

bitbake-layers show-layers | grep colosseum || true
