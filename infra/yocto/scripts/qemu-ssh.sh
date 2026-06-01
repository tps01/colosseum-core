#!/usr/bin/env bash
# Convenience wrapper for SSH into the QEMU guest.

set -euo pipefail

# shellcheck source=common.sh
source "$(dirname "$0")/common.sh"

qemu_ssh "$@"
