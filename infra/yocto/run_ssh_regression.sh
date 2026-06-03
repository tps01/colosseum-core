#!/usr/bin/env bash
# R-EMU-01/02/03: run Colosseum SSH regression cases from the host against QEMU guest.
#
# Usage:
#   ./infra/yocto/run_ssh_regression.sh              # R-EMU-01
#   ./infra/yocto/run_ssh_regression.sh --extended   # R-EMU-01 + R-EMU-02
#   ./infra/yocto/run_ssh_regression.sh --suite      # R-EMU-03
#   ./infra/yocto/run_ssh_regression.sh --all        # all SSH cases

set -euo pipefail

# shellcheck source=scripts/common.sh
source "$(dirname "$0")/scripts/common.sh"
ensure_artifacts_dir

MODE="${1:-}"
LOG="${ARTIFACTS}/ssh-regression-$(date -u +%Y%m%dT%H%M%SZ).log"
exec > >(tee -a "${LOG}") 2>&1

BENCH_CONFIG="${YOCTO_ROOT}/conf/bench.qemu.toml"
SSH_HEALTH="${REPO_ROOT}/examples/test_ssh_health.py"
REGEX_SCRIPT="${YOCTO_ROOT}/examples/regex_noisy_stdout.py"
SUITE="${YOCTO_ROOT}/suites/embedded_smoke.toml"

run_case() {
  local label="$1"
  shift
  echo "--- ${label} ---"
  "$@"
  echo "--- ${label} PASS ---"
}

echo "=== SSH regression (host -> QEMU guest) ==="
echo "Log: ${LOG}"
echo "Config: ${BENCH_CONFIG}"

cd "${REPO_ROOT}"
export COLOSSEUM_BENCH_CONFIG=bench.qemu.toml

RUN_EXTENDED=0
RUN_SUITE=0

case "${MODE}" in
  "" ) ;;
  --extended ) RUN_EXTENDED=1 ;;
  --suite ) RUN_SUITE=1 ;;
  --all )
    RUN_EXTENDED=1
    RUN_SUITE=1
    ;;
  * )
    echo "Usage: $0 [--extended|--suite|--all]" >&2
    exit 2
    ;;
esac

run_case "R-EMU-01" colosseum run "${SSH_HEALTH}" --config "${BENCH_CONFIG}"

if [[ "${RUN_EXTENDED}" -eq 1 ]]; then
  run_case "R-EMU-02" colosseum run "${REGEX_SCRIPT}" --config "${BENCH_CONFIG}"
fi

if [[ "${RUN_SUITE}" -eq 1 ]]; then
  run_case "R-EMU-03" colosseum run-suite "${SUITE}" --config "${BENCH_CONFIG}"
fi

echo "=== SSH regression PASS ==="
