from __future__ import annotations

from colosseum_equipment.exceptions import EquipmentConnectionError, EquipmentTimeoutError
from colosseum_equipment.transports.base import Transport


class SerialTransport(Transport):
    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 2.0) -> None:
        try:
            import serial
        except ImportError as exc:  # pragma: no cover
            raise EquipmentConnectionError(
                "pyserial is required for driver=serial. "
                "Install with: pip install colosseum[hardware]"
            ) from exc

        try:
            self._ser = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
        except Exception as exc:
            raise EquipmentConnectionError(f"Failed to open serial port `{port}`: {exc}") from exc

    def write(self, data: str) -> None:
        payload = data if data.endswith("\n") else f"{data}\n"
        self._ser.write(payload.encode("ascii"))

    def read(self) -> str:
        try:
            raw = self._ser.readline()
            return raw.decode("ascii", errors="replace").strip()
        except Exception as exc:
            raise EquipmentTimeoutError(str(exc)) from exc

    def query(self, data: str) -> str:
        self.write(data)
        return self.read()

    def close(self) -> None:
        if self._ser.is_open:
            self._ser.close()
