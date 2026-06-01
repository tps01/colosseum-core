"""
R-EMU-02: regex on noisy live stdout from QEMU guest.

Run from host:
  colosseum run infra/yocto/examples/regex_noisy_stdout.py \\
    --config infra/yocto/conf/bench.qemu.toml
"""

from __future__ import annotations

import colosseum as col

# Kernel release token should appear in uname -sr output despite prompt noise.
_UNAME_PATTERN = r"Linux\s+(\d+\.\d+\.\d+-yocto-standard)"


def main() -> None:
    col.shared.ssh.measure_stdout(
        ssh_id=1,
        command="echo 'prompt# '; uname -sr",
        key="noisy_uname",
    )
    col.shared.regex.verify_match(key="noisy_uname", pattern=_UNAME_PATTERN)


if __name__ == "__main__":
    main()
    col.endex()
