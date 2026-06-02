from __future__ import annotations

from colosseum_equipment.protocols.scpi import SCPIHelper, wait_opc


def sens_prefix(channel: int) -> str:
    return f"SENS{int(channel)}"


def init_prefix(channel: int) -> str:
    return f"INIT{int(channel)}"
