from __future__ import annotations

from pathlib import Path
from typing import Any

from colosseum.output.artifacts import register_artifact, resolve_artifact_path

from colosseum_equipment.instruments.speca.generic import GenericSpecA
from colosseum_equipment.instruments.speca.trace_csv import parse_trace_amplitudes, write_trace_csv
from colosseum_equipment.instruments.speca.trace_plot import write_trace_plot
from colosseum_equipment.transports.base import Transport


class KeysightE4407BSpecA(GenericSpecA):
    """Agilent / Keysight E4407B ESA-E spectrum analyzer."""

    def __init__(self, transport: Transport, config: dict[str, Any]) -> None:
        super().__init__(transport, config)
        self._model = "keysight-e4407b"

    def set_center_frequency(self, frequency: float) -> None:
        self._scpi.write(f"SENS:FREQ:CENT {frequency:.6f}")

    def set_start_frequency(self, frequency_hz: float) -> None:
        self._scpi.write(f"SENS:FREQ:STAR {frequency_hz:.6f}")

    def set_stop_frequency(self, frequency_hz: float) -> None:
        self._scpi.write(f"SENS:FREQ:STOP {frequency_hz:.6f}")

    def set_span(self, span: float) -> None:
        self._scpi.write(f"SENS:FREQ:SPAN {span:.6f}")

    def set_rbw(self, rbw: float) -> None:
        self._scpi.write(f"SENS:BAND:RES {rbw:.6f}")

    def set_vbw(self, vbw: float) -> None:
        self._scpi.write(f"SENS:BAND:VID {vbw}")

    def set_sweep_time(self, seconds: float) -> None:
        self._scpi.write(f"SENS:SWE:TIME {seconds}")

    def set_sweep_points(self, count: int) -> None:
        self._scpi.write(f"SENS:SWE:POIN {int(count)}")

    def set_detector(self, detector: str) -> None:
        self._scpi.write(f"SENS:SWE:DET {detector}")

    def peak_search(self, marker: int = 1) -> None:
        self._scpi.write(f"CALC:MARK{marker}:MAX")

    def measure_marker_power(self, marker: int = 1) -> float:
        return self._scpi.query_float(f"CALC:MARK{marker}:Y?")

    def measure_marker_frequency(self, marker: int = 1) -> float:
        return self._scpi.query_float(f"CALC:MARK{marker}:X?")

    def _fetch_trace(
        self,
        trace: int,
        *,
        include_frequency: bool = True,
    ) -> tuple[list[float], list[float]]:
        from colosseum_equipment.protocols.scpi import prepare_fast_sweep

        prepare_fast_sweep(self._scpi)
        self.single_sweep()
        center = self._scpi.query_float("SENS:FREQ:CENT?")
        span = self._scpi.query_float("SENS:FREQ:SPAN?")
        raw = self._scpi.query(f"TRAC:DATA? TRACE{trace}")
        amplitudes = parse_trace_amplitudes(raw)
        if include_frequency:
            from colosseum_equipment.instruments.speca.trace_csv import frequency_axis

            frequencies = frequency_axis(center, span, len(amplitudes))
        else:
            frequencies = list(range(len(amplitudes)))
        return frequencies, amplitudes

    def save_trace_data(
        self,
        path: str,
        *,
        trace: int = 1,
        include_frequency: bool = True,
        save_plot: bool = False,
        plot_path: str | None = None,
    ) -> Path:
        frequencies, amplitudes = self._fetch_trace(trace, include_frequency=include_frequency)
        center = (frequencies[0] + frequencies[-1]) / 2.0 if frequencies else 0.0
        span = frequencies[-1] - frequencies[0] if len(frequencies) > 1 else 0.0
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

        if save_plot or plot_path is not None:
            png_path = resolve_artifact_path(plot_path or str(Path(path).with_suffix(".png")))
            write_trace_plot(artifact_path, png_path)
            register_artifact("speca_trace_plot", png_path, description=f"trace {trace} plot")

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
