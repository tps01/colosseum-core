from __future__ import annotations

from pathlib import Path

from colosseum.output.artifacts import register_artifact, resolve_artifact_path

from colosseum_equipment.instruments.speca.generic import GenericSpecA
from colosseum_equipment.instruments.speca.trace_csv import parse_trace_amplitudes, write_trace_csv
from colosseum_equipment.protocols.scpi import prepare_fast_sweep, wait_opc


class TektronixRSA5100BSpecA(GenericSpecA):
    """Tektronix RSA5100B real-time spectrum analyzer (Spectrum view)."""

    def __init__(self, transport, config: dict) -> None:
        super().__init__(transport, config)
        self._model = "tektronix-rsa5100b"

    def _ensure_spectrum_view(self) -> None:
        active = self._scpi.query("DISP:WIND:ACT:MEAS?").upper()
        if "SPEC" not in active:
            self._scpi.write("DISP:WIND:ACT:MEAS SPECtrum")

    def set_center_frequency(self, frequency: float) -> None:
        self._ensure_spectrum_view()
        self._scpi.write(f"DISP:SPEC:FREQ:OFFS {frequency:.6f}")

    def set_span(self, span: float) -> None:
        self._ensure_spectrum_view()
        self._scpi.write(f"DISP:SPEC:FREQ:SCAL {span:.6f}")

    def set_rbw(self, rbw: float) -> None:
        self._ensure_spectrum_view()
        self._scpi.write(f"SENS:SPEC:BAND:RES {rbw:.6f}")

    def peak_search(self, marker: int = 1) -> None:
        self._ensure_spectrum_view()
        self._scpi.write(f"CALC:MARK{marker}:MAX")

    def measure_marker_power(self, marker: int = 1) -> float:
        self._ensure_spectrum_view()
        return self._scpi.query_float(f"CALC:MARK{marker}:Y?")

    def measure_marker_frequency(self, marker: int = 1) -> float:
        self._ensure_spectrum_view()
        return self._scpi.query_float(f"CALC:MARK{marker}:X?")

    def save_trace_data(
        self,
        path: str,
        *,
        trace: int = 1,
        include_frequency: bool = True,
    ) -> Path:
        self._ensure_spectrum_view()
        prepare_fast_sweep(self._scpi)
        self.single_sweep()
        center = self._scpi.query_float("DISP:SPEC:FREQ:OFFS?")
        span = self._scpi.query_float("DISP:SPEC:FREQ:SCAL?")
        raw = self._scpi.query(f"TRAC:DATA? TRACE{trace}")
        amplitudes = parse_trace_amplitudes(raw)
        artifact_path = resolve_artifact_path(path)
        write_trace_csv(
            artifact_path,
            amplitudes,
            center_hz=center if include_frequency else None,
            span_hz=span if include_frequency else None,
            include_frequency=include_frequency,
        )
        register_artifact("speca_trace", artifact_path, description=f"trace {trace}")
        self._last_trace_path = artifact_path
        return artifact_path

    def configure_trigger(self, source: str = "IMM") -> None:
        self._ensure_spectrum_view()
        self._scpi.write(f"TRIG:SOUR {source}")

    def set_acquisition_length(self, seconds: float) -> None:
        self._ensure_spectrum_view()
        self._scpi.write(f"SENS:SPEC:ACQ:TIME {seconds}")

    def download_capture(self, path: str, kind: str = "iq") -> Path:
        self._ensure_spectrum_view()
        command = "FETCH:SPEC:IQ?" if kind.lower() == "iq" else "FETCH:SPEC:TIME?"
        payload = self._scpi.read_binary_block(command)
        artifact_path = resolve_artifact_path(path)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_bytes(payload)
        register_artifact("speca_capture", artifact_path, description=f"capture {kind}")
        return artifact_path

    def save_spectrogram(self, path: str) -> Path:
        self._ensure_spectrum_view()
        payload = self._scpi.read_binary_block("FETCH:SGRam:TRAC?")
        artifact_path = resolve_artifact_path(path)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_bytes(payload)
        register_artifact("speca_spectrogram", artifact_path, description="spectrogram")
        return artifact_path
