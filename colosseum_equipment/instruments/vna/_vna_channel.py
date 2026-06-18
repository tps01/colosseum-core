from __future__ import annotations


def sens_prefix(channel: int) -> str:
    return f"SENS{int(channel)}"


def init_prefix(channel: int) -> str:
    return f"INIT{int(channel)}"


def calc_prefix(channel: int) -> str:
    return f"CALC{int(channel)}"


def disp_prefix(channel: int) -> str:
    return f"DISP:WIND{int(channel)}"


def sour_prefix(port: int) -> str:
    return f"SOUR{int(port)}"
