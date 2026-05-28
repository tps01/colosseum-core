"""U-SH-01: SSH sim stdout contract."""

from __future__ import annotations

from colosseum.context import init_context
from colosseum_shared.ssh.client import SSHClientWrapper


def test_version_command_returns_semver_like_string(isolated_cwd) -> None:
    init_context(test_case_name="ssh_sim")
    client = SSHClientWrapper({"driver": "sim", "host": "sim.local", "username": "pi"})
    out = client.exec_stdout("cat /etc/version")
    assert "v1.2.3" in out


def test_os_release_marker_command(isolated_cwd) -> None:
    init_context(test_case_name="ssh_sim")
    client = SSHClientWrapper({"driver": "sim", "host": "sim.local", "username": "pi"})
    out = client.exec_stdout("test -f /etc/os-release && echo present")
    assert "present" in out
