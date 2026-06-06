from __future__ import annotations

from pathlib import Path
from typing import Any

from colosseum.output.artifacts import register_artifact, resolve_artifact_path

from colosseum_equipment.instruments._base import ScpiInstrumentMixin
from colosseum_equipment.instruments._capabilities import unsupported
from colosseum_equipment.instruments.vna.trace_export import (
    frequency_axis,
    parse_vna_sdata,
    parse_vna_trace_values,
    write_s2p,
    write_trace_csv,
)
from colosseum_equipment.protocols.scpi import SCPIHelper, wait_opc
from colosseum_equipment.transports.base import Transport


class GenericVna(ScpiInstrumentMixin):
    """Generic SCPI network analyzer."""

    _model = "generic"

    def __init__(self, transport: Transport, config: dict[str, Any]) -> None:
        self._scpi = SCPIHelper(transport)
        self._config = config
        self._model = str(config.get("model", "generic")).lower()

    def _channel(self) -> int:
        return int(self._config.get("channel", 1))

    def _sens(self) -> str:
        return "SENS"

    def _calc(self) -> str:
        return "CALC"

    def _init(self, _channel: int | None = None) -> str:
        return "INIT"

    def _disp(self) -> str:
        return "DISP:WIND"

    def _ensure_scpi_vna(self, operation: str) -> None:
        if self._model == "anritsu-541xx":
            unsupported(self._model, operation)

    def preset(self) -> None:
        self._scpi.write("*RST")
        wait_opc(self._scpi)

    def set_start_frequency(self, frequency_hz: float) -> None:
        self._scpi.write(f"SENS:FREQ:STAR {frequency_hz:.6f}")

    def set_stop_frequency(self, frequency_hz: float) -> None:
        self._scpi.write(f"SENS:FREQ:STOP {frequency_hz:.6f}")

    def set_points(self, count: int) -> None:
        self._scpi.write(f"SENS:SWE:POIN {int(count)}")

    def single_sweep(self) -> None:
        self._scpi.write(f"{self._init()}:IMM")
        wait_opc(self._scpi)

    def wait_complete(self) -> None:
        wait_opc(self._scpi)

    def toggle_display(self, enabled: bool) -> None:
        self._ensure_scpi_vna("toggle_display")
        self._scpi.write(f"SYST:DISP:UPD {'ON' if enabled else 'OFF'}")

    def perform_ecal(self, ports: str) -> None:
        self._ensure_scpi_vna("perform_ecal")
        self._scpi.write(f"{self._sens()}:CORR:COLL:GUID {ports}")
        wait_opc(self._scpi)

    def set_marker(self, marker: int, frequency_hz: float, *, trace: int = 1) -> None:
        self._ensure_scpi_vna("set_marker")
        self._scpi.write(f"{self._calc()}:PAR{trace}:MARK{marker}:STAT ON")
        self._scpi.write(f"{self._calc()}:MARK{marker}:X {frequency_hz:.6f}")

    def measure_marker_frequency(self, marker: int = 1) -> float:
        self._ensure_scpi_vna("measure_marker_frequency")
        return self._scpi.query_float(f"{self._calc()}:MARK{marker}:X?")

    def measure_marker_value(self, marker: int = 1) -> float:
        self._ensure_scpi_vna("measure_marker_value")
        return self._scpi.query_float(f"{self._calc()}:MARK{marker}:Y?")

    def set_if_bw(self, bandwidth_hz: float) -> None:
        self._ensure_scpi_vna("set_if_bw")
        self._scpi.write(f"{self._sens()}:BWID:RES {bandwidth_hz:.6f}")

    def set_tx_power(self, power_dbm: float, *, port: int = 1) -> None:
        self._ensure_scpi_vna("set_tx_power")
        self._scpi.write(f"SOUR{int(port)}:POW {power_dbm:.3f}")

    def set_rx_power(self, power_dbm: float, *, port: int = 1) -> None:
        self._ensure_scpi_vna("set_rx_power")
        self._scpi.write(f"SENS{int(port)}:POW:RLEV {power_dbm:.3f}")

    def set_sweep_time(self, seconds: float) -> None:
        self._ensure_scpi_vna("set_sweep_time")
        self._scpi.write(f"{self._sens()}:SWE:TIME {seconds:.9f}")

    def set_trace_count(self, count: int) -> None:
        self._ensure_scpi_vna("set_trace_count")
        self._scpi.write(f"{self._calc()}:PAR:COUN {int(count)}")

    def set_trace_hold(self, trace: int, mode: str) -> None:
        self._ensure_scpi_vna("set_trace_hold")
        self._scpi.write(f"{self._disp()}:TRAC{trace}:MODE {mode.upper()}")

    def set_trace_parameters(self, trace: int, parameter: str, format: str) -> None:
        self._ensure_scpi_vna("set_trace_parameters")
        self._scpi.write(f"{self._calc()}:PAR{trace}:DEF {parameter.upper()}")
        self._scpi.write(f"{self._calc()}:PAR{trace}:FORM {format.upper()}")

    def configure_trigger(
        self,
        source: str = "IMM",
        *,
        continuous: bool | None = None,
        edge: str | None = None,
        delay_s: float | None = None,
        channel: int | None = None,
    ) -> None:
        self._ensure_scpi_vna("configure_trigger")
        self._scpi.write(f"TRIG:SOUR {source}")
        init = self._init(channel or self._channel())
        if continuous is not None:
            self._scpi.write(f"{init}:CONT {1 if continuous else 0}")
        if edge is not None:
            self._scpi.write(f"TRIG:EDGE {edge.upper()}")
        if delay_s is not None:
            self._scpi.write(f"TRIG:DEL {delay_s:.9f}")

    def _query_frequencies(self) -> list[float]:
        raw = self._scpi.query(f"{self._sens()}:FREQ:DATA?")
        frequencies = parse_vna_trace_values(raw)
        if frequencies:
            return frequencies
        start = self._scpi.query_float(f"{self._sens()}:FREQ:STAR?")
        stop = self._scpi.query_float(f"{self._sens()}:FREQ:STOP?")
        points = int(self._scpi.query_float(f"{self._sens()}:SWE:POIN?"))
        return frequency_axis(start, stop, points)

    def save_trace_data(
        self,
        path: str,
        *,
        trace: int = 1,
        file_format: str = "csv",
        parameter: str = "S11",
    ) -> Path:
        self._ensure_scpi_vna("save_trace_data")
        if file_format.lower() == "s2p" or path.lower().endswith(".s2p"):
            export_format = "s2p"
        else:
            export_format = "csv"

        display_was_enabled = True
        try:
            self.toggle_display(False)
        except Exception:
            display_was_enabled = False

        self.single_sweep()
        self.wait_complete()
        frequencies = self._query_frequencies()
        artifact_path = resolve_artifact_path(path)

        if export_format == "s2p":
            raw = self._scpi.query(f"{self._calc()}:PAR{trace}:DATA:SDATA?")
            reals, imags = parse_vna_sdata(raw)
            if len(frequencies) != len(reals):
                frequencies = frequency_axis(
                    self._scpi.query_float(f"{self._sens()}:FREQ:STAR?"),
                    self._scpi.query_float(f"{self._sens()}:FREQ:STOP?"),
                    len(reals),
                )
            write_s2p(artifact_path, frequencies, reals, imags, parameter=parameter)
        else:
            raw = self._scpi.query(f"{self._calc()}:PAR{trace}:DATA:FDATA?")
            values = parse_vna_trace_values(raw)
            if len(frequencies) != len(values):
                frequencies = frequency_axis(
                    self._scpi.query_float(f"{self._sens()}:FREQ:STAR?"),
                    self._scpi.query_float(f"{self._sens()}:FREQ:STOP?"),
                    len(values),
                )
            write_trace_csv(artifact_path, frequencies, values)

        register_artifact(
            "vna_trace", artifact_path, description=f"trace {trace} ({export_format})"
        )

        if display_was_enabled:
            self.toggle_display(True)

        return artifact_path

    def measure_s11_magnitude(self, _trace: int = 1) -> float:
        unsupported(
            self._model, "measure_s11_magnitude", detail="phase-2; needs vendor driver docs"
        )
