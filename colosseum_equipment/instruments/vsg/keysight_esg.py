from __future__ import annotations

from typing import Any

from colosseum_equipment.instruments._capabilities import unsupported
from colosseum_equipment.instruments.vsg.generic import GenericVSG
from colosseum_equipment.instruments.vsg.waveform_upload import upload_waveform_file
from colosseum_equipment.protocols.scpi import wait_opc
from colosseum_equipment.transports.base import Transport


class KeysightESGVSG(GenericVSG):
    """Keysight / Agilent E4428C and E4438C ESG signal generators."""

    def __init__(self, transport: Transport, config: dict[str, Any]) -> None:
        super().__init__(transport, config)
        self._model = "keysight-esg"
        self._idn = self._scpi.query("*IDN?")
        self._is_vector = "E4438C" in self._idn.upper()

    def _require_vector(self, operation: str) -> None:
        if not self._is_vector:
            unsupported(self._model, operation, detail="requires E4438C vector arb")

    def preset(self) -> None:
        self._scpi.write("*RST")
        wait_opc(self._scpi)

    def set_alc(self, enabled: bool) -> None:
        self._scpi.write(f"POW:ALC {1 if enabled else 0}")

    def set_attenuation(self, attenuation_db: float) -> None:
        self._scpi.write(f"POW:ATT {attenuation_db}")

    def set_phase(self, phase_deg: float) -> None:
        self._scpi.write(f"PHASE {phase_deg}")

    def set_output_blanking(self, enabled: bool) -> None:
        self._scpi.write(f"OUTP:BLAN {1 if enabled else 0}")

    def upload_waveform(
        self,
        local_path: str,
        remote_name: str,
        *,
        first_last_blanking: bool = False,
    ) -> None:
        self._require_vector("upload_waveform")
        upload_waveform_file(
            self._scpi,
            self._scpi._transport,
            self._config,
            local_path,
            remote_name,
            first_last_blanking=first_last_blanking,
        )

    def delete_waveform(self, remote_name: str) -> None:
        self._require_vector("delete_waveform")
        self._scpi.write(f'MMEM:DEL "{remote_name}"')
        wait_opc(self._scpi)

    def delete_all_waveforms(self) -> None:
        self._require_vector("delete_all_waveforms")
        self._scpi.write("MMEM:DEL:WFM1")
        wait_opc(self._scpi)

    def set_multicarrier(self, num_tones: int, spacing_hz: float) -> None:
        self._require_vector("set_multicarrier")
        self._scpi.write(
            f"RAD:DMOD:ARB:SETup:MCARrier:TABLe INIT,CUSTom,{int(num_tones)},{spacing_hz:.6f}"
        )

    def toggle_multitone(self, enabled: bool) -> None:
        self._require_vector("toggle_multitone")
        self._scpi.write(f"RAD:MTONe:ARB:STAT {1 if enabled else 0}")

    def play_iq(
        self,
        filename: str,
        center_freq_hz: float,
        amplitude_dbm: float,
        sample_clock_hz: float,
    ) -> None:
        self._require_vector("play_iq")
        self._scpi.write(f'RAD:ARB:WAV "{filename}"')
        self._scpi.write(f"FREQ:CW {center_freq_hz:.6f}")
        self._scpi.write(f"POW:AMPL {amplitude_dbm:.3f}")
        self._scpi.write(f"RAD:ARB:SCLock:RATE {sample_clock_hz:.6f}")
        self._scpi.write("RAD:ARB:STAT 1")
        self._scpi.write("OUTP:MOD ON")

    def set_pulsegen_output(self, enabled: bool) -> None:
        self._scpi.write(f"PULM:STAT {1 if enabled else 0}")

    def set_pulsemod_output(self, enabled: bool) -> None:
        self._scpi.write(f"PULM:STAT {1 if enabled else 0}")

    def set_pulse_period(self, period_s: float) -> None:
        self._scpi.write(f"PULM:INT:PER {period_s:.9f}")

    def set_pulse_width(self, width_s: float) -> None:
        self._scpi.write(f"PULM:INT:PWID {width_s:.9f}")

    def pulse_source(self, source: str) -> None:
        normalized = source.upper()
        if normalized == "PULSE":
            self._scpi.write("PULM:SOUR INT")
            self._scpi.write("PULM:INT:FUNC SHAP PULS")
        elif normalized == "SQUARE":
            self._scpi.write("PULM:SOUR INT")
            self._scpi.write("PULM:INT:FUNC SHAP SQU")
        elif normalized == "EXT1":
            self._scpi.write("PULM:SOUR EXT1")
        elif normalized == "EXT2":
            self._scpi.write("PULM:SOUR EXT2")
        else:
            raise ValueError(f"unsupported pulse source: {source}")

    def step_power(
        self,
        start_dbm: float,
        stop_dbm: float,
        step_db: float,
        interval_s: float,
    ) -> None:
        if step_db <= 0:
            raise ValueError("step_db must be positive")
        points = max(2, int(abs(stop_dbm - start_dbm) / step_db) + 1)
        self._scpi.write("LIST:TYPE STEP")
        self._scpi.write(f"POW:STAR {start_dbm:.3f}")
        self._scpi.write(f"POW:STOP {stop_dbm:.3f}")
        self._scpi.write(f"SWE:POIN {points}")
        self._scpi.write(f"SWE:DWEL {interval_s:.9f}")
        self._scpi.write("LIST:TRIG:SOUR IMM")
        self._scpi.write("INIT:CONT ON")

    def freq_sweep(
        self,
        start_hz: float,
        stop_hz: float,
        points: int,
        dwell_s: float,
    ) -> None:
        self._scpi.write("LIST:TYPE STEP")
        self._scpi.write(f"FREQ:STAR {start_hz:.6f}")
        self._scpi.write(f"FREQ:STOP {stop_hz:.6f}")
        self._scpi.write(f"SWE:POIN {int(points)}")
        self._scpi.write(f"SWE:DWEL {dwell_s:.9f}")
        self._scpi.write("INIT:CONT ON")

    def amplitude_sweep(
        self,
        start_dbm: float,
        stop_dbm: float,
        points: int,
        dwell_s: float,
    ) -> None:
        self._scpi.write("LIST:TYPE STEP")
        self._scpi.write(f"POW:STAR {start_dbm:.3f}")
        self._scpi.write(f"POW:STOP {stop_dbm:.3f}")
        self._scpi.write(f"SWE:POIN {int(points)}")
        self._scpi.write(f"SWE:DWEL {dwell_s:.9f}")
        self._scpi.write("INIT:CONT ON")

    def select_waveform(self, remote_name: str) -> None:
        self._require_vector("select_waveform")
        self._scpi.write(f'RAD:ARB:WAV "{remote_name}"')

    def set_arb_state(self, enabled: bool) -> None:
        self._require_vector("set_arb_state")
        self._scpi.write(f"RAD:ARB:STAT {1 if enabled else 0}")

    def configure_list(self, frequencies: list[float], powers: list[float] | None = None) -> None:
        self._scpi.write("LIST:MODE LIST")
        freq_values = ",".join(str(value) for value in frequencies)
        self._scpi.write(f"LIST:FREQ {freq_values}")
        if powers is not None:
            power_values = ",".join(str(value) for value in powers)
            self._scpi.write(f"LIST:POW {power_values}")

    def measure_frequency(self) -> float:
        return self._scpi.query_float(":FREQ:CW?")

    def measure_power_dbm(self) -> float:
        return self._scpi.query_float(":POW:AMPL?")

    def set_modulation(self, enabled: bool, modulation_type: str = "none") -> None:
        if self._is_vector:
            self._scpi.write(f"DM:STAT {1 if enabled else 0}")
            return
        if enabled and modulation_type.lower() != "none":
            self._scpi.write(f"DMODE {modulation_type.upper()}")
        else:
            self._scpi.write("DMODE OFF")
