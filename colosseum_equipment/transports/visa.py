from __future__ import annotations

from colosseum_equipment.exceptions import EquipmentConnectionError, EquipmentTimeoutError
from colosseum_equipment.transports.base import Transport


class VISATransport(Transport):
    def __init__(self, resource: str, timeout: float = 5.0) -> None:
        try:
            import pyvisa
        except ImportError as exc:  # pragma: no cover
            raise EquipmentConnectionError(
                "pyvisa is required for driver=visa. Install colosseum with the equipment extra."
            ) from exc

        self._timeout = timeout
        try:
            self._rm = pyvisa.ResourceManager()
            self._inst = self._rm.open_resource(resource)
            self._inst.timeout = int(timeout * 1000)
        except Exception as exc:
            raise EquipmentConnectionError(f"Failed to open VISA resource `{resource}`: {exc}") from exc

    def write(self, data: str) -> None:
        try:
            self._inst.write(data)
        except Exception as exc:
            raise EquipmentTimeoutError(str(exc)) from exc

    def read(self) -> str:
        try:
            return str(self._inst.read())
        except Exception as exc:
            raise EquipmentTimeoutError(str(exc)) from exc

    def query(self, data: str) -> str:
        try:
            return str(self._inst.query(data))
        except Exception as exc:
            raise EquipmentTimeoutError(str(exc)) from exc

    def close(self) -> None:
        try:
            self._inst.close()
        except Exception:
            pass
        try:
            self._rm.close()
        except Exception:
            pass
