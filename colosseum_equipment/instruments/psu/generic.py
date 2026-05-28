from __future__ import annotations

from colosseum_equipment.protocols.scpi import SCPIHelper
from colosseum_equipment.transports.base import Transport


class GenericPSU:
    def __init__(self, transport: Transport, config: dict) -> None:
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

    def close(self) -> None:
        self._scpi._transport.close()
