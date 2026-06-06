from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any

from colosseum.output.artifacts import register_artifact, resolve_artifact_path

from colosseum_equipment.instruments._capabilities import unsupported
from colosseum_equipment.instruments.speca.bandwidth import measure_bandwidth_hz
from colosseum_equipment.instruments.speca.trace_csv import (
    frequency_axis,
    parse_trace_amplitudes,
    read_trace_power_at_frequency,
    write_trace_csv,
)
from colosseum_equipment.instruments.speca.trace_plot import read_trace_csv, write_trace_plot
from colosseum_equipment.protocols.scpi import SCPIHelper, prepare_fast_sweep, wait_opc
from colosseum_equipment.transports.base import Transport


class GenericSpecA:
    _model = "generic"

    def __init__(self, transport: Transport, config: dict[str, Any]) -> None:
        self._scpi = SCPIHelper(transport)
        self._config = config
        self._model = str(config.get("model", "generic")).lower()
        if "center_freq" in config:
            self.set_center_frequency(float(config["center_freq"]))
        if "span" in config:
            self.set_span(float(config["span"]))
        if "rbw" in config:
            self.set_rbw(float(config["rbw"]))

    def set_center_frequency(self, frequency: float) -> None:
        self._scpi.write(f"FREQ:CENT {frequency:.6f}")

    def set_start_frequency(self, frequency_hz: float) -> None:
        self._scpi.write(f"FREQ:STAR {frequency_hz:.6f}")

    def set_stop_frequency(self, frequency_hz: float) -> None:
        self._scpi.write(f"FREQ:STOP {frequency_hz:.6f}")

    def set_span(self, span: float) -> None:
        self._scpi.write(f"FREQ:SPAN {span:.6f}")

    def set_rbw(self, rbw: float) -> None:
        self._scpi.write(f"BAND:RES {rbw:.6f}")

    def toggle_marker(self, marker: int, enabled: bool) -> None:
        self._scpi.write(f"CALC:MARK{marker}:STAT {'ON' if enabled else 'OFF'}")

    def peak_search(self, marker: int = 1) -> None:
        self._scpi.write(f"CALC:MARK{marker}:MAX")

    def next_peak_right(self, marker: int = 1) -> None:
        self._scpi.write(f"CALC:MARK{marker}:MAX:NEXT")

    def next_peak_left(self, marker: int = 1) -> None:
        self._scpi.write(f"CALC:MARK{marker}:MAX:PREV")

    def next_highest_peak(self, marker: int = 1) -> None:
        self._scpi.write(f"CALC:MARK{marker}:MAX")

    def set_sweep_points(self, count: int) -> None:
        self._scpi.write(f"SWE:POIN {int(count)}")

    def toggle_trigger_delay(self, enabled: bool) -> None:
        self._scpi.write(f"TRIG:DEL:STAT {'ON' if enabled else 'OFF'}")

    def set_trigger_delay(self, delay_s: float) -> None:
        self._scpi.write(f"TRIG:DEL {delay_s:.9f}")

    def set_trigger_source(self, source: str) -> None:
        self._scpi.write(f"TRIG:SOUR {source}")

    def user_preset(self) -> None:
        self._scpi.write("*RCL 1")
        wait_opc(self._scpi)

    def set_marker_frequency(self, marker: int, frequency_hz: float) -> None:
        self._scpi.write(f"CALC:MARK{marker}:X {frequency_hz:.6f}")

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
        prepare_fast_sweep(self._scpi)
        self.single_sweep()
        center = self._scpi.query_float("FREQ:CENT?")
        span = self._scpi.query_float("FREQ:SPAN?")
        raw = self._scpi.query(f"TRAC:DATA? TRACE{trace}")
        amplitudes = parse_trace_amplitudes(raw)
        if include_frequency:
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

    def measure_bw(
        self,
        start_hz: float,
        stop_hz: float,
        *,
        threshold_db: float = 3.0,
        smoothing_order: int = 0,
        trace: int = 1,
        trace_path: str | Path | None = None,
    ) -> float:
        path = (
            Path(trace_path) if trace_path is not None else getattr(self, "_last_trace_path", None)
        )
        if path is not None:
            frequencies, amplitudes = read_trace_csv(path)
        else:
            frequencies, amplitudes = self._fetch_trace(trace, include_frequency=True)
        return measure_bandwidth_hz(
            frequencies,
            amplitudes,
            start_hz=start_hz,
            stop_hz=stop_hz,
            threshold_db=threshold_db,
            smoothing_order=smoothing_order,
        )

    def measure_trace_power_at_frequency(
        self,
        frequency_hz: float,
        *,
        trace_path: str | Path | None = None,
    ) -> tuple[float, float]:
        path = (
            Path(trace_path) if trace_path is not None else getattr(self, "_last_trace_path", None)
        )
        if path is None:
            raise ValueError("no trace CSV; call save_trace_data first or pass trace_path=")
        return read_trace_power_at_frequency(path, frequency_hz)

    def preset(self) -> None:
        self._scpi.write("*RST")
        wait_opc(self._scpi)

    def set_reference_level(self, level_dbm: float) -> None:
        self._scpi.write(f"DISP:WIND:TRAC:Y:SCAL:RLEV {level_dbm}")

    def set_vbw(self, vbw: float) -> None:
        self._scpi.write(f"BAND:VID {vbw}")

    def set_sweep_time(self, seconds: float) -> None:
        self._scpi.write(f"SWE:TIME {seconds}")

    def set_detector(self, detector: str) -> None:
        self._scpi.write(f"DET {detector}")

    def set_trace_mode(self, trace: int, mode: str) -> None:
        self._scpi.write(f"TRAC{trace}:MODE {mode}")

    def set_continuous_sweep(self, enabled: bool) -> None:
        self._scpi.write(f"INIT:CONT {1 if enabled else 0}")

    def single_sweep(self) -> None:
        self._scpi.write("INIT:CONT OFF")
        self._scpi.write("INIT:IMM")
        wait_opc(self._scpi)

    def save_screenshot(self, _path: str) -> Path:
        unsupported(self._model, "save_screenshot")

    def close(self) -> None:
        with contextlib.suppress(Exception):
            self._scpi.write("DISP:UPD ON")
        self._scpi._transport.close()
