from __future__ import annotations

from typing import Any

from colosseum_equipment.instruments._base import ScpiInstrumentMixin
from colosseum_equipment.protocols.scpi import SCPIHelper
from colosseum_equipment.transports.base import Transport


class GenericASG(ScpiInstrumentMixin):
    """Generic analog signal generator using R&S-oriented SCPI mnemonics."""

    _model = "generic"

    def __init__(self, transport: Transport, config: dict[str, Any]) -> None:
        self._scpi = SCPIHelper(transport)
        self._config = config
        self._model = str(config.get("model", "generic")).lower()
        if "frequency" in config:
            self.set_frequency(float(config["frequency"]))
        if "power_dbm" in config:
            self.set_power(float(config["power_dbm"]))
        if config.get("output"):
            self.set_output(True)

    def set_frequency(self, frequency: float) -> None:
        self._scpi.write(f"FREQ:CW {frequency:.6f}")

    def set_power(self, power_dbm: float) -> None:
        self._scpi.write(f"POW:AMPL {power_dbm:.3f}")

    def set_output(self, enabled: bool) -> None:
        self._scpi.write("OUTP ON" if enabled else "OUTP OFF")

    def set_pulsegen_output(self, enabled: bool) -> None:
        self._scpi.write(":PULGen:STAT ON" if enabled else ":PULGen:STAT OFF")

    def set_pulsemod_output(self, enabled: bool) -> None:
        self._scpi.write(":PULM:STAT ON" if enabled else ":PULM:STAT OFF")

    def set_pulse_period(self, period_s: float) -> None:
        self._scpi.write(f":PULM:PER {period_s:.9f}")

    def set_pulse_width(self, width_s: float) -> None:
        self._scpi.write(f":PULM:WIDt {width_s:.9f}")
