#!/usr/bin/env bash
set -eo pipefail
export PATH="${HOME}/colosseum-venv/bin:${PATH}"
cd /mnt/c/Users/tomlocal/colloseum
export COLOSSEUM_BENCH_CONFIG=bench.qemu.toml
colosseum run examples/test_ssh_health.py --config infra/yocto/conf/bench.qemu.toml
echo "exit=$?"
