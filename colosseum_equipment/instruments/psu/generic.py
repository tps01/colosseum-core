from __future__ import annotations

import time
from typing import Any

from colosseum_equipment.exceptions import EquipmentTimeoutError
from colosseum_equipment.instruments._base import ScpiInstrumentMixin
from colosseum_equipment.protocols.scpi import SCPIHelper
from colosseum_equipment.transports.base import Transport


class GenericPSU(ScpiInstrumentMixin):
    def __init__(self, transport: Transport, config: dict[str, Any]) -> None:
        self._scpi = SCPIHelper(transport)
        self._config = config
        if "voltage" in config:
            self.set_voltage(float(config["voltage"]))
        if "ocp" in config:
            self.set_current_limit(float(config["ocp"]))

    def set_voltage(self, voltage: float) -> None:
        self._scpi.write(f"VOLT {voltage}")

    def set_current_limit(self, current: float) -> None:
        self._scpi.write(f"CURR {current}")

    def set_output(self, enabled: bool) -> None:
        self._scpi.write("OUTP ON" if enabled else "OUTP OFF")

    def measure_voltage(self) -> float:
        return self._scpi.query_float("MEAS:VOLT?")

    def measure_current(self) -> float:
        return self._scpi.query_float("MEAS:CURR?")

    def measure_output_state(self) -> bool:
        return bool(int(float(self._scpi.query("OUTP?"))))

    def wait_for_current(
        self, current: float, *, timeout_s: float, tolerance: float = 0.01
    ) -> None:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            measured = self.measure_current()
            if abs(measured - current) <= tolerance:
                return
            time.sleep(0.05)
        raise EquipmentTimeoutError(
            f"PSU did not reach {current} A within {timeout_s}s (last reading {measured} A)"
        )
