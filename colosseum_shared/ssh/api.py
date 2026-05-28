from __future__ import annotations

from colosseum.decorators import measurement

from colosseum_shared.connections import get_ssh_client


@measurement
def measure_stdout(*, ssh_id: int, command: str, key: str, timeout: float = 30.0) -> str:
    return get_ssh_client(ssh_id).exec_stdout(command, timeout=timeout)
