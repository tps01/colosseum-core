from __future__ import annotations

from pathlib import Path

from colosseum_equipment.instruments._capabilities import unsupported
from colosseum_equipment.instruments.vsg.generic import GenericVSG
from colosseum_equipment.protocols.scpi import wait_opc
from colosseum_equipment.transports.base import Transport


class KeysightESGVSG(GenericVSG):
    """Keysight / Agilent E4428C and E4438C ESG signal generators."""

    def __init__(self, transport: Transport, config: dict) -> None:
        super().__init__(transport, config)
        self._model = "keysight-esg"
        self._idn = self._scpi.query("*IDN?")
        self._is_vector = "E4438C" in self._idn.upper()

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

    def upload_waveform(self, local_path: str, remote_name: str) -> None:
        if not self._is_vector:
            unsupported(
                self._model,
                "upload_waveform",
                detail="requires E4438C vector arb",
            )
        payload = Path(local_path).read_bytes()
        self._scpi.write_binary_block(f'MMEM:DATA "{remote_name}"', payload)
        wait_opc(self._scpi)

    def select_waveform(self, remote_name: str) -> None:
        if not self._is_vector:
            unsupported(
                self._model,
                "select_waveform",
                detail="requires E4438C vector arb",
            )
        self._scpi.write(f'RAD:ARB:WAV "{remote_name}"')

    def set_arb_state(self, enabled: bool) -> None:
        if not self._is_vector:
            unsupported(
                self._model,
                "set_arb_state",
                detail="requires E4438C vector arb",
            )
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
