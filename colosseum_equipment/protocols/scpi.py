from __future__ import annotations

import re

from colosseum_equipment.exceptions import EquipmentResponseError
from colosseum_equipment.transports.base import Transport


def strip_response(text: str) -> str:
    return text.strip()


def parse_float(text: str) -> float:
    match = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", text)
    if not match:
        raise EquipmentResponseError(f"No numeric value in response: {text!r}")
    return float(match.group(0))


class SCPIHelper:
    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    def write(self, command: str) -> None:
        self._transport.write(command)

    def query(self, command: str) -> str:
        return strip_response(self._transport.query(command))

    def query_float(self, command: str) -> float:
        return parse_float(self.query(command))


def write_transport(transport: Transport, command: str) -> None:
    transport.write(command)


def query_transport(transport: Transport, command: str) -> str:
    return strip_response(transport.query(command))
