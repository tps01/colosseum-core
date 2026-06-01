from __future__ import annotations

from colosseum_equipment.instruments._capabilities import unsupported
from colosseum_equipment.protocols.scpi import SCPIHelper, wait_opc
from colosseum_equipment.transports.base import Transport


class GenericVSG:
    _model = "generic"

    def __init__(self, transport: Transport, config: dict) -> None:
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

    def preset(self) -> None:
        unsupported(self._model, "preset")

    def wait_complete(self) -> None:
        wait_opc(self._scpi)

    def set_alc(self, enabled: bool) -> None:
        unsupported(self._model, "set_alc")

    def set_attenuation(self, attenuation_db: float) -> None:
        unsupported(self._model, "set_attenuation")

    def set_phase(self, phase_deg: float) -> None:
        unsupported(self._model, "set_phase")

    def set_output_blanking(self, enabled: bool) -> None:
        unsupported(self._model, "set_output_blanking")

    def upload_waveform(self, local_path: str, remote_name: str) -> None:
        unsupported(self._model, "upload_waveform")

    def select_waveform(self, remote_name: str) -> None:
        unsupported(self._model, "select_waveform")

    def set_arb_state(self, enabled: bool) -> None:
        unsupported(self._model, "set_arb_state")

    def configure_list(self, frequencies: list[float], powers: list[float] | None = None) -> None:
        unsupported(self._model, "configure_list")

    def set_modulation(self, enabled: bool, modulation_type: str = "none") -> None:
        unsupported(self._model, "set_modulation")

    def measure_output_state(self) -> bool:
        return bool(int(float(self._scpi.query("OUTP:STAT?"))))

    def close(self) -> None:
        self._scpi._transport.close()
