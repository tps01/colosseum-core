from __future__ import annotations

from pathlib import Path

from colosseum.output.artifacts import register_artifact, resolve_artifact_path

from colosseum_equipment.instruments._capabilities import unsupported
from colosseum_equipment.instruments.speca.trace_csv import (
    parse_trace_amplitudes,
    read_trace_power_at_frequency,
    write_trace_csv,
)
from colosseum_equipment.protocols.scpi import SCPIHelper, prepare_fast_sweep, wait_opc
from colosseum_equipment.transports.base import Transport


class GenericSpecA:
    _model = "generic"

    def __init__(self, transport: Transport, config: dict) -> None:
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

    def set_span(self, span: float) -> None:
        self._scpi.write(f"FREQ:SPAN {span:.6f}")

    def set_rbw(self, rbw: float) -> None:
        self._scpi.write(f"BAND:RES {rbw:.6f}")

    def peak_search(self, marker: int = 1) -> None:
        self._scpi.write(f"CALC:MARK{marker}:MAX")

    def set_marker_frequency(self, marker: int, frequency_hz: float) -> None:
        self._scpi.write(f"CALC:MARK{marker}:X {frequency_hz:.6f}")

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
        prepare_fast_sweep(self._scpi)
        self.single_sweep()
        center = self._scpi.query_float("FREQ:CENT?")
        span = self._scpi.query_float("FREQ:SPAN?")
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

    def measure_trace_power_at_frequency(
        self,
        frequency_hz: float,
        *,
        trace_path: str | Path | None = None,
    ) -> tuple[float, float]:
        path = Path(trace_path) if trace_path is not None else getattr(self, "_last_trace_path", None)
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

    def save_screenshot(self, path: str) -> Path:
        unsupported(self._model, "save_screenshot")

    def download_capture(self, path: str, kind: str = "iq") -> Path:
        unsupported(self._model, "download_capture")

    def save_spectrogram(self, path: str) -> Path:
        unsupported(self._model, "save_spectrogram")

    def configure_trigger(self, source: str = "IMM") -> None:
        unsupported(self._model, "configure_trigger")

    def set_acquisition_length(self, seconds: float) -> None:
        unsupported(self._model, "set_acquisition_length")

    def close(self) -> None:
        try:
            self._scpi.write("DISP:UPD ON")
        except Exception:
            pass
        self._scpi._transport.close()
