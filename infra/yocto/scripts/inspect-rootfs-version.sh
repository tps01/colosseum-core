#!/usr/bin/env bash
set -eo pipefail
ROOTFS="$(readlink -f "${HOME}/colosseum-yocto/build/tmp/deploy/images/qemux86-64/colosseum-qemu-image-qemux86-64.ext4")"
echo "Image: ${ROOTFS}"
debugfs -R 'cat /etc/version' "${ROOTFS}" 2>&1
