"""I-SH: shared SSH + regex on sim."""

from __future__ import annotations

import colosseum as col
from colosseum.config import load_config

from tests.conftest import run_endex_expect_code

_VERSION_PATTERN = r"v\d+\.\d+\.\d+"


def test_ssh_measure_and_regex_verify(bench_sim, isolated_cwd) -> None:
    load_config(bench_sim)
    col.shared.ssh.measure_stdout(ssh_id=1, command="cat /etc/version", key="uut_version")
    v_result = col.shared.regex.verify_match(key="uut_version", pattern=_VERSION_PATTERN)
    assert v_result.status == "PASS"
    col.shared.ssh.measure_stdout(
        ssh_id=1, command="test -f /etc/os-release && echo present", key="os_release_marker"
    )
    o_result = col.shared.regex.verify_match(key="os_release_marker", pattern=r"present")
    assert o_result.status == "PASS"
    run_endex_expect_code(0)
