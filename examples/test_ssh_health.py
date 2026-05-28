"""
Target example: DUT software health via SSH (Wave 2+).

Development goal:
  - col.shared.ssh.measure_stdout stores stdout under a measurement key
  - col.shared.regex.verify_match reads measure_stdout evidence (not verify_match rows)
  - col.endex() aggregates required/optional verifications and exits 0/1 (no manual result loop)

Run when implemented:
  python examples/test_ssh_health.py
  colosseum run examples/test_ssh_health.py --config examples/configs/bench.toml
"""

from __future__ import annotations
import os
from pathlib import Path
import colosseum as col

_CONFIG = Path(__file__).resolve().parent / "configs" / os.environ.get("COLOSSEUM_BENCH_CONFIG", "bench.toml")

# Version pattern for embedded Linux image strings
_VERSION_PATTERN = r"v\d+\.\d+\.\d+"

def main() -> None:
    col.config.load_config(str(_CONFIG))

    col.shared.ssh.measure_stdout(ssh_id=1, command="cat /etc/version", key="uut_version")
    col.shared.regex.verify_match(key="uut_version", pattern=_VERSION_PATTERN)

    col.shared.ssh.measure_stdout(ssh_id=1, command="test -f /etc/os-release && echo present", key="os_release_marker")
    col.shared.regex.verify_match(key="os_release_marker", pattern=r"present")


if __name__ == "__main__":
    main()
    col.endex()
