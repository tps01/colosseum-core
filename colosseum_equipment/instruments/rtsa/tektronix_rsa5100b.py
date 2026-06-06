from __future__ import annotations

from pathlib import Path
from typing import Any

from colosseum.output.artifacts import register_artifact, resolve_artifact_path

from colosseum_equipment.instruments.rtsa.generic import GenericRtsa
from colosseum_equipment.instruments.rtsa.iq_export import (
    normalize_iq_format,
    write_iq_bin,
    write_iq_mat,
    write_iq_tar,
)
from colosseum_equipment.protocols.scpi import wait_opc
from colosseum_equipment.transports.base import Transport


class TektronixRSA5100BRtsa(GenericRtsa):
    """Tektronix RSA5100B real-time spectrum analyzer (IQ acquisition)."""

    def __init__(self, transport: Transport, config: dict[str, Any]) -> None:
        super().__init__(transport, config)
        self._model = "tektronix-rsa5100b"

    def _ensure_spectrum_view(self) -> None:
        active = self._scpi.query("DISP:WIND:ACT:MEAS?").upper()
        if "SPEC" not in active:
            self._scpi.write("DISP:WIND:ACT:MEAS SPECtrum")

    def preset(self) -> None:
        self._scpi.write("*RST")
        wait_opc(self._scpi)

    def set_center_freq(self, frequency_hz: float) -> None:
        self._ensure_spectrum_view()
        self._scpi.write(f"DISP:SPEC:FREQ:OFFS {frequency_hz:.6f}")

    def set_span(self, span_hz: float) -> None:
        self._ensure_spectrum_view()
        self._scpi.write(f"DISP:SPEC:FREQ:SCAL {span_hz:.6f}")

    def set_bandwidth(self, bandwidth_hz: float) -> None:
        self._ensure_spectrum_view()
        self._scpi.write(f"SENS:SPEC:BAND:RES {bandwidth_hz:.6f}")

    def set_acq_time(self, seconds: float) -> None:
        self._ensure_spectrum_view()
        self._scpi.write(f"SENS:SPEC:ACQ:TIME {seconds:.9f}")

    def set_continuous_run(self, enabled: bool) -> None:
        self._ensure_spectrum_view()
        self._scpi.write(f"INIT:CONT {1 if enabled else 0}")

    def set_num_samples(self, count: int) -> None:
        self._ensure_spectrum_view()
        self._scpi.write(f"SENS:SPEC:ACQ:POIN {int(count)}")

    def get_num_samples(self) -> int:
        self._ensure_spectrum_view()
        return int(self._scpi.query_float("SENS:SPEC:ACQ:POIN?"))

    def set_trigger_source(self, source: str) -> None:
        self._ensure_spectrum_view()
        self._scpi.write(f"TRIG:SOUR {source}")

    def set_trigger_level(self, level_dbm: float) -> None:
        self._ensure_spectrum_view()
        self._scpi.write(f"TRIG:LEV {level_dbm:.3f}")

    def set_trigger_position(self, position_dbm: float) -> None:
        self._ensure_spectrum_view()
        self._scpi.write(f"TRIG:POS {position_dbm:.3f}")

    def run(self) -> None:
        self._ensure_spectrum_view()
        self._scpi.write("INIT:IMM")
        wait_opc(self._scpi)

    def save_IQ_data(self, path: str, *, file_format: str = "bin") -> Path:
        self._ensure_spectrum_view()
        payload = self._scpi.read_binary_block("FETCH:SPEC:IQ?")
        export_format = normalize_iq_format(file_format, path)
        artifact_path = resolve_artifact_path(path)
        metadata = {
            "center_freq_hz": self._scpi.query_float("DISP:SPEC:FREQ:OFFS?"),
            "span_hz": self._scpi.query_float("DISP:SPEC:FREQ:SCAL?"),
            "num_samples": self.get_num_samples(),
            "format": export_format,
        }
        if export_format == "mat":
            write_iq_mat(artifact_path, payload, metadata=metadata)
        elif export_format == "iq.tar":
            write_iq_tar(artifact_path, payload, metadata=metadata)
        else:
            write_iq_bin(artifact_path, payload)
        register_artifact("rtsa_iq", artifact_path, description=f"IQ capture ({export_format})")
        return artifact_path
