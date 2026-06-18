from __future__ import annotations

from pathlib import Path
from typing import Any

from colosseum_equipment.instruments._base import ScpiInstrumentMixin
from colosseum_equipment.instruments._capabilities import unsupported
from colosseum_equipment.protocols.scpi import SCPIHelper
from colosseum_equipment.transports.base import Transport


class GenericRtsa(ScpiInstrumentMixin):
    """Generic RTSA placeholder; vendor models required for IQ acquisition."""

    _model = "generic"

    def __init__(self, transport: Transport, config: dict[str, Any]) -> None:
        self._scpi = SCPIHelper(transport)
        self._config = config
        self._model = str(config.get("model", "generic")).lower()
        if "center_freq" in config:
            self.set_center_freq(float(config["center_freq"]))
        if "span" in config:
            self.set_span(float(config["span"]))
        if "rbw" in config:
            self.set_bandwidth(float(config["rbw"]))

    def preset(self) -> None:
        unsupported(self._model, "preset")

    def set_center_freq(self, _frequency_hz: float) -> None:
        unsupported(self._model, "set_center_freq")

    def set_span(self, _span_hz: float) -> None:
        unsupported(self._model, "set_span")

    def set_bandwidth(self, _bandwidth_hz: float) -> None:
        unsupported(self._model, "set_bandwidth")

    def set_acq_time(self, _seconds: float) -> None:
        unsupported(self._model, "set_acq_time")

    def set_continuous_run(self, _enabled: bool) -> None:
        unsupported(self._model, "set_continuous_run")

    def set_num_samples(self, _count: int) -> None:
        unsupported(self._model, "set_num_samples")

    def get_num_samples(self) -> int:
        unsupported(self._model, "get_num_samples")
        return 0

    def set_trigger_source(self, _source: str) -> None:
        unsupported(self._model, "set_trigger_source")

    def set_trigger_level(self, _level_dbm: float) -> None:
        unsupported(self._model, "set_trigger_level")

    def set_trigger_position(self, _position_dbm: float) -> None:
        unsupported(self._model, "set_trigger_position")

    def run(self) -> None:
        unsupported(self._model, "run")

    def save_IQ_data(self, path: str, *, file_format: str = "bin") -> Path:
        _ = path, file_format
        unsupported(self._model, "save_IQ_data")
