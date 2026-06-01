#!/usr/bin/env bash
# R-OFFLINE-01: offline pip install on QEMU guest + sim smoke test.

set -euo pipefail

# shellcheck source=scripts/common.sh
source "$(dirname "$0")/scripts/common.sh"
ensure_artifacts_dir

LOG="${ARTIFACTS}/offline-regression-$(date -u +%Y%m%dT%H%M%SZ).log"
exec > >(tee -a "${LOG}") 2>&1

echo "=== R-OFFLINE-01: Colosseum offline regression ==="
echo "Log: ${LOG}"

"$(dirname "$0")/scripts/install-offline-bundle.sh"

qemu_ssh sh -s <<'REMOTE'
set -eu
/opt/colosseum-venv/bin/colosseum run /tmp/offline-bundle/smoke/run_sim.py \
  --config /tmp/offline-bundle/smoke/bench.sim.toml
REMOTE

echo "=== R-OFFLINE-01 PASS ==="
