from __future__ import annotations

from typing import Any

from colosseum_equipment.instruments._base import ScpiInstrumentMixin
from colosseum_equipment.instruments._capabilities import unsupported
from colosseum_equipment.protocols.scpi import SCPIHelper, wait_opc
from colosseum_equipment.transports.base import Transport


class GenericVSG(ScpiInstrumentMixin):
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

    def preset(self) -> None:
        unsupported(self._model, "preset")

    def wait_complete(self) -> None:
        wait_opc(self._scpi)

    def set_alc(self, _enabled: bool) -> None:
        unsupported(self._model, "set_alc")

    def set_attenuation(self, _attenuation_db: float) -> None:
        unsupported(self._model, "set_attenuation")

    def set_phase(self, _phase_deg: float) -> None:
        unsupported(self._model, "set_phase")

    def set_output_blanking(self, _enabled: bool) -> None:
        unsupported(self._model, "set_output_blanking")

    def upload_waveform(
        self,
        local_path: str,
        remote_name: str,
        *,
        first_last_blanking: bool = False,
    ) -> None:
        _ = local_path, remote_name, first_last_blanking
        unsupported(self._model, "upload_waveform")

    def delete_waveform(self, _remote_name: str) -> None:
        unsupported(self._model, "delete_waveform")

    def delete_all_waveforms(self) -> None:
        unsupported(self._model, "delete_all_waveforms")

    def set_multicarrier(self, _num_tones: int, _spacing_hz: float) -> None:
        unsupported(self._model, "set_multicarrier")

    def toggle_multitone(self, _enabled: bool) -> None:
        unsupported(self._model, "toggle_multitone")

    def play_iq(
        self,
        _filename: str,
        _center_freq_hz: float,
        _amplitude_dbm: float,
        _sample_clock_hz: float,
    ) -> None:
        unsupported(self._model, "play_iq")

    def set_pulsegen_output(self, _enabled: bool) -> None:
        unsupported(self._model, "set_pulsegen_output")

    def set_pulsemod_output(self, _enabled: bool) -> None:
        unsupported(self._model, "set_pulsemod_output")

    def set_pulse_period(self, _period_s: float) -> None:
        unsupported(self._model, "set_pulse_period")

    def set_pulse_width(self, _width_s: float) -> None:
        unsupported(self._model, "set_pulse_width")

    def pulse_source(self, _source: str) -> None:
        unsupported(self._model, "pulse_source")

    def step_power(
        self,
        _start_dbm: float,
        _stop_dbm: float,
        _step_db: float,
        _interval_s: float,
    ) -> None:
        unsupported(self._model, "step_power")

    def freq_sweep(
        self,
        _start_hz: float,
        _stop_hz: float,
        _points: int,
        _dwell_s: float,
    ) -> None:
        unsupported(self._model, "freq_sweep")

    def amplitude_sweep(
        self,
        _start_dbm: float,
        _stop_dbm: float,
        _points: int,
        _dwell_s: float,
    ) -> None:
        unsupported(self._model, "amplitude_sweep")

    def select_waveform(self, _remote_name: str) -> None:
        unsupported(self._model, "select_waveform")

    def set_arb_state(self, _enabled: bool) -> None:
        unsupported(self._model, "set_arb_state")

    def configure_list(self, _frequencies: list[float], _powers: list[float] | None = None) -> None:
        unsupported(self._model, "configure_list")

    def set_modulation(self, _enabled: bool, _modulation_type: str = "none") -> None:
        unsupported(self._model, "set_modulation")

    def measure_output_state(self) -> bool:
        return bool(int(float(self._scpi.query("OUTP:STAT?"))))

    def measure_frequency(self) -> float:
        return self._scpi.query_float("FREQ:CW?")

    def measure_power_dbm(self) -> float:
        return self._scpi.query_float("POW:AMPL?")
