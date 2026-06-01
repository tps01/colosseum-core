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


def format_definite_length_block(payload: bytes) -> bytes:
    length = len(payload)
    digits = str(length)
    return f"#{len(digits)}{length}".encode("ascii") + payload


def parse_definite_length_block(data: bytes) -> bytes:
    if not data.startswith(b"#"):
        return data
    digit_count = int(chr(data[1]))
    length = int(data[2 : 2 + digit_count].decode("ascii"))
    start = 2 + digit_count
    return data[start : start + length]


class SCPIHelper:
    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    def write(self, command: str) -> None:
        self._transport.write(command)

    def query(self, command: str) -> str:
        return strip_response(self._transport.query(command))

    def query_float(self, command: str) -> float:
        return parse_float(self.query(command))

    def write_binary_block(self, command_prefix: str, payload: bytes) -> None:
        block = format_definite_length_block(payload)
        write_raw = getattr(self._transport, "write_raw", None)
        if not callable(write_raw):
            raise EquipmentResponseError("Transport does not support binary block writes")
        write_raw(f"{command_prefix} ".encode("ascii") + block)

    def read_binary_block(self, command: str) -> bytes:
        read_raw = getattr(self._transport, "read_raw", None)
        if not callable(read_raw):
            raise EquipmentResponseError("Transport does not support binary block reads")
        self.write(command)
        return parse_definite_length_block(read_raw())


def wait_opc(scpi: SCPIHelper) -> None:
    scpi.query("*OPC?")


def prepare_fast_sweep(scpi: SCPIHelper) -> None:
    scpi.write("DISP:UPD OFF")


def write_transport(transport: Transport, command: str) -> None:
    transport.write(command)


def query_transport(transport: Transport, command: str) -> str:
    return strip_response(transport.query(command))
