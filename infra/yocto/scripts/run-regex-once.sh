#!/usr/bin/env bash
set -eo pipefail
export PATH="${HOME}/colosseum-venv/bin:${PATH}"
cd /mnt/c/Users/tomlocal/colloseum
colosseum run infra/yocto/examples/regex_noisy_stdout.py --config infra/yocto/conf/bench.qemu.toml
echo "exit=$?"
