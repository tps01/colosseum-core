from __future__ import annotations

from pathlib import Path

from colosseum.output.artifacts import register_artifact, resolve_artifact_path

from colosseum_equipment.instruments.speca.generic import GenericSpecA
from colosseum_equipment.instruments.speca.trace_csv import parse_trace_amplitudes, write_trace_csv


class KeysightE4407BSpecA(GenericSpecA):
    """Agilent / Keysight E4407B ESA-E spectrum analyzer."""

    def __init__(self, transport, config: dict) -> None:
        super().__init__(transport, config)
        self._model = "keysight-e4407b"

    def set_center_frequency(self, frequency: float) -> None:
        self._scpi.write(f"SENS:FREQ:CENT {frequency:.6f}")

    def set_span(self, span: float) -> None:
        self._scpi.write(f"SENS:FREQ:SPAN {span:.6f}")

    def set_rbw(self, rbw: float) -> None:
        self._scpi.write(f"SENS:BAND:RES {rbw:.6f}")

    def set_vbw(self, vbw: float) -> None:
        self._scpi.write(f"SENS:BAND:VID {vbw}")

    def set_sweep_time(self, seconds: float) -> None:
        self._scpi.write(f"SENS:SWE:TIME {seconds}")

    def set_detector(self, detector: str) -> None:
        self._scpi.write(f"SENS:SWE:DET {detector}")

    def peak_search(self, marker: int = 1) -> None:
        self._scpi.write(f"CALC:MARK{marker}:MAX")

    def measure_marker_power(self, marker: int = 1) -> float:
        return self._scpi.query_float(f"CALC:MARK{marker}:Y?")

    def measure_marker_frequency(self, marker: int = 1) -> float:
        return self._scpi.query_float(f"CALC:MARK{marker}:X?")

    def save_trace_data(
        self,
        path: str,
        *,
        trace: int = 1,
        include_frequency: bool = True,
    ) -> Path:
        from colosseum_equipment.protocols.scpi import prepare_fast_sweep

        prepare_fast_sweep(self._scpi)
        self.single_sweep()
        center = self._scpi.query_float("SENS:FREQ:CENT?")
        span = self._scpi.query_float("SENS:FREQ:SPAN?")
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
        return artifact_path

    def save_screenshot(self, path: str) -> Path:
        remote = "SCREEN.PNG"
        self._scpi.write(f'MMEM:STOR:SCR "{remote}"')
        payload = self._scpi.read_binary_block(f'MMEM:DATA? "{remote}"')
        artifact_path = resolve_artifact_path(path)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_bytes(payload)
        register_artifact("speca_screenshot", artifact_path, description="instrument screenshot")
        return artifact_path
