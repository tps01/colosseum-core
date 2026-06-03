#!/usr/bin/env bash
sleep 15
pid="$(cat /mnt/c/Users/tomlocal/colloseum/infra/yocto/artifacts/qemu.pid 2>/dev/null || true)"
if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
  echo "QEMU still running pid=${pid}"
  ssh -p 2222 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 cat /etc/version
else
  echo "QEMU not running"
  tail -5 /mnt/c/Users/tomlocal/colloseum/infra/yocto/artifacts/qemu.log
  exit 1
fi
