from __future__ import annotations

import logging

from colosseum_shared.parsing.text import parse_float as _parse_float
from colosseum_shared.parsing.text import strip_response

from colosseum_equipment.exceptions import EquipmentResponseError
from colosseum_equipment.transports.base import Transport

_logger = logging.getLogger("colosseum.equipment")


def parse_float(text: str) -> float:
    try:
        return _parse_float(text)
    except ValueError as exc:
        raise EquipmentResponseError(str(exc)) from exc


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
        _logger.debug("SCPI write: %s", command)
        self._transport.write(command)

    def query(self, command: str) -> str:
        _logger.debug("SCPI query: %s", command)
        response = strip_response(self._transport.query(command))
        _logger.debug("SCPI response: %s", response[:200] + ("..." if len(response) > 200 else ""))
        return response

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
