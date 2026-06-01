#!/usr/bin/env bash
# Run SSH + GUI regression phases only (guest up, colosseum already installed).
set -eo pipefail
export PATH="${HOME}/colosseum-venv/bin:${PATH}"
YOCTO="$(cd "$(dirname "$0")/.." && pwd)"
"${YOCTO}/run_ssh_regression.sh" --all
"${YOCTO}/run_gui_regression.sh" --headless
echo "=== SSH + GUI regression complete ==="
